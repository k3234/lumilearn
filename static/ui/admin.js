/* ============================================================
 * admin.js — LumiLearn v0.2.0 管理端共享壳（window.LLA）
 * 认证：与旧管理面板一致 —— localStorage['admin_token'] + 请求头 X-Admin-Token
 *       同时带 credentials:'same-origin' 兼容 cookie session 页面守卫
 * 提供：侧栏渲染 / 登录门 / toast / 同源 API 封装 / 工具函数
 * 用法：<script src="/static/ui/admin.js"></script>  页面调用 LLA.boot({nav:'dashboard'})
 * ============================================================ */
(function () {
  "use strict";

  var API = "/api/admin";
  var TOKEN_KEY = "admin_token";
  var TOKEN = "";
  try { TOKEN = localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { TOKEN = ""; }

  var _me = null;

  var NAV = [
    { key: "dashboard", label: "仪表盘",     href: "/admin",         icon: "house" },
    { key: "org",       label: "用户与组织", href: "/admin/org",     icon: "user" },
    { key: "ops",       label: "容量与并发", href: "/admin/ops",     icon: "settings" },
    { key: "traces",    label: "调用链追踪", href: "/admin/traces",  icon: "clock" },
    { key: "console",   label: "深度控制台", href: "/admin/console", icon: "external-link" }
  ];

  /* ---------------- 工具 ---------------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function pct(v, digits) {
    var n = Number(v);
    if (!isFinite(n)) return "—";
    if (n > 0 && n <= 1) n = n * 100;
    return n.toFixed(digits == null ? 0 : digits) + "%";
  }
  function fmtDate(s) { return String(s || "").slice(0, 16).replace("T", " "); }
  function fmtBytes(n) {
    n = Number(n);
    if (!isFinite(n) || n < 0) return "—";
    if (n < 1024) return n + " B";
    var u = ["KB", "MB", "GB", "TB"], i = -1;
    do { n /= 1024; i++; } while (n >= 1024 && i < u.length - 1);
    return n.toFixed(1) + " " + u[i];
  }
  function fmtDuration(sec) {
    var n = Number(sec);
    if (!isFinite(n) || n < 0) return "—";
    if (n < 60) return n.toFixed(0) + " 秒";
    if (n < 3600) return (n / 60).toFixed(1) + " 分钟";
    if (n < 86400) return (n / 3600).toFixed(1) + " 小时";
    return (n / 86400).toFixed(1) + " 天";
  }
  function icon(name, size) {
    return '<i class="icon icon-' + (size || 16) + ' icon-' + name + '" aria-hidden="true"></i>';
  }

  /* ---------------- toast ---------------- */
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
    _tt = setTimeout(function () { el.classList.remove("show"); }, 2400);
  }

  /* ---------------- API ---------------- */
  function unwrap(j) {
    if (j && typeof j === "object" && !("success" in j) && "code" in j && "data" in j) return j.data;
    return j;
  }
  function request(path, method, body) {
    var headers = { "Content-Type": "application/json" };
    if (TOKEN) headers["X-Admin-Token"] = TOKEN;
    var opt = { method: method, headers: headers, credentials: "same-origin" };
    if (body !== undefined) opt.body = JSON.stringify(body);
    return fetch(API + path, opt).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        j = j || {};
        if (r.status === 401 || r.status === 403) {
          if (r.status === 401) { TOKEN = ""; try { localStorage.removeItem(TOKEN_KEY); } catch (e) {} }
          // 强制改密期：后端对非改密端点统一 403，前端应弹改密窗而非登录门
          if (j.must_change_password) { showPwdGate(); }
          else { setNoAuth(r.status); }
          var err = new Error(j.error || j.message || "未登录或权限不足");
          err.status = r.status; throw err;
        }
        if (!r.ok) {
          var e2 = new Error(j.error || j.message || ("请求失败（HTTP " + r.status + "）"));
          e2.status = r.status; throw e2;
        }
        return unwrap(j);
      });
    });
  }
  function get(p) { return request(p, "GET"); }
  function post(p, b) { return request(p, "POST", b === undefined ? {} : b); }
  function put(p, b) { return request(p, "PUT", b === undefined ? {} : b); }

  /* ---------------- 侧栏 ---------------- */
  function renderSidebar(active) {
    var host = document.getElementById("appSidebar");
    if (!host) return;
    var html = '<div class="brand">' +
        '<span class="brand-mark">L</span>' +
        '<span class="brand-copy"><b>LumiLearn Admin</b><em class="muted small">管理控制台</em></span>' +
      '</div><div class="nav-stack">';
    NAV.forEach(function (n) {
      var cls = "nav-item" + (n.key === active ? " active" : "");
      html += '<a class="' + cls + '" href="' + n.href + '">' + icon(n.icon) +
              '<span class="nav-label"><span>' + esc(n.label) + '</span></span></a>';
    });
    html += '</div><div class="sidebar-footer">' +
        '<div class="sidebar-user flex" id="adminBox" style="display:none">' +
          '<span class="brand-mark" style="width:26px;height:26px;font-size:12px" id="adminAvatar">A</span>' +
          '<span class="sidebar-user-detail" style="min-width:0">' +
            '<b id="adminName" style="display:block;font-size:13px">—</b>' +
            '<span class="muted small" id="adminMeta">—</span>' +
          '</span>' +
        '</div>' +
        '<button class="btn ghost sm" id="logoutBtn" type="button" style="width:100%;margin-top:8px">' +
          icon("log-out") + ' 退出登录</button>' +
      '</div>';
    host.innerHTML = html;
    var lo = document.getElementById("logoutBtn");
    if (lo) lo.addEventListener("click", logout);
  }

  function renderAdmin(a) {
    var box = document.getElementById("adminBox");
    if (!box) return;
    box.style.display = "flex";
    var nm = document.getElementById("adminName");
    var mt = document.getElementById("adminMeta");
    var av = document.getElementById("adminAvatar");
    var label = (a && (a.display_name || a.username)) || "管理员";
    if (nm) nm.textContent = label;
    if (mt) mt.textContent = (a && a.role) || "";
    if (av) av.textContent = String(label).slice(0, 1).toUpperCase();
  }

  /* ---------------- 登录门 ---------------- */
  function ensureGate() {
    if (document.getElementById("loginGate")) return;
    var g = document.createElement("div");
    g.className = "login-gate"; g.id = "loginGate";
    g.innerHTML =
      '<form class="login-box" id="loginForm">' +
        '<h3>' + icon("user") + ' 登录管理控制台</h3>' +
        '<p class="sub">需要管理员账号。未登录时页面不会显示任何数据。</p>' +
        '<input id="loginUser" placeholder="管理员用户名" autocomplete="username">' +
        '<input id="loginPass" type="password" placeholder="密码" autocomplete="current-password">' +
        '<div class="small" style="color:var(--destructive-text);min-height:16px;margin-top:6px" id="loginErr"></div>' +
        '<button class="btn primary" id="loginBtn" type="submit">登 录</button>' +
      '</form>';
    document.body.appendChild(g);
    g.querySelector("#loginForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var u = g.querySelector("#loginUser").value.trim();
      var p = g.querySelector("#loginPass").value;
      var errEl = g.querySelector("#loginErr");
      errEl.textContent = "";
      if (!u || !p) { errEl.textContent = "请输入用户名和密码"; return; }
      var b = g.querySelector("#loginBtn");
      b.disabled = true; b.textContent = "登录中…";
      fetch(API + "/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ username: u, password: p })
      }).then(function (r) { return r.json().catch(function () { return {}; }); }).then(function (j) {
        if (j && j.success && j.token) {
          TOKEN = j.token;
          try { localStorage.setItem(TOKEN_KEY, TOKEN); } catch (e2) {}
          g.classList.remove("show");
          location.reload();
        } else {
          errEl.textContent = (j && (j.error || j.message)) || "登录失败";
          b.disabled = false; b.textContent = "登 录";
        }
      }).catch(function () {
        errEl.textContent = "网络异常，请重试";
        b.disabled = false; b.textContent = "登 录";
      });
    });
  }
  function showLogin() { ensureGate(); document.getElementById("loginGate").classList.add("show"); }

  /* ---------------- 强制改密门 ----------------
   * 首次登录（must_change_password=1）时后端对所有非改密端点返回 403，
   * 必须提供改密入口，否则管理员被锁在门外无法完成改密。
   */
  function ensurePwdGate() {
    if (document.getElementById("pwdGate")) return;
    var g = document.createElement("div");
    g.className = "login-gate"; g.id = "pwdGate";
    g.innerHTML =
      '<form class="login-box" id="pwdForm">' +
        '<h3>' + icon("settings") + ' 首次登录需修改密码</h3>' +
        '<p class="sub">为保障账号安全，请先修改初始密码（至少 8 位，含大写字母和数字）。</p>' +
        '<input id="pwdOld" type="password" placeholder="当前密码" autocomplete="current-password">' +
        '<input id="pwdNew" type="password" placeholder="新密码" autocomplete="new-password">' +
        '<input id="pwdNew2" type="password" placeholder="确认新密码" autocomplete="new-password">' +
        '<div class="small" style="color:var(--destructive-text);min-height:16px;margin-top:6px" id="pwdErr"></div>' +
        '<button class="btn primary" id="pwdBtn" type="submit">提交修改</button>' +
      '</form>';
    document.body.appendChild(g);
    g.querySelector("#pwdForm").addEventListener("submit", function (e) {
      e.preventDefault();
      var errEl = g.querySelector("#pwdErr");
      errEl.textContent = "";
      var oldP = g.querySelector("#pwdOld").value;
      var newP = g.querySelector("#pwdNew").value;
      var newP2 = g.querySelector("#pwdNew2").value;
      if (!oldP || !newP) { errEl.textContent = "请填写当前密码与新密码"; return; }
      if (newP !== newP2) { errEl.textContent = "两次输入的新密码不一致"; return; }
      var b = g.querySelector("#pwdBtn");
      b.disabled = true; b.textContent = "提交中…";
      // 直接 fetch：改密端点本身放行，不经过 request() 以免触发 403 分支
      var headers = { "Content-Type": "application/json" };
      if (TOKEN) headers["X-Admin-Token"] = TOKEN;
      fetch(API + "/password", {
        method: "POST", headers: headers, credentials: "same-origin",
        body: JSON.stringify({ old_password: oldP, new_password: newP })
      }).then(function (r) { return r.json().catch(function () { return {}; }); }).then(function (j) {
        j = j || {};
        if (j.success) {
          g.classList.remove("show");
          toast("密码修改成功");
          setTimeout(function () { location.reload(); }, 600);
        } else {
          errEl.textContent = j.error || j.message || "修改失败";
          b.disabled = false; b.textContent = "提交修改";
        }
      }).catch(function () {
        errEl.textContent = "网络异常，请重试";
        b.disabled = false; b.textContent = "提交修改";
      });
    });
  }
  function showPwdGate() { ensurePwdGate(); document.getElementById("pwdGate").classList.add("show"); }

  var _noAuth = false;
  function setNoAuth(status) {
    _noAuth = status || 401;
    showLogin();
  }
  function noAuthBanner() {
    return '<div class="card" style="border-color:var(--destructive-border);background:var(--destructive-subtle);color:var(--destructive-text)">' +
      icon("triangle-alert") + ' <b>未登录 / 无权限</b>：请先登录管理员账号后查看真实数据。' +
      ' <button class="btn sm" type="button" id="openLoginBtn" style="margin-left:8px">登录</button></div>';
  }
  function bindLoginButton(root) {
    var b = (root || document).querySelector("#openLoginBtn");
    if (b) b.addEventListener("click", showLogin);
  }

  /* ---------------- 认证 ---------------- */
  function me() {
    return get("/me").then(function (j) { _me = (j && j.admin) || null; return _me; })
      .catch(function () { _me = null; return null; });
  }
  function logout() {
    request("/logout", "POST").catch(function () {});
    TOKEN = "";
    try { localStorage.removeItem(TOKEN_KEY); } catch (e) {}
    location.reload();
  }

  /**
   * boot({nav}) → 渲染侧栏 + 校验登录态
   * @returns Promise<admin|null>（null 表示未登录，页面应显示「未登录」提示而非伪造数据）
   */
  function boot(opts) {
    opts = opts || {};
    ensureToast();
    renderSidebar(opts.nav || "");
    return me().then(function (a) {
      if (a) {
        renderAdmin(a);
        // 首次登录未改密：仅展示改密窗并阻止业务数据加载（返回 null）
        if (a.must_change_password) { showPwdGate(); return null; }
        return a;
      }
      showLogin();
      return null;
    });
  }

  window.LLA = {
    api: { get: get, post: post, put: put },
    boot: boot, me: me, logout: logout,
    toast: toast, esc: esc, pct: pct, fmtDate: fmtDate,
    fmtBytes: fmtBytes, fmtDuration: fmtDuration, icon: icon,
    showLogin: showLogin, showPwdGate: showPwdGate,
    noAuthBanner: noAuthBanner, bindLoginButton: bindLoginButton,
    isNoAuth: function () { return _noAuth; },
    admin: function () { return _me; }
  };
})();
