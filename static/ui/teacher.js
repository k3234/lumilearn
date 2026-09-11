/* ============================================================
 * teacher.js — LumiLearn v0.2.0 教师端共享壳
 * 提供：侧栏导航渲染 / 用户信息 / toast / 同源 API 封装 / 工具函数
 * 认证：页面由服务端 session 角色守卫（/teacher* 仅 teacher/admin），
 *      本壳仍会请求 GET /api/auth/me 展示用户名与角色，并做容错。
 * 契约：同一后端存在两种返回风格，本壳统一兼容：
 *      {success:true, ...} 与 {code:0, data:...}
 * 用法：<script src="/static/ui/teacher.js"></script>
 *      页面调用 LLT.boot({nav:'dashboard'|'class'|'tasks'})
 * ============================================================ */
(function () {
  var NAV = [
    { key: "dashboard", label: "仪表盘",       href: "/teacher",        icon: "house" },
    { key: "class",     label: "班级与学生",   href: "/teacher/class",  icon: "user" },
    { key: "tasks",     label: "任务与资源",   href: "/teacher/tasks",  icon: "file" },
    { key: "analytics", label: "学情分析",     href: "/analytics",      icon: "chart" },
    { key: "console",   label: "深度控制台",   href: "/teacher/console", icon: "settings" }
  ];

  var _user = null;

  /* ---------- 工具 ---------- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  // 教师端取到的数值本身即为百分数（如 avg_mastery=76、correct_rate=84、accuracy=75.0）
  function pct(v, digits) {
    var n = Number(v);
    if (v === null || v === undefined || v === "" || !isFinite(n)) return "—";
    return n.toFixed(digits == null ? 0 : digits) + "%";
  }
  function fmtDate(s) {
    var t = String(s || "").trim();
    if (!t) return "—";
    return t.slice(0, 16).replace("T", " ");
  }
  function icon(name, size) {
    return '<i class="icon icon-' + (size || 16) + ' icon-' + name + '" aria-hidden="true"></i>';
  }
  function num(v) {
    var n = Number(v);
    return isFinite(n) ? n : 0;
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
    _tt = setTimeout(function () { el.classList.remove("show"); }, 2400);
  }

  /* ---------- API（统一兼容 {success,...} 与 {code,data}） ---------- */
  function req(path, method, body) {
    var opt = { method: method || "GET", headers: { "Content-Type": "application/json" }, credentials: "same-origin" };
    if (body !== undefined) opt.body = JSON.stringify(body);
    return fetch(path, opt).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (j && typeof j === "object") { j._status = r.status; return j; }
        return { _status: r.status, success: false, error: "响应解析失败" };
      });
    }).catch(function () {
      return { _status: 0, success: false, error: "网络异常，请重试" };
    });
  }
  function get(path) { return req(path, "GET"); }
  function post(path, body) { return req(path, "POST", body || {}); }
  function put(path, body) { return req(path, "PUT", body || {}); }

  /** 是否成功：兼容 success:true / code:0 */
  function ok(j) { return !!(j && (j.success === true || j.code === 0)); }
  /** 取值：优先 data[key]，回退顶层 key；key 省略时优先返回 data */
  function val(j, key) {
    if (!j) return undefined;
    var d = j.data;
    if (key === undefined) return d !== undefined ? d : j;
    if (d && typeof d === "object" && !Array.isArray(d) && d[key] !== undefined) return d[key];
    return j[key];
  }
  /** 取列表：兼容 data 为数组 / data[key] / 顶层 key */
  function list(j, key) {
    var v = key === undefined ? val(j) : val(j, key);
    if (Array.isArray(v)) return v;
    return [];
  }
  function errMsg(j) {
    if (!j) return "请求失败";
    return j.error || j.message || ("请求失败(" + (j._status || 0) + ")");
  }

  /* ---------- 侧栏 ---------- */
  function renderSidebar(active) {
    var host = document.getElementById("appSidebar");
    if (!host) return;
    var html = '<div class="brand">' +
        '<span class="brand-mark">L</span>' +
        '<span class="brand-copy"><b>LumiLearn</b>' +
        '<em class="muted small" style="display:block">教师工作台</em></span>' +
      '</div><div class="nav-stack">';
    NAV.forEach(function (n) {
      var cls = "nav-item" + (n.key === active ? " active" : "");
      html += '<a class="' + cls + '" data-nav="' + n.key + '" href="' + n.href + '">' +
                icon(n.icon) + '<span>' + esc(n.label) + '</span></a>';
    });
    html += '</div><div class="sidebar-footer">' +
        '<div class="sidebar-user flex" id="userBox">' +
          '<span class="brand-mark" style="width:26px;height:26px;font-size:12px" id="userAvatar">师</span>' +
          '<span class="sidebar-user-detail" style="min-width:0;flex:1">' +
            '<b id="userName" style="display:block;font-size:13px">—</b>' +
            '<span class="muted small" id="userMeta">教师</span>' +
          '</span>' +
        '</div>' +
        '<button class="btn ghost sm mt-1" id="logoutBtn" type="button" style="width:100%">' +
          icon("log-out", 16) + ' 退出登录</button>' +
      '</div>';
    host.innerHTML = html;

    var lo = document.getElementById("logoutBtn");
    if (lo) lo.addEventListener("click", function () {
      lo.disabled = true;
      post("/api/auth/logout", {}).then(function () { location.href = "/"; });
    });
    var c = host.querySelector('[data-nav="console"]');
    if (c) c.addEventListener("click", function (e) {
      // 深度控制台尚未提供页面，避免 404
      e.preventDefault();
      toast("深度控制台开发中");
    });
  }

  function renderUser() {
    if (!_user) return;
    var nm = document.getElementById("userName");
    var mt = document.getElementById("userMeta");
    var av = document.getElementById("userAvatar");
    var name = _user.name || _user.username || "教师";
    if (nm) nm.textContent = name;
    if (mt) mt.textContent = _user.role === "admin" ? "管理员" : "教师";
    if (av) av.textContent = String(name).slice(0, 1).toUpperCase();
  }

  /** 登录态（教师页已被服务端守卫，此处仅用于展示信息，做容错） */
  function me() { return get("/api/auth/me"); }

  function boot(opts) {
    opts = opts || {};
    ensureToast();
    renderSidebar(opts.nav || "");
    return me().then(function (j) {
      if (ok(j)) { _user = j.user || j.data || null; renderUser(); }
      return _user;
    }).catch(function () { return null; });
  }

  window.LLT = {
    boot: boot, me: me, toast: toast,
    esc: esc, pct: pct, fmtDate: fmtDate, icon: icon, num: num,
    get: get, post: post, put: put,
    ok: ok, val: val, list: list, errMsg: errMsg,
    user: function () { return _user; }
  };
})();
