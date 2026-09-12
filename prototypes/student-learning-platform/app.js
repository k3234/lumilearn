/* ============================================================
 * app.js — LumiLearn v0.2.0 学生端共享壳
 * 提供：侧栏导航渲染 / 统一登录门 / toast / 同源 API 封装 / 工具函数
 * 契约：真实后端由 Student Portal 注入 window.__LUMILEARN_REAL__ = true
 *      以及 <base href="/student/">；接口统一返回 {code,data} 或 {success,...}
 * 用法：<script src="app.js"></script>，页面调用 LL.boot({nav:'index'})
 * ============================================================ */
(function () {
  var REAL = window.__LUMILEARN_REAL__ === true;

  var NAV = [
    { section: "学习中心" },
    { key: "index",      label: "首页",     href: "index.html",      icon: "house" },
    { key: "start",      label: "开始学习", href: "start.html",      icon: "circle-play" },
    { key: "learn",      label: "学习过程", href: "learn.html",      icon: "book-open" },
    { key: "checkpoint", label: "闯关检测", href: "checkpoint.html", icon: "target" },
    { key: "profile",    label: "学习档案", href: "profile.html",    icon: "user" },
    { section: "账户" },
    { key: "report",     label: "学习报告", href: "report.html",     icon: "file" },
    { key: "settings",   label: "设置",     href: "javascript:void(0)", icon: "settings", act: "settings" }
  ];

  var _user = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function pct(v, digits) {
    var n = Number(v);
    if (!isFinite(n)) return "—";
    if (n <= 1 && n > 0) n = n * 100;          // BKT 掌握度 0-1 → 百分
    return n.toFixed(digits == null ? 0 : digits) + "%";
  }
  function fmtDate(s) { return String(s || "").slice(0, 16).replace("T", " "); }
  function icon(name, size) {
    return '<i class="icon icon-' + (size || 16) + ' icon-' + name + '" aria-hidden="true"></i>';
  }

  /* ---------- toast ---------- */
  function ensureToast() {
    if (document.getElementById("toast")) return;
    var t = document.createElement("div");
    t.className = "toast"; t.id = "toast";
    document.body.appendChild(t);
  }
  var _tt = null;
  function toast(msg) {
    ensureToast();
    var el = document.getElementById("toast");
    el.textContent = msg; el.classList.add("show");
    clearTimeout(_tt);
    _tt = setTimeout(function () { el.classList.remove("show"); }, 2200);
  }

  /* ---------- API ---------- */
  function req(path, method, body) {
    var opt = { method: method || "GET", headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opt.body = JSON.stringify(body);
    return fetch(path, opt).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        return { status: r.status, json: j || {} };
      });
    });
  }
  function apiGet(path) { return req(path, "GET").then(function (r) { return r.json; }); }
  function apiPost(path, body) { return req(path, "POST", body || {}).then(function (r) { return r.json; }); }

  /* ---------- 登录门 ---------- */
  function ensureGate() {
    if (document.getElementById("loginGate")) return;
    var g = document.createElement("div");
    g.className = "login-gate"; g.id = "loginGate";
    g.innerHTML =
      '<form class="login-box" id="loginForm" autocomplete="on">' +
        '<h3>' + icon("user") + ' 登录 LumiLearn</h3>' +
        '<p class="sub">使用你的学习账号登录（学生 / 教师账号）</p>' +
        '<input id="loginUser" placeholder="用户名" autocomplete="username">' +
        '<input id="loginPass" type="password" placeholder="密码" autocomplete="current-password">' +
        '<button class="btn primary" id="loginBtn" type="submit">登 录</button>' +
      '</form>';
    document.body.appendChild(g);
    g.querySelector("#loginForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var u = g.querySelector("#loginUser").value.trim();
      var p = g.querySelector("#loginPass").value;
      if (!u || !p) { toast("请输入用户名和密码"); return; }
      var b = g.querySelector("#loginBtn");
      b.disabled = true; b.textContent = "登录中…";
      apiPost("/api/auth/login", { username: u, password: p }).then(function (j) {
        if (j.code === 0 || j.success) {
          _user = (j.data || j.user) || null;
          g.classList.remove("show");
          toast("欢迎回来，" + ((_user && _user.name) || u));
          renderUser();
          if (location.search.indexOf("need=login") !== -1) history.replaceState(null, "", location.pathname);
          if (typeof window.LL_AFTER_LOGIN === "function") { window.LL_AFTER_LOGIN(_user); }
          else { setTimeout(function () { location.reload(); }, 500); }
        } else {
          toast(j.message || j.error || "登录失败");
          b.disabled = false; b.textContent = "登 录";
        }
      }).catch(function () { toast("网络异常，请重试"); b.disabled = false; b.textContent = "登 录"; });
    });
  }
  function showLogin() { ensureGate(); document.getElementById("loginGate").classList.add("show"); }

  function me() {
    if (!REAL) return Promise.resolve({ code: 401 });
    return apiGet("/api/auth/me");
  }

  /** 登录态守卫：未登录弹出登录门；返回 Promise<user|null> */
  function guard() {
    ensureGate();
    return me().then(function (j) {
      if (j && j.code === 0) { _user = j.data || j.user; renderUser(); return _user; }
      if (REAL) showLogin();
      return null;
    }).catch(function () { showLogin(); return null; });
  }

  /* ---------- 侧栏 ---------- */
  function renderSidebar(active) {
    var host = document.getElementById("appSidebar");
    if (!host) return;
    var html = '<div class="brand">' +
        '<span class="brand-mark">L</span>' +
        '<span class="brand-copy"><b>LumiLearn</b><em class="muted small">学生端 · AI 教官</em></span>' +
      '</div><div class="nav-stack">';
    NAV.forEach(function (n) {
      if (n.section) { html += '<div class="nav-section-title muted small" style="padding:12px 12px 6px">' + esc(n.section) + '</div>'; return; }
      var cls = "nav-item" + (n.key === active ? " active" : "");
      var attr = n.act ? ' data-act="' + n.act + '"' : '';
      html += '<a class="' + cls + '" data-nav="' + n.key + '" href="' + n.href + '"' + attr + '>' +
                icon(n.icon) + '<span>' + esc(n.label) + '</span></a>';
    });
    html += '</div><div class="sidebar-footer">' +
        '<div class="sidebar-user flex" id="userBox" style="display:none">' +
          '<span class="brand-mark" style="width:26px;height:26px;font-size:12px" id="userAvatar">S</span>' +
          '<span class="sidebar-user-detail" style="min-width:0">' +
            '<b id="userName" style="display:block;font-size:13px">—</b>' +
            '<span class="muted small" id="userMeta">—</span>' +
          '</span>' +
          '<button class="btn ghost sm" id="logoutBtn" type="button" style="margin-left:auto">退出</button>' +
        '</div>' +
      '</div>';
    host.innerHTML = html;
    var lo = document.getElementById("logoutBtn");
    if (lo) lo.addEventListener("click", function () {
      apiPost("/api/auth/logout", {}).then(function () { location.href = "index.html?need=login"; });
    });
    var st = host.querySelector('[data-act="settings"]');
    if (st) st.addEventListener("click", function () { toast("设置功能开发中"); });
  }

  function renderUser() {
    var box = document.getElementById("userBox");
    if (!box || !_user) return;
    box.style.display = "flex";
    var nm = document.getElementById("userName");
    var mt = document.getElementById("userMeta");
    var av = document.getElementById("userAvatar");
    if (nm) nm.textContent = _user.name || _user.username || "同学";
    if (mt) mt.textContent = _user.role === "teacher" ? "教师" : "学生";
    if (av) av.textContent = String(_user.name || "S").slice(0, 1).toUpperCase();
  }

  /** boot({nav})：渲染侧栏 + 守卫登录（可选 requireLogin） */
  function boot(opts) {
    opts = opts || {};
    ensureToast();
    renderSidebar(opts.nav || "");
    var p = Promise.resolve(_user);
    if (opts.requireLogin !== false) p = guard();
    return p;
  }

  window.LL = {
    REAL: REAL, api: { get: apiGet, post: apiPost }, me: me, guard: guard,
    boot: boot, toast: toast, esc: esc, pct: pct, fmtDate: fmtDate, icon: icon,
    user: function () { return _user; }
  };
})();
