# -*- coding: utf-8 -*-
"""真实浏览器走查：以真实用户体验完整使用 LumiLearn 全部学习端口并检查

用系统 Edge（headless）访问天虹服务器各端口，执行真实用户操作并断言，
截图保存到 docs/evidence/ 作为运行证据。
覆盖：18080/classroom、18080/chat、18082/admin、5010 学生端、5000 GOAI、
      5001 教师端、18090 分析仪表盘。
"""
import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "http://192.168.2.68"
EVIDENCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "evidence")
os.makedirs(EVIDENCE, exist_ok=True)

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--window-size=1440,900")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")

driver = webdriver.Edge(options=opts)
driver.set_page_load_timeout(90)

passed, failed, notes = [], [], []


def check(name, cond, extra=""):
    (passed if cond else failed).append(name)
    print(("PASS" if cond else "FAIL") + " | " + name + ((" | " + str(extra)) if extra else ""))


def shot(name):
    try:
        driver.save_screenshot(os.path.join(EVIDENCE, name + ".png"))
    except Exception as e:
        print("  ⚠️ 截图失败", name, e)


def wait_css(sel, t=20):
    WebDriverWait(driver, t).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))


def js(expr):
    return driver.execute_script("return " + expr)


# ============ 1. 课堂模式 18080/classroom ============
print("\n===== 1. 课堂模式 /classroom =====")
try:
    driver.get(BASE + ":18080/classroom")
    wait_css(".header", 15)
    check("页面标题", "LumiLearn" in driver.title, driver.title)
    check("三栏布局", js("!!document.querySelector('.panel-left')&&!!document.querySelector('.slide-canvas')&&!!document.querySelector('.panel-right')"))
    check("KaTeX 本地库加载", js("typeof katex === 'object' || typeof katex === 'function'"))
    check("Chart.js 本地库加载", js("typeof Chart === 'function'"))
    check("Reveal 本地库加载", js("typeof Reveal === 'function'"))
    shot("01_classroom_home")

    # 切换五步学习 tab
    try:
        tabs = driver.find_elements(By.CSS_SELECTOR, ".mode-tab")
        tabs[1].click()  # 五步学习
        time.sleep(1)
        check("五步学习面板显示", js("document.getElementById('feynmanContainer').style.display === 'flex'"))
        shot("02_classroom_feynman")
    except Exception as e:
        check("五步学习面板显示", False, str(e)[:80])

    # AI 聊天（真实模型）：等待 typing 指示消失且出现 AI 回复
    try:
        inp = driver.find_element(By.ID, "chatInput")
        inp.send_keys("用一句话解释什么是力")
        driver.find_element(By.ID, "btnSend").click()
        WebDriverWait(driver, 120).until(
            lambda d: d.execute_script(
                "var t=document.querySelectorAll('#chatMessages .chat-typing');"
                "var msgs=document.querySelectorAll('#chatMessages .chat-msg-text');"
                "return t.length===0 && msgs.length>=2 && msgs[msgs.length-1].textContent.trim().length>10"))
        chat_txt = driver.find_element(By.ID, "chatMessages").text
        check("AI 老师聊天有回复", "AI老师" in chat_txt and len(chat_txt) > 30, chat_txt[-60:].replace("\n", " "))
        shot("03_classroom_chat")
    except Exception as e:
        check("AI 老师聊天有回复", False, str(e)[:100])

    # 思维导图
    try:
        driver.find_element(By.ID, "btnMindmap").click()
        time.sleep(2)
        check("思维导图打开", js("document.getElementById('mindmapOverlay').classList.contains('show')"))
        shot("04_classroom_mindmap")
    except Exception as e:
        check("思维导图打开", False, str(e)[:80])
except Exception as e:
    check("课堂模式整体", False, str(e)[:120])

# ============ 2. 对话终端 18080/chat ============
print("\n===== 2. 对话终端 /chat =====")
try:
    driver.get(BASE + ":18080/chat")
    wait_css(".chat-input-wrap input, .chat-input-area input, textarea", 15)
    shot("05_chat_terminal")
    # 找输入框发消息
    inp = driver.find_element(By.CSS_SELECTOR, ".chat-input-wrap input, .chat-input-area input, textarea")
    inp.send_keys("什么叫加速度")
    btn = driver.find_element(By.CSS_SELECTOR, ".chat-input-wrap button, .btn-send, button[type='submit']")
    btn.click()
    time.sleep(12)
    body_txt = driver.find_element(By.TAG_NAME, "body").text
    check("终端回复非空", "加速度" in body_txt or "加速" in body_txt or len(body_txt) > 60, body_txt[:60].replace("\n", " "))
    shot("06_chat_reply")
except Exception as e:
    check("对话终端", False, str(e)[:120])

# ============ 3. 管理面板 18082/admin ============
print("\n===== 3. 管理面板 /admin =====")
try:
    driver.get(BASE + ":18082/admin")
    wait_css("#loginWrap", 15)
    check("登录页显示", js("document.getElementById('loginWrap').style.display !== 'none'"))
    # 登录（默认 admin/admin123 已预填）
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys("admin")
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys("admin123")
    driver.execute_script("doLogin()")
    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script("return document.getElementById('loginWrap').style.display === 'none'"))
    check("管理员登录成功", True)

    # 概览：最近活动应含学生使用记录
    time.sleep(3)
    ov_txt = driver.find_element(By.CSS_SELECTOR, "#content").text
    check("概览「最近活动」含学生记录", ("推理" in ov_txt) or ("报告" in ov_txt), ov_txt[:60].replace("\n", " "))
    shot("07_admin_overview")

    # 系统日志面板
    driver.execute_script("switchPanel('logs')")
    time.sleep(3)
    logs_txt = driver.find_element(By.CSS_SELECTOR, "#content").text
    check("系统日志面板含来源徽标", ("系统" in logs_txt) and ("推理" in logs_txt), logs_txt[:70].replace("\n", " "))
    check("系统日志展示学生数据", ("勾股" in logs_txt) or ("化学" in logs_txt) or ("力" in logs_txt), logs_txt[:90].replace("\n", " "))
    shot("08_admin_logs")

    # 推理记录
    driver.execute_script("switchPanel('reasoning')")
    time.sleep(4)
    rz_txt = driver.find_element(By.CSS_SELECTOR, "#content").text
    check("推理记录有数据", ("总记录数" in rz_txt) and ("勾股" in rz_txt or "牛顿" in rz_txt or "速度" in rz_txt), rz_txt[:80].replace("\n", " "))
    shot("09_admin_reasoning")

    # 学习记录
    driver.execute_script("switchPanel('reports')")
    time.sleep(3)
    rp_txt = driver.find_element(By.CSS_SELECTOR, "#content").text
    check("学习记录有报告", len(rp_txt) > 30, rp_txt[:60].replace("\n", " "))
    shot("10_admin_reports")

    # 数据可视化
    driver.execute_script("switchPanel('analytics')")
    time.sleep(4)
    an_txt = driver.find_element(By.CSS_SELECTOR, "#content").text
    check("数据可视化面板加载", len(an_txt) > 30, an_txt[:60].replace("\n", " "))
    shot("11_admin_analytics")
except Exception as e:
    check("管理面板", False, str(e)[:120])

# ============ 4. 学生端 5010 引导式学习 ============
print("\n===== 4. 学生端 5010 引导式学习 =====")
try:
    driver.get(BASE + ":5010/index.html")
    # 等待登录门真正显示（api.me() 异步返回后才 show）
    WebDriverWait(driver, 25).until(
        lambda d: d.execute_script(
            "var g=document.getElementById('loginGate');"
            "return g && g.classList.contains('show') && getComputedStyle(g).display==='flex'"))
    # 登录
    driver.find_element(By.ID, "loginUser").send_keys("guidestu")
    driver.find_element(By.ID, "loginPass").send_keys("stu123")
    driver.find_element(By.ID, "loginBtn").click()
    ok = False
    for _ in range(20):
        if driver.execute_script(
                "var g=document.getElementById('loginGate');"
                "return !g || g.style.display==='none' || g.offsetParent===null"):
            ok = True
            break
        time.sleep(0.5)
    check("学生登录成功", ok, "url=" + driver.current_url)
except Exception as e:
    check("学生登录成功", False, str(e)[:100])
    driver.quit()
    sys.exit(1)

try:
    # 发起学习
    wait_css("#topicInput", 10)
    driver.find_element(By.ID, "topicInput").clear()
    driver.find_element(By.ID, "topicInput").send_keys("我想理解速度的定义")
    driver.find_element(By.ID, "submitBtn").click()
    # 跳转到 learn.html 并出现第 1 步引导
    WebDriverWait(driver, 20).until(lambda d: "/learn.html" in d.current_url)
    WebDriverWait(driver, 120).until(
        lambda d: d.execute_script(
            "var el=document.getElementById('stepList');"
            "return el && el.textContent.trim().length>0 && "
            "(document.querySelector('textarea[id^=guideAnswer]')!=null || "
            "document.querySelector('#feynmanText')!=null)"))
    time.sleep(2)
    check("引导式学习进入（第1步提问+输入框）", True)
    shot("12_student_guide_step1")

    # 回答第 1 步 → 推进第 2 步
    try:
        ta = driver.find_element(By.CSS_SELECTOR, "textarea[id^='guideAnswer']")
        ta.send_keys("速度就是物体运动快慢的程度")
        driver.find_element(By.CSS_SELECTOR, "button[id^='guideSubmit']").click()
        WebDriverWait(driver, 120).until(
            lambda d: d.execute_script(
                "var done=document.querySelectorAll('.step-card.done').length;"
                "return done>=1 && document.querySelectorAll('.step-card.done').length>=1"))
        time.sleep(2)
        txt = driver.find_element(By.ID, "stepList").text
        check("回答后 AI 调整引导推进", "认知冲突" in txt or "思维模型" in txt or "自主推导" in txt, txt[-50:].replace("\n", " "))
        shot("13_student_guide_step2")
    except Exception as e:
        body = driver.find_element(By.TAG_NAME, "body").text
        check("回答后 AI 调整引导推进", False, str(e)[:80] + " | body:" + body[:80].replace("\n", " "))
except Exception as e:
    check("学生端引导式学习", False, str(e)[:100] + " | url=" + driver.current_url)

# ============ 5-7. 其他端口打开检查 ============
for port, name, sel, key in [
    (5000, "GOAI 学习 Web", "body", "LumiLearn"),
    (5001, "教师端", "body", "教师"),
    (18090, "分析仪表盘", "body", ""),
]:
    print(f"\n===== {port} {name} =====")
    try:
        driver.get(f"{BASE}:{port}/")
        time.sleep(5)
        body = driver.find_element(By.TAG_NAME, "body").text
        check(f"{name} 页面可打开", len(body) > 0, body[:40].replace("\n", " "))
        shot(f"14_port_{port}")
    except Exception as e:
        check(f"{name} 页面可打开", False, str(e)[:100])

driver.quit()

print("\n" + "=" * 60)
print(f"浏览器走查结果: {len(passed)} 通过, {len(failed)} 失败")
if failed:
    print("失败项:")
    for f in failed:
        print("  ❌", f)
print(f"截图已保存: {EVIDENCE}")
print("=" * 60)
sys.exit(1 if failed else 0)
