#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn GOAI Agent — Web Demo
====================================
Flask后端 + 单页前端，评委通过浏览器直接体验

运行方式：
  python goai_web.py
  浏览器打开 http://localhost:5000

API端点：
  POST /api/learn — 提交学习目标，返回学习报告
  GET  /api/status — Agent状态
  POST /api/chat — 对话式交互
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template_string
from goai_agent import LumiLearnAgent, TaskUnderstanding, FlowOrchestrator

app = Flask(__name__)

# 全局Agent实例（Ollama 地址通过环境变量 OLLAMA_URL 配置，见 .env.example）
agent = LumiLearnAgent()


# ============================================================
# HTML模板
# ============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LumiLearn AI 教官 — GOAI 教育智能体</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
                 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
    background: #f8fafc;
    color: #1e293b;
    min-height: 100vh;
  }

  /* 顶栏 */
  .header {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  .header h1 { font-size: 20px; font-weight: 600; }
  .header .subtitle { font-size: 12px; opacity: 0.9; margin-top: 2px; }
  .header .status { font-size: 12px; display: flex; align-items: center; gap: 6px; }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #4ade80;
    display: inline-block;
  }
  .status-dot.offline { background: #fbbf24; }

  /* 主容器 */
  .container { max-width: 900px; margin: 0 auto; padding: 24px 16px; }

  /* 输入区域 */
  .input-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  .input-section label {
    font-size: 14px;
    font-weight: 500;
    color: #475569;
    display: block;
    margin-bottom: 8px;
  }
  .input-row { display: flex; gap: 10px; }
  .input-row input {
    flex: 1;
    padding: 12px 16px;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s;
  }
  .input-row input:focus { border-color: #6366f1; }
  .input-row button {
    padding: 12px 24px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    transition: transform 0.1s, box-shadow 0.2s;
  }
  .input-row button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(99,102,241,0.4);
  }
  .input-row button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  /* 快捷示例 */
  .examples { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
  .example-tag {
    padding: 4px 12px;
    background: #f1f5f9;
    border-radius: 16px;
    font-size: 12px;
    color: #64748b;
    cursor: pointer;
    transition: all 0.2s;
  }
  .example-tag:hover { background: #e0e7ff; color: #6366f1; }

  /* 进度区域 */
  .progress-section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: none;
  }
  .progress-section.active { display: block; }
  .progress-title { font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 12px; }
  .progress-steps { display: flex; gap: 8px; }
  .progress-step {
    flex: 1;
    text-align: center;
    padding: 8px 4px;
    border-radius: 8px;
    font-size: 12px;
    transition: all 0.3s;
    background: #f1f5f9;
    color: #94a3b8;
  }
  .progress-step.active { background: #e0e7ff; color: #6366f1; font-weight: 500; }
  .progress-step.done { background: #dcfce7; color: #16a34a; }
  .progress-step .step-icon { font-size: 18px; margin-bottom: 4px; }

  /* 报告区域 */
  .report-section {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: none;
  }
  .report-section.active { display: block; }
  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #e2e8f0;
  }
  .report-header h2 { font-size: 18px; color: #1e293b; }
  .report-meta { font-size: 12px; color: #94a3b8; }

  /* 报告内容 */
  .report-section-full { margin-bottom: 20px; }
  .section-title {
    font-size: 14px;
    font-weight: 600;
    color: #475569;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .section-title .icon { font-size: 16px; }

  /* 任务理解卡片 */
  .task-card {
    background: #f8fafc;
    border-radius: 8px;
    padding: 12px 16px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
  }
  .task-item { text-align: center; }
  .task-item .label { font-size: 11px; color: #94a3b8; margin-bottom: 2px; }
  .task-item .value { font-size: 14px; font-weight: 500; color: #334155; }

  /* 教学步骤 */
  .teach-steps { display: flex; flex-direction: column; gap: 8px; }
  .teach-step {
    display: flex;
    gap: 12px;
    padding: 10px 14px;
    background: #f8fafc;
    border-radius: 8px;
    border-left: 3px solid #e2e8f0;
  }
  .teach-step.done { border-left-color: #16a34a; }
  .teach-step .step-num {
    width: 24px; height: 24px;
    border-radius: 50%;
    background: #e2e8f0;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 600;
    flex-shrink: 0;
  }
  .teach-step.done .step-num { background: #16a34a; color: white; }
  .teach-step .step-content { flex: 1; }
  .teach-step .step-name { font-size: 13px; font-weight: 500; color: #334155; }
  .teach-step .step-detail {
    font-size: 12px; color: #64748b; margin-top: 2px;
    max-height: 60px; overflow: hidden;
  }

  /* 评估区域 */
  .assessment-box {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .assessment-item {
    flex: 1;
    min-width: 150px;
    background: #f8fafc;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }
  .assessment-item .score { font-size: 24px; font-weight: 700; color: #6366f1; }
  .assessment-item .label { font-size: 11px; color: #94a3b8; margin-top: 2px; }

  /* 建议列表 */
  .suggestion-list { list-style: none; }
  .suggestion-list li {
    padding: 8px 12px;
    background: #f8fafc;
    border-radius: 6px;
    margin-bottom: 6px;
    font-size: 13px;
    color: #475569;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .suggestion-list li::before { content: "→"; color: #6366f1; font-weight: 600; }

  /* 页脚 */
  .footer {
    text-align: center;
    padding: 20px;
    color: #94a3b8;
    font-size: 12px;
  }

  /* 加载动画 */
  .spinner {
    display: inline-block;
    width: 16px; height: 16px;
    border: 2px solid #e2e8f0;
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* 响应式 */
  @media (max-width: 600px) {
    .progress-steps { flex-wrap: wrap; }
    .input-row { flex-direction: column; }
    .header { flex-direction: column; gap: 8px; }
  }
</style>
</head>
<body>

<!-- 顶栏 -->
<header class="header">
  <div>
    <h1>🎓 LumiLearn AI 教官</h1>
    <div class="subtitle">教育智能体 · GOAI 无界应用赛道参赛作品</div>
  </div>
  <div class="status">
    <span class="status-dot" id="statusDot"></span>
    <span id="statusText">就绪</span>
  </div>
</header>

<!-- 主容器 -->
<div class="container">

  <!-- 输入区域 -->
  <div class="input-section">
    <label>📝 输入你的学习目标</label>
    <div class="input-row">
      <input type="text" id="topicInput" placeholder="例如：我想理解函数的单调性"
             onkeypress="if(event.key==='Enter')startLearning()">
      <button id="startBtn" onclick="startLearning()">
        <span id="btnText">开始学习</span>
      </button>
    </div>
    <div class="examples">
      <span class="example-tag" onclick="setTopic('我想理解函数的单调性')">函数的单调性</span>
      <span class="example-tag" onclick="setTopic('帮我复习牛顿第二定律')">牛顿第二定律</span>
      <span class="example-tag" onclick="setTopic('化学平衡移动原理')">化学平衡移动</span>
      <span class="example-tag" onclick="setTopic('英语定语从句用法')">定语从句</span>
      <span class="example-tag" onclick="setTopic('勾股定理')">勾股定理</span>
    </div>
  </div>

  <!-- 进度区域 -->
  <div class="progress-section" id="progressSection">
    <div class="progress-title" id="progressTitle">正在处理...</div>
    <div class="progress-steps">
      <div class="progress-step" id="step1">
        <div class="step-icon">🔍</div>
        <div>任务理解</div>
      </div>
      <div class="progress-step" id="step2">
        <div class="step-icon">📋</div>
        <div>流程编排</div>
      </div>
      <div class="progress-step" id="step3">
        <div class="step-icon">🤖</div>
        <div>工具调用</div>
      </div>
      <div class="progress-step" id="step4">
        <div class="step-icon">📊</div>
        <div>结果交付</div>
      </div>
    </div>
  </div>

  <!-- 报告区域 -->
  <div class="report-section" id="reportSection">
    <div class="report-header">
      <h2 id="reportTitle">学习报告</h2>
      <span class="report-meta" id="reportMeta"></span>
    </div>

    <!-- 任务理解 -->
    <div class="report-section-full">
      <div class="section-title"><span class="icon">🔍</span> 任务理解</div>
      <div class="task-card" id="taskCard"></div>
    </div>

    <!-- 教学流程 -->
    <div class="report-section-full">
      <div class="section-title"><span class="icon">📚</span> 教学流程（费曼五步法）</div>
      <div class="teach-steps" id="teachSteps"></div>
    </div>

    <!-- 掌握度评估 -->
    <div class="report-section-full">
      <div class="section-title"><span class="icon">📈</span> 掌握度评估</div>
      <div class="assessment-box" id="assessmentBox"></div>
    </div>

    <!-- 薄弱点分析 -->
    <div class="report-section-full">
      <div class="section-title"><span class="icon">⚠️</span> 薄弱点分析</div>
      <ul class="suggestion-list" id="weakPointsList"></ul>
    </div>

    <!-- 下一步建议 -->
    <div class="report-section-full">
      <div class="section-title"><span class="icon">💡</span> 下一步建议</div>
      <ul class="suggestion-list" id="nextStepsList"></ul>
    </div>
  </div>

</div>

<!-- 页脚 -->
<div class="footer">
  LumiLearn AI 教官 · 教育智能体 · 由高一学生 LumiLearn 开发 · GOAI 无界应用赛道参赛作品
</div>

<script>
// 全局状态
let isProcessing = false;

// 设置主题
function setTopic(topic) {
  document.getElementById('topicInput').value = topic;
  startLearning();
}

// 开始学习
async function startLearning() {
  const topic = document.getElementById('topicInput').value.trim();
  if (!topic || isProcessing) return;

  isProcessing = true;
  document.getElementById('startBtn').disabled = true;
  document.getElementById('btnText').innerHTML = '<span class="spinner"></span>';
  document.getElementById('reportSection').classList.remove('active');

  // 显示进度区域
  const progressSection = document.getElementById('progressSection');
  progressSection.classList.add('active');

  // 重置步骤
  for (let i = 1; i <= 4; i++) {
    const step = document.getElementById('step' + i);
    step.className = 'progress-step';
  }

  try {
    // 模拟进度动画
    await animateProgress();

    // 调用API
    const response = await fetch('/api/learn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topic }),
    });

    const report = await response.json();

    // 渲染报告
    renderReport(report);

  } catch (err) {
    console.error('Error:', err);
    alert('请求失败：' + err.message);
  } finally {
    isProcessing = false;
    document.getElementById('startBtn').disabled = false;
    document.getElementById('btnText').textContent = '开始学习';
    progressSection.classList.remove('active');
  }
}

// 进度动画
async function animateProgress() {
  const steps = ['step1', 'step2', 'step3', 'step4'];
  for (let i = 0; i < steps.length; i++) {
    document.getElementById(steps[i]).classList.add('active');
    document.getElementById('progressTitle').textContent =
      ['任务理解中...', '生成教学流程...', '执行教学（调用AI模型）...', '生成学习报告...'][i];
    await sleep(600);
    document.getElementById(steps[i]).classList.remove('active');
    document.getElementById(steps[i]).classList.add('done');
  }
  await sleep(200);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// 渲染报告
function renderReport(report) {
  // 标题
  document.getElementById('reportTitle').textContent = report.title || '学习报告';
  document.getElementById('reportMeta').textContent = report.generated_at || '';

  // 任务理解
  const task = report.task_understanding || {};
  document.getElementById('taskCard').innerHTML = `
    <div class="task-item"><div class="label">学科</div><div class="value">${task.subject || '-'}</div></div>
    <div class="task-item"><div class="label">类型</div><div class="value">${task.topic_type || '-'}</div></div>
    <div class="task-item"><div class="label">难度</div><div class="value">${task.difficulty || '-'}</div></div>
    <div class="task-item"><div class="label">学习类型</div><div class="value">${task.learning_type || '-'}</div></div>
    <div class="task-item"><div class="label">置信度</div><div class="value">${((task.confidence || 0) * 100).toFixed(0)}%</div></div>
  `;

  // 教学步骤
  const steps = (report.teaching_flow?.steps_detail || []);
  const stepNames = ['现象引入', '认知冲突', '思维模型', '自主推导', '费曼测试'];
  document.getElementById('teachSteps').innerHTML = steps.map((s, i) => `
    <div class="teach-step ${s.success ? 'done' : ''}">
      <div class="step-num">${s.success ? '✓' : i + 1}</div>
      <div class="step-content">
        <div class="step-name">${stepNames[i] || s.name || ('步骤' + (i + 1))}</div>
        <div class="step-detail">${(s.content || '').substring(0, 100)}...</div>
      </div>
    </div>
  `).join('');

  // 掌握度评估
  const mastery = report.mastery_assessment || {};
  document.getElementById('assessmentBox').innerHTML = `
    <div class="assessment-item">
      <div class="score">${mastery.score || 0}</div>
      <div class="label">综合评分</div>
    </div>
    <div class="assessment-item">
      <div class="score" style="font-size:16px">${mastery.level || '-'}</div>
      <div class="label">掌握等级</div>
    </div>
    <div class="assessment-item">
      <div class="score" style="font-size:14px">${mastery.emoji || ''}</div>
      <div class="label">${mastery.summary || ''}</div>
    </div>
  `;

  // 薄弱点
  document.getElementById('weakPointsList').innerHTML =
    (report.weak_points || []).map(wp => `<li>${wp}</li>`).join('');

  // 下一步建议
  document.getElementById('nextStepsList').innerHTML =
    (report.next_steps || []).map(ns => `<li>${ns}</li>`).join('');

  // 显示报告
  document.getElementById('reportSection').classList.add('active');
}
</script>

</body>
</html>
"""


# ============================================================
# API路由
# ============================================================
def get_local_ip():
    """获取局域网 IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


@app.route('/')
def index():
    """服务仪表盘首页"""
    local_ip = get_local_ip()

    services = [
        ("🎓 GOAI 学习智能体", "/learn", "5000", "AI 教官问答 + 费曼教学法五步学习", "在线"),
        ("🖥️ 框架终端", f"http://{local_ip}:18080/", "18080", "LumiLearn 全功能终端界面", "在线" if check_port(18080) else "离线"),
        ("🔌 REST API", f"http://{local_ip}:18081/", "18081", "纯 API 服务，供第三方集成", "在线" if check_port(18081) else "离线"),
        ("🤖 模型管理", f"http://{local_ip}:18082/", "18082", "模型列表、切换、健康检查", "在线" if check_port(18082) else "离线"),
    ]

    dashboard_html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LumiLearn 服务仪表盘</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
                     'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
        background: #0f172a;
        color: #e2e8f0;
        min-height: 100vh;
      }
      .header {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%);
        padding: 24px 32px;
        border-bottom: 1px solid #334155;
      }
      .header h1 { font-size: 28px; font-weight: 700; color: #f8fafc; }
      .header h1 span { color: #818cf8; }
      .header .sub { font-size: 14px; color: #94a3b8; margin-top: 6px; }
      .header .ip-badge {
        display: inline-block; background: #1e293b; color: #818cf8;
        padding: 4px 12px; border-radius: 20px; font-size: 13px;
        margin-top: 8px; border: 1px solid #334155;
      }
      .container { max-width: 1000px; margin: 0 auto; padding: 32px 24px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; }
      .card {
        background: #1e293b; border-radius: 16px; padding: 24px;
        border: 1px solid #334155; transition: all 0.2s;
        position: relative; overflow: hidden;
      }
      .card:hover { border-color: #6366f1; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(99,102,241,0.15); }
      .card .icon { font-size: 32px; margin-bottom: 12px; }
      .card h3 { font-size: 18px; color: #f1f5f9; margin-bottom: 4px; }
      .card .port { font-size: 12px; color: #64748b; font-family: monospace; }
      .card .desc { font-size: 13px; color: #94a3b8; margin: 8px 0 16px; line-height: 1.5; }
      .card .status {
        display: inline-block; font-size: 12px; padding: 3px 10px;
        border-radius: 12px; font-weight: 500;
      }
      .status-online { background: #065f46; color: #6ee7b7; }
      .status-offline { background: #7f1d1d; color: #fca5a5; }
      .card a {
        display: inline-block; margin-top: 12px; padding: 8px 20px;
        background: #312e81; color: #c7d2fe; border-radius: 8px;
        text-decoration: none; font-size: 13px; font-weight: 500;
        transition: all 0.2s;
      }
      .card a:hover { background: #4338ca; color: #e0e7ff; }
      .quick-links {
        margin-top: 32px; background: #1e293b; border-radius: 16px;
        padding: 24px; border: 1px solid #334155;
      }
      .quick-links h3 { font-size: 16px; color: #f1f5f9; margin-bottom: 16px; }
      .quick-links code {
        display: block; background: #0f172a; padding: 10px 16px;
        border-radius: 8px; font-size: 13px; color: #a5b4fc;
        margin-bottom: 8px; font-family: 'Cascadia Code', 'Fira Code', monospace;
      }
      .quick-links .label { color: #94a3b8; font-size: 12px; margin-bottom: 2px; }
      .footer { text-align: center; padding: 32px; color: #475569; font-size: 13px; }
      .footer a { color: #818cf8; text-decoration: none; }
    </style>
    </head>
    <body>
      <div class="header">
        <h1>LumiLearn <span>服务仪表盘</span></h1>
        <div class="sub">全面配置 — 全部服务已开放</div>
        <div class="ip-badge">🌐 本机 IP: """ + local_ip + """</div>
      </div>
      <div class="container">
        <div class="grid">
    """
    for icon, path, port, desc, status in services:
        status_class = "status-online" if status == "在线" else "status-offline"
        link = path if path.startswith("http") else path
        dashboard_html += f"""
          <div class="card">
            <div class="icon">{icon.split()[0]}</div>
            <h3>{' '.join(icon.split()[1:])}</h3>
            <div class="port">端口 {port}</div>
            <div class="desc">{desc}</div>
            <span class="status {status_class}">● {status}</span>
            <a href="{link}" target="_blank">🚀 打开服务</a>
          </div>
        """
    dashboard_html += """
        </div>
        <div class="quick-links">
          <h3>📋 快速参考</h3>
          <div class="label">GOAI 学习 API (POST)</div>
          <code>curl -X POST http://localhost:5000/api/learn -H "Content-Type: application/json" -d '{"topic":"勾股定理","subject":"数学"}'</code>
          <div class="label">框架健康检查 (GET)</div>
          <code>curl http://localhost:18080/health</code>
          <div class="label">框架 API 状态 (GET)</div>
          <code>curl http://localhost:18080/api/status</code>
          <div class="label">模型列表 (GET)</div>
          <code>curl http://localhost:18080/api/models</code>
          <div class="label">费曼教学 API (POST)</div>
          <code>curl -X POST http://localhost:18080/api/feynman/explain -H "Content-Type: application/json" -d '{"topic":"勾股定理"}'</code>
        </div>
        <div class="footer">
          LumiLearn · <a href="https://github.com/your-username/lumilearn" target="_blank">GitHub</a>
        </div>
      </div>
    </body>
    </html>
    """
    return dashboard_html


def check_port(port):
    """检查端口是否在监听"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except:
        return False


@app.route('/learn')
def learn_page():
    """GOAI 学习智能体页面"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/learn', methods=['POST'])
def api_learn():
    """提交学习目标，返回学习报告"""
    data = request.get_json()
    topic = data.get('topic', '').strip()

    if not topic:
        return jsonify({'error': '请提供学习目标'}), 400

    try:
        report = agent.run(topic, interactive=False)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """获取Agent状态"""
    return jsonify(agent.get_status())


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """对话式交互（预留扩展）"""
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    tu = TaskUnderstanding()
    task = tu.understand(message)
    return jsonify({'reply': f"已识别你的学习目标：{task['core_topic']}（{task['subject']}/{task['difficulty']}）", 'task': task})


# ============================================================
# 启动
# ============================================================
def main():
    local_ip = get_local_ip()
    print("\n" + "=" * 60)
    print("  🎓 LumiLearn AI 教官 — 服务仪表盘")
    print("  GOAI 无界应用赛道参赛作品")
    print("=" * 60)
    print(f"  📊 仪表盘首页:  http://localhost:5000")
    print(f"  🎓 学习智能体:  http://localhost:5000/learn")
    print(f"  🖥️ 框架终端:    http://{local_ip}:18080")
    print(f"  🔌 REST API:    http://{local_ip}:18081")
    print(f"  🤖 模型管理:    http://{local_ip}:18082")
    print(f"  📡 API地址:     http://localhost:5000/api/learn")
    print(f"  🚀 Ollama状态:  {'可用' if agent.tool_caller.available else '不可用（兜底模式）'}")
    print("=" * 60)
    print("  按 Ctrl+C 停止服务\n")

    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
