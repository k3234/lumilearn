/* nav.js — 唯一 active 状态机制：读 body[data-page]，标记匹配的 .nav-item
 * 不做任何布局工作；每页在末尾同步加载。 */
(function () {
  const page = (document.body && document.body.dataset.page) || "";
  var items = document.querySelectorAll(".nav-item[data-nav]");
  for (var i = 0; i < items.length; i++) {
    if (items[i].getAttribute("data-nav") === page) {
      items[i].classList.add("active");
    }
  }
})();
