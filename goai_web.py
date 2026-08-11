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

from flask import (Flask, request, jsonify, render_template_string, session,
                   redirect, url_for, send_from_directory, abort)
from goai_agent import LumiLearnAgent, TaskUnderstanding, FlowOrchestrator

# 连接 Framework 数据库（与 18080 管理端共享 lumilearn.db）
from framework.database import db
db.init()

# 多轮对话持久化（chat_history，惰性连接，共享同一 lumilearn.db）
from framework.services.conversation_store import conversation_store as conv_store

app = Flask(__name__)
app.secret_key = os.environ.get("GOAI_SECRET_KEY", "lumilearn-goai-web-secret")

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

  /* 登录界面 */
  .login-overlay {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(6px);
    display: flex; align-items: center; justify-content: center;
    z-index: 1000;
  }
  .login-box {
    background: white; border-radius: 16px; padding: 32px;
    width: 340px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  }
  .login-box h2 { font-size: 20px; color: #1e293b; margin-bottom: 20px; text-align: center; }
  .login-box input {
    width: 100%; padding: 12px 16px; margin-bottom: 12px;
    border: 1.5px solid #e2e8f0; border-radius: 8px; font-size: 15px; outline: none;
  }
  .login-box input:focus { border-color: #6366f1; }
  .login-box button {
    width: 100%; padding: 12px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white; border: none; border-radius: 8px; font-size: 15px; font-weight: 500;
    cursor: pointer; margin-top: 4px;
  }
  .login-error { color: #ef4444; font-size: 13px; margin-bottom: 10px; min-height: 18px; text-align: center; }
  .login-hint { font-size: 12px; color: #94a3b8; text-align: center; margin-top: 14px; }

  /* 学习历史 */
  .history-section {
    background: white; border-radius: 12px; padding: 20px;
    margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: none;
  }
  .history-section.active { display: block; }
  .history-section h3 { font-size: 16px; color: #334155; margin-bottom: 12px; }
  .history-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px;
    margin-bottom: 8px; cursor: pointer; transition: all 0.2s;
  }
  .history-item:hover { border-color: #6366f1; background: #f8fafc; }
  .history-item .h-topic { font-size: 14px; font-weight: 500; color: #334155; }
  .history-item .h-meta { font-size: 12px; color: #94a3b8; }
  .history-item .h-score {
    font-size: 14px; font-weight: 700; color: #6366f1;
    background: #e0e7ff; padding: 4px 10px; border-radius: 12px;
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
  <div class="header-right" style="display:flex;align-items:center;gap:14px;">
    <div class="user-info" id="userInfo" style="font-size:13px;display:none;">
      <span id="userName"></span>
      <button onclick="logout()" style="margin-left:8px;padding:4px 10px;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:6px;color:white;cursor:pointer;font-size:12px;">退出</button>
    </div>
    <button id="historyBtn" onclick="toggleHistory()" style="display:none;padding:6px 12px;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:6px;color:white;cursor:pointer;font-size:12px;">📚 学习历史</button>
    <div class="status">
      <span class="status-dot" id="statusDot"></span>
      <span id="statusText">就绪</span>
    </div>
  </div>
</header>

<!-- 登录界面 -->
<div class="login-overlay" id="loginOverlay">
  <div class="login-box">
    <h2>🔐 登录 LumiLearn</h2>
    <div class="login-error" id="loginError"></div>
    <input type="text" id="loginUsername" placeholder="用户名" autocomplete="username">
    <input type="password" id="loginPassword" placeholder="密码" autocomplete="current-password"
           onkeypress="if(event.key==='Enter')doLogin()">
    <button onclick="doLogin()">登 录</button>
    <div class="login-hint">账号由管理员在管理面板 (18080/admin) 创建</div>
  </div>
</div>

<!-- 主容器 -->
<div class="container">

  <!-- 学习历史 -->
  <div class="history-section" id="historySection">
    <h3>📚 我的学习历史</h3>
    <div id="historyList" style="color:#94a3b8;font-size:13px;">加载中...</div>
  </div>

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
  LumiLearn AI 教官 · 教育智能体 · 由一名高中生开发者开发 · GOAI 无界应用赛道参赛作品
</div>

<script>
// 全局状态
let isProcessing = false;

// ---------- 登录认证 ----------
async function checkLogin() {
  try {
    const resp = await fetch('/api/me');
    const data = await resp.json();
    if (data.success) {
      document.getElementById('loginOverlay').style.display = 'none';
      document.getElementById('userInfo').style.display = 'flex';
      document.getElementById('historyBtn').style.display = 'inline-block';
      document.getElementById('userName').textContent = `👤 ${data.user.name} (${data.user.role === 'teacher' ? '教师' : '学生'})`;
      loadHistory();
      return true;
    }
  } catch (e) { /* 忽略 */ }
  document.getElementById('loginOverlay').style.display = 'flex';
  return false;
}

async function doLogin() {
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  document.getElementById('loginError').textContent = '';
  if (!username || !password) {
    document.getElementById('loginError').textContent = '请输入用户名和密码';
    return;
  }
  try {
    const resp = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (!data.success) {
      document.getElementById('loginError').textContent = data.error || '登录失败';
      return;
    }
    document.getElementById('loginPassword').value = '';
    await checkLogin();
  } catch (e) {
    document.getElementById('loginError').textContent = '登录请求失败: ' + e.message;
  }
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' }).catch(() => {});
  location.reload();
}

// ---------- 学习历史 ----------
async function loadHistory() {
  try {
    const resp = await fetch('/api/history');
    const data = await resp.json();
    const list = document.getElementById('historyList');
    if (!data.success) { list.textContent = '加载失败'; return; }
    const reports = data.reports || [];
    if (!reports.length) {
      list.textContent = '暂无学习记录，输入学习目标开始你的第一次学习吧！';
      return;
    }
    list.innerHTML = '';
    reports.forEach(r => {
      const div = document.createElement('div');
      div.className = 'history-item';
      const s = r.summary || {};
      div.innerHTML = `
        <div>
          <div class="h-topic">${s.core_topic || r.topic}</div>
          <div class="h-meta">${s.subject || ''} · ${s.generated_at || r.created_at || ''}</div>
        </div>
        <div class="h-score">${s.score ?? '-'}分</div>`;
      div.onclick = () => showSavedReport(r);
      list.appendChild(div);
    });
  } catch (e) {
    document.getElementById('historyList').textContent = '加载失败: ' + e.message;
  }
}

function toggleHistory() {
  const sec = document.getElementById('historySection');
  const open = sec.classList.toggle('active');
  if (open) loadHistory();
  document.getElementById('historyBtn').textContent = open ? '📚 收起历史' : '📚 学习历史';
}

function showSavedReport(r) {
  const rep = r.report || {};
  const task = rep.task_understanding || {};
  const mastery = rep.mastery_assessment || {};
  const steps = rep.teaching_flow?.steps_detail || [];
  const stepNames = ['现象引入', '认知冲突', '思维模型', '自主推导', '费曼测试'];
  document.getElementById('reportTitle').textContent = rep.title || '学习报告';
  document.getElementById('reportMeta').textContent = (rep.generated_at || '') + ' · 历史记录';
  document.getElementById('taskCard').innerHTML = `
    <div class="task-item"><div class="label">学科</div><div class="value">${task.subject || '-'}</div></div>
    <div class="task-item"><div class="label">类型</div><div class="value">${task.topic_type || '-'}</div></div>
    <div class="task-item"><div class="label">难度</div><div class="value">${task.difficulty || '-'}</div></div>
    <div class="task-item"><div class="label">学习类型</div><div class="value">${task.learning_type || '-'}</div></div>
    <div class="task-item"><div class="label">置信度</div><div class="value">${((task.confidence || 0) * 100).toFixed(0)}%</div></div>`;
  document.getElementById('teachSteps').innerHTML = steps.map((s, i) => `
    <div class="teach-step ${s.success ? 'done' : ''}">
      <div class="step-num">${s.success ? '✓' : i + 1}</div>
      <div class="step-content">
        <div class="step-name">${stepNames[i] || s.name || ('步骤' + (i + 1))}</div>
        <div class="step-detail">${(s.content || '').substring(0, 100)}...</div>
      </div>
    </div>`).join('');
  document.getElementById('assessmentBox').innerHTML = `
    <div class="assessment-item"><div class="score">${mastery.score || 0}</div><div class="label">综合评分</div></div>
    <div class="assessment-item"><div class="score" style="font-size:16px">${mastery.level || '-'}</div><div class="label">掌握等级</div></div>
    <div class="assessment-item"><div class="score" style="font-size:14px">${mastery.emoji || ''}</div><div class="label">${mastery.summary || ''}</div></div>`;
  document.getElementById('weakPointsList').innerHTML = (rep.weak_points || []).map(wp => `<li>${wp}</li>`).join('');
  document.getElementById('nextStepsList').innerHTML = (rep.next_steps || []).map(ns => `<li>${ns}</li>`).join('');
  document.getElementById('reportSection').classList.add('active');
  window.scrollTo({ top: document.getElementById('reportSection').offsetTop - 80, behavior: 'smooth' });
}

// 设置主题
function setTopic(topic) {
  document.getElementById('topicInput').value = topic;
  startLearning();
}

// 开始学习
async function startLearning() {
  const topic = document.getElementById('topicInput').value.trim();
  if (!topic || isProcessing) return;
  // 未登录时要求先登录
  const me = await fetch('/api/me').then(r => r.json()).catch(() => ({ success: false }));
  if (!me.success) { toast_('请先登录后再开始学习'); return; }

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
    if (!response.ok || report.error) {
      throw new Error(report.error || '生成失败');
    }

    // 渲染报告
    renderReport(report);
    // 刷新历史
    loadHistory();

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

function toast_(msg) {
  const old = document.getElementById('toastBox');
  if (old) old.remove();
  const t = document.createElement('div');
  t.id = 'toastBox';
  t.style.cssText = 'position:fixed;top:80px;left:50%;transform:translateX(-50%);background:#f1f5f9;color:#475569;padding:10px 20px;border-radius:8px;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,0.1);z-index:999;';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
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

// 页面加载时检查登录状态
checkLogin();
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
    current_user = _get_current_user()
    user_badge = f"👤 {current_user['name']} ({'教师' if current_user['role'] == 'teacher' else '学生'})" if current_user else "未登录"

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
        <div class="user-badge" style="display:inline-block;background:#312e81;color:#c7d2fe;padding:4px 14px;border-radius:20px;font-size:13px;margin-top:8px;border:1px solid #4338ca;">""" + user_badge + """</div>
        <a href="/learn" style="display:inline-block;margin-left:10px;background:#4338ca;color:white;padding:4px 14px;border-radius:20px;font-size:13px;text-decoration:none;margin-top:8px;">🚀 开始学习</a>
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
          LumiLearn · <a href="https://github.com/k3234/lumilearn" target="_blank">GitHub</a>
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


# ---------- 用户认证 ----------

@app.route('/api/login', methods=['POST'])
def api_login():
    """用户登录（使用 Framework 数据库账号）"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'success': False, 'error': '请输入用户名和密码'}), 400
    user = db.verify_user_login(username, password)
    if not user:
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
    session['user_id'] = user['id']
    return jsonify({
        'success': True,
        'user': {'id': user['id'], 'name': user['name'], 'role': user['role']},
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/me')
def api_me():
    """获取当前登录用户"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401
    user = db.get_user(user_id)
    if not user:
        session.clear()
        return jsonify({'success': False, 'error': '用户不存在'}), 401
    return jsonify({'success': True, 'user': {
        'id': user['id'], 'name': user['name'], 'role': user['role'],
        'username': user.get('username', ''),
    }})


def _get_current_user():
    """获取当前登录用户，未登录返回 None"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.get_user(user_id)


@app.route('/api/history')
def api_history():
    """获取当前用户的学习历史"""
    user = _get_current_user()
    if not user:
        return jsonify({'success': False, 'error': '未登录'}), 401
    reports = db.get_learning_reports(user_id=user['id'], limit=30)
    for r in reports:
        rep = r.get('report', {})
        r['summary'] = {
            'core_topic': (rep.get('task_understanding') or {}).get('core_topic', r['topic']),
            'subject': (rep.get('task_understanding') or {}).get('subject', ''),
            'generated_at': rep.get('generated_at', ''),
            'score': (rep.get('mastery_assessment') or {}).get('score', 0),
        }
        # 保留完整 report 供前端查看
    return jsonify({'success': True, 'reports': reports})


@app.route('/api/learn', methods=['POST'])
def api_learn():
    """提交学习目标，返回学习报告（需登录，报告自动保存到数据库）"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401

    data = request.get_json()
    topic = data.get('topic', '').strip()

    if not topic:
        return jsonify({'error': '请提供学习目标'}), 400

    try:
        report = agent.run(topic, interactive=False, user_id=user['id'])
        # 保存学习报告到共享数据库（Admin 面板可见）
        score = (report.get('mastery_assessment') or {}).get('score', 0)
        db.add_learning_report(user['id'], topic, report, score=score)
        report['user'] = {'id': user['id'], 'name': user['name']}
        # 多轮对话持久化：学习目标 + 报告摘要写入 chat_history
        try:
            sid = conv_store.create_session(topic, user_id=user['id'])
            conv_store.add_message(sid, "user", topic)
            summary = json.dumps({
                "mastery": score,
                "weak_points": (report.get('weak_points') or [])[:3],
            }, ensure_ascii=False)
            conv_store.add_message(sid, "assistant",
                                   f"学习报告已生成：{summary}",
                                   model=agent.tool_caller.preferred_model)
        except Exception:
            pass  # 持久化失败不影响主流程
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """获取Agent状态"""
    return jsonify(agent.get_status())


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """对话式交互（多轮消息自动持久化到 chat_history）"""
    user = _get_current_user()
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    tu = TaskUnderstanding()
    task = tu.understand(message)
    reply = f"已识别你的学习目标：{task['core_topic']}（{task['subject']}/{task['difficulty']}）"

    # 多轮对话持久化：登录用户消息 + 回复写入"对话式问答"会话
    try:
        if user:
            sid = _get_or_create_chat_session(user['id'])
            conv_store.add_message(sid, "user", message)
            conv_store.add_message(sid, "assistant", reply, model="task-understanding")
    except Exception:
        pass  # 持久化失败不影响主流程

    return jsonify({'reply': reply, 'task': task})


def _get_or_create_chat_session(user_id: int) -> int:
    """找到该用户最近的"对话式问答"会话，无则新建（保持多轮上下文连贯）。"""
    for s in conv_store.list_sessions(user_id=user_id, limit=20):
        if s["title"] == "对话式问答":
            return s["id"]
    return conv_store.create_session("对话式问答", user_id=user_id)


# ============================================================
# 对话历史（chat_history 多轮持久化查看）
# ============================================================
@app.route('/api/conversations')
def api_conversations():
    """列出当前用户的对话会话（含消息数与末条预览）"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401
    return jsonify({'success': True, 'sessions': conv_store.list_sessions(user_id=user['id'], limit=30)})


@app.route('/api/conversations/<int:session_id>')
def api_conversation_detail(session_id):
    """获取某会话的完整多轮消息"""
    user = _get_current_user()
    if not user:
        return jsonify({'error': '未登录，请先登录'}), 401
    s = conv_store.get_session(session_id)
    if not s or s["user_id"] != user["id"]:
        return jsonify({'error': '会话不存在'}), 404
    return jsonify({'success': True, 'session': s,
                    'messages': conv_store.get_messages(session_id)})


# ============================================================
# 学生端原型（静态交付，GOAI Web 内嵌访问）
# ============================================================
PROTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "prototypes", "student-learning-platform")


@app.route('/proto/')
def proto_index():
    return _send_proto("index.html")


@app.route('/proto/<path:filename>')
def proto_file(filename):
    return _send_proto(filename)


def _send_proto(filename):
    """安全发送原型静态文件（防路径穿越）"""
    safe = os.path.normpath(filename).lstrip("/\\")
    if ".." in safe.split(os.sep):
        abort(404)
    full = os.path.join(PROTO_DIR, safe)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(PROTO_DIR, safe)


# ============================================================
# 启动
# ============================================================
def _get_goai_port() -> int:
    """从 port_settings 读取 GOAI Web 端口（可被环境变量覆盖）"""
    env_port = os.environ.get("GOAI_PORT", "")
    if env_port.isdigit():
        return int(env_port)
    try:
        from framework.services.provider_service import get_provider_service
        cfg = get_provider_service().get_port_settings().get("goai_web", {})
        if cfg.get("port"):
            return int(cfg["port"])
    except Exception:
        pass
    return 5000


def main():
    local_ip = get_local_ip()
    port = _get_goai_port()
    print("\n" + "=" * 60)
    print("  🎓 LumiLearn AI 教官 — 服务仪表盘")
    print("  GOAI 无界应用赛道参赛作品")
    print("=" * 60)
    print(f"  📊 仪表盘首页:  http://localhost:{port}")
    print(f"  🎓 学习智能体:  http://localhost:{port}/learn")
    print(f"  🖥️ 框架终端:    http://{local_ip}:18080")
    print(f"  🔌 REST API:    http://{local_ip}:18081")
    print(f"  🤖 模型管理:    http://{local_ip}:18082")
    print(f"  📡 API地址:     http://localhost:{port}/api/learn")
    print(f"  🚀 Ollama状态:  {'可用' if agent.tool_caller.available else '不可用（兜底模式）'}")
    print("=" * 60)
    print("  按 Ctrl+C 停止服务\n")

    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
