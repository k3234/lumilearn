/* ============================================================
 * api.js — 双模式 API 层
 * 真实后端模式（window.__LUMILEARN_REAL__ = true，由 Student Portal 注入）：
 *   直接 fetch 同源真实接口，函数签名/返回 {code,data} 契约与 mock 完全一致。
 * 离线演示模式（无真实后端，如双击打开 / GOAI Web /proto/）：
 *   使用下方 mock 桩，带模拟延迟，保留 loading 态。
 * 集成点：真实后端实现见 student_portal.py，替换 mock 无需改动页面。
 * ============================================================ */

const REAL = window.__LUMILEARN_REAL__ === true;
const delay = (ms) => new Promise((res) => setTimeout(res, ms));
const _uid = (() => { let n = 1007; return () => "s-" + (n++); })();

/* 本地会话草稿（learn → report 传参），mock 模式下用 localStorage */
const SessionStore = {
  KEY: "ll_session",
  get draft() { try { return JSON.parse(localStorage.getItem(this.KEY) || "null"); } catch { return null; } },
  save(session) { localStorage.setItem(this.KEY, JSON.stringify(session)); },
  clear() { localStorage.removeItem(this.KEY); },
};

/* 真实后端请求封装：401 → 跳转登录 */
async function fetchJson(path, method, body) {
  const opt = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opt.body = JSON.stringify(body);
  const resp = await fetch(path, opt);
  let json = {};
  try { json = await resp.json(); } catch (e) { json = {}; }
  if (resp.status === 401 && path.indexOf("/api/auth/") !== 0 && !location.search.includes("need=login")) {
    location.href = "index.html?need=login";
    throw new Error("未登录");
  }
  return json;
}

/* 主题归一化：剥离常见意图前缀，命中文案库键 */
function normalizeTopic(topic) {
  var t = (topic || "").trim();
  ["我想理解", "我想学", "我想学习", "我要学", "帮我学习", "帮我理解", "帮我掌握",
   "帮我", "学习", "理解", "掌握", "复习", "什么是", "怎么学", "如何理解", "请讲解", "讲解"].forEach(function (p) {
    if (t.indexOf(p) === 0) t = t.slice(p.length);
  });
  return t.trim() || (topic || "").trim();
}

/* 从 mock 文案库取某主题的 5 步教学文案；不存在则用通用生成器 */
function buildSteps(topic, subject, difficulty) {
  var key = normalizeTopic(topic);
  var hit = DB.stepLibrary[key] || DB.stepLibrary[Object.keys(DB.stepLibrary).find(function (k) {
    return DB.stepLibrary[k].subject === subject && key.indexOf(k) !== -1;
  })];
  if (hit && hit.subject === subject) return hit.steps;
  return DB.fallbackSteps(topic, subject, difficulty);
}

const api = {
  /* ---------- 认证（仅真实后端模式使用） ---------- */

  /** POST /api/auth/login { username, password } */
  async login(username, password) {
    return fetchJson("/api/auth/login", "POST", { username, password });
  },

  /** GET /api/auth/me */
  async me() {
    return fetchJson("/api/auth/me", "GET");
  },

  /** POST /api/auth/logout */
  async logout() {
    return fetchJson("/api/auth/logout", "POST", {});
  },

  /* ---------- 学习流程 ---------- */

  /**
   * POST /api/learn/start  { topic, subject, difficulty }
   * 发起学习：编排调度 Agent 理解任务 → 生成费曼五步流程
   */
  async startLearning({ topic, subject, difficulty }) {
    if (REAL) return fetchJson("/api/learn/start", "POST", { topic, subject, difficulty });
    await delay(900);
    const id = _uid();
    const flow = buildSteps(topic, subject, difficulty).map((s, i) => ({
      step: i + 1, name: DB.STEP_NAMES[i], purpose: DB.STEP_PURPOSES[i], status: "pending",
    }));
    return {
      code: 0,
      data: {
        id, topic, subject, difficulty,
        createdAt: new Date().toLocaleString("zh-CN", { hour12: false }),
        status: "learning", model: "qwen2.5:7b",
        flow,
        agents: DB.agentDefs.map((a) => ({ ...a, status: "idle", calls: 0 })),
      },
    };
  },

  /**
   * POST /api/learn/step  { sessionId, step }
   * 执行某一教学步骤：费曼教学 Agent 生成内容 + 知识检索 Agent 注入上下文
   */
  async runStep({ sessionId, step }) {
    if (REAL) return fetchJson("/api/learn/step", "POST", { sessionId, step });
    await delay(650);
    const topic = SessionStore.draft?.topic || "函数的单调性";
    const subject = SessionStore.draft?.subject || "数学";
    const key = normalizeTopic(topic);
    const steps = buildSteps(topic, subject, SessionStore.draft?.difficulty || "高中");
    const def = steps[step - 1] || steps[0];
    const knowledgeHints = {
      "函数的单调性": ["定义域与区间", "图像上升/下降", "最值与极值"],
      "牛顿第二定律": ["力的合成与分解", "加速度与速度方向", "质量与惯性"],
      "化学平衡移动": ["勒夏特列原理", "平衡常数 K", "压强与浓度"],
      "光合作用": ["叶绿体结构", "光反应与暗反应", "ATP 与 NADPH"],
    };
    const hints = knowledgeHints[key] || ["核心概念", "典型例题", "易错点"];
    return {
      code: 0,
      data: {
        step,
        content: def.content,
        knowledge: hints,
        agents: [
          { id: "orchestrator", action: `分发步骤 ${step}「${DB.STEP_NAMES[step - 1]}」` },
          { id: "knowledge",    action: `检索「${key}」相关知识点 ${hints.length} 条` },
          { id: "feynman",      action: `生成「${DB.STEP_NAMES[step - 1]}」教学内容` },
        ],
      },
    };
  },

  /**
   * POST /api/learn/guide  { sessionId, answer?, level? }
   * 引导式学习：老师提问 → 学生自主回答 → 根据回答生成下一步引导。
   * 首次调用不带 answer（开始引导），之后每次带 answer（学生本轮回答）。
   */
  async guideStep({ sessionId, answer, level }) {
    const body = { sessionId };
    if (answer) body.answer = answer;
    if (level) body.level = level;
    if (REAL) return fetchJson("/api/learn/guide", "POST", body);
    await delay(700);
    const topic = SessionStore.draft?.topic || "函数的单调性";
    const steps = buildSteps(topic, SessionStore.draft?.subject || "数学", level || "高中");
    // mock 模式：按当前已引导的步骤数返回下一步（引导式单步）
    const count = SessionStore.guideCount || 0;
    const def = steps[count] || steps[0];
    SessionStore.guideCount = count + 1;
    return {
      code: 0,
      data: {
        step: count + 1,
        step_name: DB.STEP_NAMES[count] || "",
        content: def.content.slice(0, 160) + "\n\n（想一想：你能用自己的话回答这个问题吗？）",
        is_last: count + 1 >= 5,
        model_used: "mock",
        progress: { current: count + 1, total: 5 },
      },
    };
  },

  /**
   * POST /api/learn/feynman-test  { sessionId, text }
   * 费曼测试：评测 Agent 对学生的 30 秒讲解打分（五维）
   */
  async submitFeynmanTest({ sessionId, text }) {
    if (REAL) return fetchJson("/api/learn/feynman-test", "POST", { sessionId, text });
    await delay(1200);
    const len = (text || "").trim().length;
    const score = len < 20 ? 62 : len < 60 ? 78 : 88;
    return {
      code: 0,
      data: {
        score,
        verdict: score >= 80 ? "讲解清晰，能用自己的话讲明白" : (score >= 70 ? "基本合格，再具体一些会更好" : "建议补充一个具体例子再讲一遍"),
        feedback: {
          simplicity: { score: score - 2, comment: "整体用语口语化" },
          accuracy: { score: score + 3, comment: "核心概念方向正确" },
          analogy: { score: score - 4, comment: "可再增加一个生活比喻" },
          completeness: { score: score - 1, comment: "关键点已覆盖" },
          jargon_free: { score: score - 3, comment: "术语使用需再克制" },
        },
        agents: [{ id: "coach", action: `对费曼测试讲解进行五维评分` }],
      },
    };
  },

  /**
   * POST /api/learn/report  { sessionId, feynmanScore }
   * 生成完整学习报告：掌握度 + 薄弱点 + 下一步建议
   */
  async generateReport({ sessionId, feynmanScore }) {
    if (REAL) return fetchJson("/api/learn/report", "POST", { sessionId, feynmanScore });
    await delay(1100);
    const draft = SessionStore.draft || {};
    const topic = draft.topic || "函数的单调性";
    const subject = draft.subject || "数学";
    const difficulty = draft.difficulty || "高中";
    const key = normalizeTopic(topic);
    const date = new Date().toLocaleString("zh-CN", { hour12: false });
    const mastery = Math.min(96, Math.round(80 * 0.82 + (feynmanScore || 80) * 0.18));

    const weakLib = {
      "函数的单调性": [{ text: "区间端点的开闭判断不够严谨", severity: "中" }, { text: "复合函数单调性判断需多练", severity: "低" }],
      "牛顿第二定律": [{ text: "受力分析时易漏力", severity: "中" }, { text: "连接体问题需加强", severity: "低" }],
      "化学平衡移动": [{ text: "压强改变对平衡影响的推理不熟练", severity: "中" }],
      "光合作用": [{ text: "光反应与暗反应的场所容易记混", severity: "低" }],
    };
    const weakPoints = weakLib[key] || [
      { text: "概念理解到位，但应用场景判断可再熟练", severity: "低" },
    ];

    const report = {
      id: sessionId, topic, subject, difficulty,
      generatedAt: date, status: "done", mastery,
      model: draft.model || "qwen2.5:7b",
      duration: "3分45秒", toolCalls: 15,
      weakPoints,
      nextSteps: [
        `完成「${topic}」相关练习（${difficulty}难度）`,
        "尝试用 30 秒向同学讲解核心概念",
        "复习周期：1 天后 → 3 天后 → 7 天后 → 14 天后",
      ],
      agents: DB.agentDefs.map((a) => ({
        id: a.id, name: a.name, model: a.model, status: "done",
        calls: a.id === "orchestrator" ? 6 : a.id === "feynman" ? 5 : 2,
      })),
      feynmanScore: feynmanScore || 80,
    };

    DB.sessions.unshift({
      id: sessionId, topic, subject, difficulty, date,
      status: "done", mastery, model: report.model, duration: report.duration,
      toolCalls: report.toolCalls, weakPoints, nextSteps, agents: report.agents,
    });
    return { code: 0, data: report };
  },

  /**
   * GET /api/learn/report/:id
   * 按 id 取报告
   */
  async getReport({ id }) {
    if (REAL) return fetchJson(`/api/learn/report/${id}`, "GET");
    await delay(300);
    const hit = DB.sessions.find((s) => s.id === id);
    if (!hit) return { code: 404, message: "报告不存在" };
    return { code: 0, data: hit };
  },

  /**
   * GET /api/learn/history?subject=math
   * 学习历史列表（可按学科筛选；空数组=空态）
   */
  async getHistory({ subject } = {}) {
    if (REAL) return fetchJson(`/api/learn/history?subject=${encodeURIComponent(subject || "全部")}`, "GET");
    await delay(400);
    let list = DB.sessions.slice();
    if (subject && subject !== "全部") list = list.filter((s) => s.subject === subject);
    return { code: 0, data: list, total: list.length };
  },

  /**
   * GET /api/profile — 我的学习档案（真实模式）
   */
  async profile() {
    if (REAL) return fetchJson("/api/profile", "GET");
    await delay(300);
    const list = DB.sessions.slice();
    const avg = Math.round(list.reduce(function (s, x) { return s + x.mastery; }, 0) / (list.length || 1));
    const weak = {};
    list.forEach(function (s) {
      (s.weakPoints || []).forEach(function (w) { weak[w.text] = (weak[w.text] || 0) + 1; });
    });
    return {
      code: 0,
      data: {
        user: { id: 0, name: "演示学生", role: "student" },
        total_reports: list.length, avg_mastery: avg,
        trend: list.slice(0, 10).reverse().map(function (s) { return { date: s.date.slice(5, 10), score: s.mastery }; }),
        weak_points: Object.keys(weak).slice(0, 8).map(function (k) { return { text: k, severity: "中", count: weak[k] }; }),
        conversations: [],
        recent_reports: list.slice(0, 5).map(function (s) { return { id: s.id, topic: s.topic, score: s.mastery, date: s.date }; }),
      },
    };
  },
};
