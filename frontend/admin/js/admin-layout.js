// 認証チェックと共通レイアウト処理
(function() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    location.href = "/admin/index.html";
    return;
  }

  // 管理者名を表示
  const nameEl = document.getElementById("admin-name");
  if (nameEl) nameEl.textContent = localStorage.getItem("admin_name") || "";

  // store_idをURLまたはlocalStorageから取得・設定
  const params = new URLSearchParams(location.search);
  const storeId = params.get("store_id");
  if (storeId) localStorage.setItem("current_store_id", storeId);

  // モバイルヘッダーを自動挿入
  const mobileHeader = document.createElement("div");
  mobileHeader.className = "mobile-header";
  mobileHeader.innerHTML =
    '<button class="hamburger" onclick="toggleSidebar()" aria-label="メニュー">' +
      "<span></span><span></span><span></span>" +
    "</button>" +
    '<span class="mobile-brand">LINE予約管理</span>';
  document.body.insertBefore(mobileHeader, document.body.firstChild);

  // オーバーレイを自動挿入
  const overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  overlay.addEventListener("click", closeSidebar);
  document.body.appendChild(overlay);
})();

function toggleSidebar() {
  document.body.classList.toggle("sidebar-open");
}

function closeSidebar() {
  document.body.classList.remove("sidebar-open");
}

function logout() {
  localStorage.clear();
  location.href = "/admin/index.html";
}
