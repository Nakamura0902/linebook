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
})();

function logout() {
  localStorage.clear();
  location.href = "/admin/index.html";
}
