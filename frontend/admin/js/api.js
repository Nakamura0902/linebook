const API_BASE = "/api/v1";

function getToken() {
  return localStorage.getItem("access_token");
}

async function request(method, path, body = null) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (res.status === 401) {
    localStorage.removeItem("access_token");
    location.href = "/admin/index.html";
    return;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "エラーが発生しました" }));
    throw new Error(err.message || err.detail || "エラーが発生しました");
  }

  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  delete: (path, body) => request("DELETE", path, body),
};

// トースト通知
function showToast(message, type = "success") {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// モーダル管理
function openModal(id) {
  document.getElementById(id).style.display = "flex";
}
function closeModal(id) {
  document.getElementById(id).style.display = "none";
}

// 現在のstore_idをURLパラメータから取得
function getStoreId() {
  const params = new URLSearchParams(location.search);
  return params.get("store_id") || localStorage.getItem("current_store_id");
}

// 日付フォーマット
function formatDateTime(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
}

function formatDate(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  return `${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")}`;
}

// ステータスバッジ
function statusBadge(status) {
  const labels = {
    confirmed: "確定",
    pending: "仮予約",
    cancelled: "取消",
    completed: "完了",
    no_show: "無断欠席",
  };
  return `<span class="badge badge-${status}">${labels[status] || status}</span>`;
}
