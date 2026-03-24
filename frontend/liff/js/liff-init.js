const LIFF_ID = window.LIFF_ID || "";  // HTMLから注入される
const API_BASE = window.API_BASE || "/api/v1";

let liffProfile = null;
let lineAccessToken = null;

async function initLiff() {
  await liff.init({ liffId: LIFF_ID });

  if (!liff.isLoggedIn()) {
    liff.login({ redirectUri: location.href });
    return false;
  }

  lineAccessToken = liff.getAccessToken();
  liffProfile = await liff.getProfile();
  return true;
}

async function liffRequest(method, path, body = null) {
  const headers = {
    "Content-Type": "application/json",
    "X-Line-Access-Token": lineAccessToken,
  };

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "エラーが発生しました" }));
    throw new Error(err.message || err.detail || "エラーが発生しました");
  }

  return res.json();
}

const liffApi = {
  get: (path) => liffRequest("GET", path),
  post: (path, body) => liffRequest("POST", path, body),
  put: (path, body) => liffRequest("PUT", path, body),
  delete: (path, body) => liffRequest("DELETE", path, body),
};

function showError(message) {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) overlay.style.display = "none";

  const errDiv = document.createElement("div");
  errDiv.style.cssText = "padding:24px;text-align:center;color:#ef4444";
  errDiv.innerHTML = `<p style="font-size:16px">エラー</p><p style="font-size:14px;margin-top:8px">${message}</p>`;
  document.body.appendChild(errDiv);
}

function getStoreId() {
  // 通常のクエリパラメータを確認
  const direct = new URLSearchParams(location.search).get("store_id");
  if (direct) return direct;
  // LIFFがliff.stateにエンコードした場合
  const liffState = new URLSearchParams(location.search).get("liff.state");
  if (liffState) {
    const decoded = decodeURIComponent(liffState);
    return new URLSearchParams(decoded).get("store_id");
  }
  return null;
}

function formatTime(isoStr) {
  const d = new Date(isoStr);
  return `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
}

function formatDateJa(isoStr) {
  const d = new Date(isoStr);
  const weekdays = ["日","月","火","水","木","金","土"];
  return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日（${weekdays[d.getDay()]}）`;
}
