/* auth.js — 真实后端模式的用户信息显示 + 退出登录（所有页面共享）
 * 仅当 window.__LUMILEARN_REAL__ 存在时生效；离线演示模式自动跳过。 */
(function () {
  if (window.__LUMILEARN_REAL__ !== true) return;
  var box = document.getElementById("userBox");
  var nameEl = document.getElementById("userName");
  var btn = document.getElementById("logoutBtn");
  if (!box || !nameEl || !btn) return;

  api.me().then(function (j) {
    if (j.code === 0) {
      nameEl.textContent = j.data.name + "（" + j.data.role + "）";
      box.style.display = "flex";
    }
  }).catch(function () { /* 未登录由登录门处理 */ });

  btn.addEventListener("click", function () {
    api.logout().then(function () {
      location.href = "index.html?need=login";
    });
  });
})();
