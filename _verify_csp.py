# -*- coding: utf-8 -*-
"""用 Chrome headless 验证 CSP 修复效果（捕获 console 错误 + 渲染后 DOM）"""
import subprocess, sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.2.xx:18080/"

proc = subprocess.run(
    [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
     "--dump-dom", "--virtual-time-budget=8000", url],
    capture_output=True, timeout=60
)
dom = proc.stdout.decode("utf-8", errors="replace")
err = proc.stderr.decode("utf-8", errors="replace")

print(f"[DOM长度] {len(dom)}")
print(f"[STDERR长度] {len(err)}")

# 检查 CSP 违规
refused = [l for l in err.splitlines() if "Refused" in l or "Content Security Policy" in l]
print(f"[CSP违规条数] {len(refused)}")
for l in refused[:10]:
    print("  ", l[:200])

# 检查 DOM 中 JS 渲染痕迹（终端页面的 key 元素）
import re
checks = {
    "JS渲染body内容>5000": len(dom) > 5000,
    "含terminal-shell": "terminal-shell" in dom or "terminal" in dom.lower(),
    "含fetch代码引用": "api/status" in dom,
}
for k, v in checks.items():
    print(f"[{k}] {v}")

# 保存 DOM 供人工检查
with open("_dom_check.html", "w", encoding="utf-8") as f:
    f.write(dom)
print("[DOM已保存] _dom_check.html")
