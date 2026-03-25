// EC ショップ LIFF アプリ
const shopState = {
  storeId: null,
  customer: null,
  categories: [],
  selectedCategoryIds: [],   // カテゴリ選択画面で選んだもの
  activeCategoryId: null,    // 商品一覧のフィルター
  mode: "select",            // "select" | "list" | "detail"
  products: [],
};

window.addEventListener("DOMContentLoaded", async () => {
  shopState.storeId = getStoreId();
  if (!shopState.storeId) { showError("店舗IDが指定されていません"); return; }

  try {
    const ready = await initLiff();
    if (!ready) return;

    // 顧客識別
    const customerData = await liffApi.post(
      `/liff/customers/identify?store_id=${shopState.storeId}`, {}
    );
    shopState.customer = customerData.customer;

    // カテゴリ取得
    shopState.categories = await liffApi.get(
      `/liff/stores/${shopState.storeId}/shop/categories`
    );

    // URLで商品詳細直リンクの場合
    const productId = new URLSearchParams(location.search).get("product_id");
    if (productId) {
      await renderProductDetail(productId);
      return;
    }

    // 既存の興味設定があるか確認
    if (shopState.customer) {
      const interests = await liffApi.get(
        `/liff/customers/${shopState.customer.id}/interests`
      );
      if (interests.length > 0) {
        // 興味設定済み → 商品一覧へ
        shopState.activeCategoryId = interests[0];
        await renderProductList();
        return;
      }
    }

    // 初回 or 未設定 → カテゴリ選択
    renderCategorySelect();

  } catch (err) {
    showError(err.message);
  } finally {
    document.getElementById("loading-overlay").style.display = "none";
  }
});

// ─── カテゴリ選択画面 ───

function renderCategorySelect() {
  shopState.mode = "select";
  const content = document.getElementById("content");

  content.innerHTML = `
    <div class="shop-header">
      <h2>気になるケアを教えてください</h2>
      <p>あなたにぴったりの商品をご紹介します</p>
    </div>
    <div class="category-grid">
      ${shopState.categories.map(c => `
        <div class="category-card" id="cat-${c.id}" onclick="toggleCategory('${c.id}')">
          <div class="category-emoji">${c.emoji || "🛍️"}</div>
          <div class="category-name">${escapeHtml(c.name)}</div>
        </div>
      `).join("")}
    </div>
    <div style="padding:0 16px 32px">
      <button class="btn-line" id="btn-select" onclick="confirmCategories()" disabled
        style="background:linear-gradient(135deg,#f093fb,#f5576c);box-shadow:0 4px 14px rgba(245,87,108,0.35);opacity:0.5">
        この商品を見る
      </button>
    </div>
  `;
}

function toggleCategory(catId) {
  const idx = shopState.selectedCategoryIds.indexOf(catId);
  if (idx >= 0) {
    shopState.selectedCategoryIds.splice(idx, 1);
    document.getElementById("cat-" + catId).classList.remove("selected");
  } else {
    shopState.selectedCategoryIds.push(catId);
    document.getElementById("cat-" + catId).classList.add("selected");
  }

  const btn = document.getElementById("btn-select");
  const hasSelection = shopState.selectedCategoryIds.length > 0;
  btn.disabled = !hasSelection;
  btn.style.opacity = hasSelection ? "1" : "0.5";
}

async function confirmCategories() {
  if (!shopState.selectedCategoryIds.length) return;

  // 興味を保存
  if (shopState.customer) {
    try {
      await liffApi.post(`/liff/customers/${shopState.customer.id}/interests`, {
        category_ids: shopState.selectedCategoryIds,
      });
    } catch (e) { /* 保存失敗しても表示は続ける */ }
  }

  shopState.activeCategoryId = shopState.selectedCategoryIds[0];
  await renderProductList();
}

// ─── 商品一覧 ───

async function renderProductList() {
  shopState.mode = "list";
  const content = document.getElementById("content");

  // カテゴリタブ生成
  const tabsHtml = `
    <div class="cat-tabs">
      <div class="cat-tab ${!shopState.activeCategoryId ? 'active' : ''}"
           onclick="filterByCategory(null)">すべて</div>
      ${shopState.categories.map(c => `
        <div class="cat-tab ${shopState.activeCategoryId === c.id ? 'active' : ''}"
             onclick="filterByCategory('${c.id}')">
          ${c.emoji || ""} ${escapeHtml(c.name)}
        </div>
      `).join("")}
    </div>
  `;

  content.innerHTML = tabsHtml + '<div id="products-area"><div class="loading">読み込み中...</div></div>';

  await loadProducts();
}

async function loadProducts() {
  const url = `/liff/stores/${shopState.storeId}/shop/products${shopState.activeCategoryId ? "?category_id=" + shopState.activeCategoryId : ""}`;
  try {
    shopState.products = await liffApi.get(url);
  } catch (e) {
    document.getElementById("products-area").innerHTML =
      `<div class="shop-empty"><div class="shop-empty-icon">😔</div><div class="shop-empty-text">${e.message}</div></div>`;
    return;
  }

  if (!shopState.products.length) {
    document.getElementById("products-area").innerHTML = `
      <div class="shop-empty">
        <div class="shop-empty-icon">🛍️</div>
        <div class="shop-empty-text">このカテゴリの商品はまだありません</div>
      </div>
    `;
    return;
  }

  document.getElementById("products-area").innerHTML = `
    <div class="product-list">
      ${shopState.products.map(p => `
        <div class="product-card" onclick="renderProductDetail('${p.id}')">
          <div class="product-thumb">
            ${p.image_url
              ? `<img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" onerror="this.parentElement.innerHTML='🛒'">`
              : "🛒"}
          </div>
          <div class="product-info">
            <div class="product-name">${escapeHtml(p.name)}</div>
            ${p.description ? `<div class="product-desc">${escapeHtml(p.description)}</div>` : ""}
            <div>
              <span class="product-price">${p.price != null ? "¥" + p.price.toLocaleString() : "価格はサイトで確認"}</span>
              ${p.ec_platform ? `<span class="product-platform">${p.ec_platform}</span>` : ""}
            </div>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

async function filterByCategory(catId) {
  shopState.activeCategoryId = catId;

  // タブのアクティブ更新
  document.querySelectorAll(".cat-tab").forEach(el => el.classList.remove("active"));
  const idx = shopState.categories.findIndex(c => c.id === catId);
  const tabs = document.querySelectorAll(".cat-tab");
  tabs[catId ? idx + 1 : 0]?.classList.add("active");

  document.getElementById("products-area").innerHTML =
    '<div class="loading">読み込み中...</div>';
  await loadProducts();
}

// ─── 商品詳細（接客ページ） ───

async function renderProductDetail(productId) {
  shopState.mode = "detail";
  const content = document.getElementById("content");
  content.innerHTML = '<div class="loading">読み込み中...</div>';

  try {
    const p = await liffApi.get(`/liff/shop/products/${productId}`);

    content.innerHTML = `
      <div class="back-link" onclick="renderProductList()">
        ← 商品一覧に戻る
      </div>
      <div class="product-detail">
        <div class="product-hero">
          ${p.image_url
            ? `<img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}">`
            : "🛒"}
        </div>
        <div class="product-detail-body">
          <div class="product-detail-name">${escapeHtml(p.name)}</div>
          <div class="product-detail-price">
            ${p.price != null ? "¥" + p.price.toLocaleString() : "価格はサイトで確認"}
            ${p.ec_platform ? `<span class="product-platform">${p.ec_platform}</span>` : ""}
          </div>
          ${p.staff_comment ? `
            <div class="staff-comment-box">
              <div class="staff-comment-label">スタッフより</div>
              <div class="staff-comment-text">${escapeHtml(p.staff_comment)}</div>
            </div>
          ` : ""}
          ${p.description ? `<p style="font-size:14px;color:#495057;line-height:1.7">${escapeHtml(p.description)}</p>` : ""}
        </div>
      </div>
      <a href="${escapeHtml(p.external_url)}" target="_blank" class="btn-buy"
         onclick="recordClick('${p.id}')">
        商品ページで購入する →
      </a>
    `;
  } catch (err) {
    showError(err.message);
  }
}

async function recordClick(productId) {
  try {
    await liffApi.post(`/liff/shop/products/${productId}/click`, {});
  } catch (e) { /* ignore */ }
}
