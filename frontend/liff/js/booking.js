// 予約フローの状態管理
const state = {
  step: 1,
  storeId: null,
  store: null,
  menus: [],
  staffList: [],
  customer: null,
  selectedMenu: null,
  selectedStaff: null,      // null = おまかせ
  selectedDate: null,       // YYYY-MM-DD
  selectedSlot: null,       // TimeSlotResponse
  calendarYear: null,
  calendarMonth: null,
  availableDates: {},        // YYYY-MM-DD → slots[]
};

const TOTAL_STEPS = 5;

// ──────────── 初期化 ────────────

window.addEventListener("DOMContentLoaded", async () => {
  state.storeId = getStoreId();

  if (!state.storeId) {
    showError("店舗IDが指定されていません");
    return;
  }

  try {
    const ready = await initLiff();
    if (!ready) return;

    // liff.init後にURLパラメータが確定してから判定
    const page = getPageParam();
    if (page === "my-reservations") {
      await renderReservationsMode();
      return;
    }

    const [store, menus, staffList] = await Promise.all([
      liffApi.get(`/liff/stores/${state.storeId}`),
      liffApi.get(`/liff/stores/${state.storeId}/menus`),
      liffApi.get(`/liff/stores/${state.storeId}/staff`),
    ]);

    state.store = store;
    state.menus = menus;
    state.staffList = staffList;

    document.getElementById("store-name").textContent = store.name;

    // 顧客識別
    const customerData = await liffApi.post(
      `/liff/customers/identify?store_id=${state.storeId}`, {}
    );
    state.customer = customerData.customer;

    document.getElementById("loading-overlay").style.display = "none";
    renderStep(1);

  } catch (err) {
    showError(err.message);
  }
});

// ──────────── 予約確認モード ────────────

async function renderReservationsMode() {
  // ヘッダーと進捗バーを予約確認用に変更
  const header = document.getElementById("store-name");
  header.textContent = "予約確認";
  header.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
  header.style.boxShadow = "0 2px 12px rgba(102,126,234,0.35)";

  document.querySelector(".progress-bar").style.display = "none";

  const footer = document.querySelector(".liff-footer");
  footer.innerHTML = `
    <button class="btn-line" onclick="liff.closeWindow()" style="background:linear-gradient(135deg,#667eea,#764ba2);box-shadow:0 4px 14px rgba(102,126,234,0.35)">LINEに戻る</button>
  `;

  const content = document.getElementById("content");

  try {
    const customerData = await liffApi.post(
      `/liff/customers/identify?store_id=${state.storeId}`, {}
    );
    const customer = customerData.customer;
    const reservations = await liffApi.get(`/liff/customers/${customer.id}/reservations`);

    document.getElementById("loading-overlay").style.display = "none";

    if (!reservations.length) {
      content.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📅</div>
          <div class="empty-title">予約がありません</div>
          <div class="empty-sub">新しい予約を作成してみましょう</div>
        </div>
      `;
      return;
    }

    const now = new Date();
    const upcoming = reservations.filter(r =>
      ["confirmed","pending"].includes(r.status) && new Date(r.start_datetime) >= now
    );
    const past = reservations.filter(r =>
      !upcoming.includes(r)
    );

    let html = "";
    if (upcoming.length) {
      html += `<div class="res-section-title">直近の予約</div>`;
      html += upcoming.map(r => renderResCard(r, false)).join("");
    }
    if (past.length) {
      html += `<div class="res-section-title">過去の予約</div>`;
      html += past.map(r => renderResCard(r, true)).join("");
    }
    content.innerHTML = html;

  } catch (err) {
    document.getElementById("loading-overlay").style.display = "none";
    showError(err.message);
  }
}

function renderResCard(r, isPast) {
  const statusMap = {
    confirmed: { label: "確定",    cls: "confirmed" },
    pending:   { label: "確認待ち", cls: "pending"   },
    cancelled: { label: "取消済み", cls: "cancelled" },
    completed: { label: "完了",    cls: "completed" },
    no_show:   { label: "無断欠席", cls: "no_show"   },
  };
  const s = statusMap[r.status] || { label: r.status, cls: "completed" };
  const cardCls = isPast ? (r.status === "cancelled" ? "cancelled" : "past") : "";
  const canCancel = ["confirmed","pending"].includes(r.status) && new Date(r.start_datetime) >= new Date();

  return `
    <div class="reservation-card ${cardCls}">
      <div class="res-header">
        <div>
          <div class="res-date">${formatDateJa(r.start_datetime)}</div>
          <div class="res-time">${formatTime(r.start_datetime)}</div>
        </div>
        <span class="res-badge ${s.cls}">${s.label}</span>
      </div>
      <div class="res-detail">
        ${r.menu_name ? `<strong>${escapeHtml(r.menu_name)}</strong>` : ""}
        ${r.staff_name ? ` · ${escapeHtml(r.staff_name)}` : " · 指名なし"}
      </div>
      <div class="res-code">予約番号: ${r.confirmation_code || "—"}</div>
      ${canCancel ? `
        <div class="res-actions" style="margin-top:12px">
          <button class="btn-cancel" onclick="cancelReservation('${r.id}')">取消する</button>
        </div>
      ` : ""}
    </div>
  `;
}

async function cancelReservation(reservationId) {
  if (!confirm("予約を取消しますか？")) return;
  try {
    await liffApi.delete(`/liff/reservations/${reservationId}`, { reason: null });
    await renderReservationsMode();
  } catch (err) {
    alert(err.message);
  }
}

// ──────────── ステップ制御 ────────────

function renderStep(step) {
  state.step = step;
  updateProgressBar(step);

  document.getElementById("btn-back").style.display = step > 1 ? "block" : "none";
  document.getElementById("btn-next").disabled = true;

  const content = document.getElementById("content");
  content.innerHTML = "";

  switch (step) {
    case 1: renderMenuStep(content); break;
    case 2: renderStaffStep(content); break;
    case 3: renderDateStep(content); break;
    case 4: renderInfoStep(content); break;
    case 5: renderConfirmStep(content); break;
  }
}

function updateProgressBar(activeStep) {
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const el = document.getElementById(`step-${i}`);
    el.classList.remove("active", "done");
    if (i < activeStep) el.classList.add("done");
    else if (i === activeStep) el.classList.add("active");
  }
}

function prevStep() { if (state.step > 1) renderStep(state.step - 1); }

function nextStep() {
  if (state.step < TOTAL_STEPS) {
    renderStep(state.step + 1);
  } else {
    submitReservation();
  }
}

function enableNext(text = "次へ") {
  const btn = document.getElementById("btn-next");
  btn.disabled = false;
  btn.textContent = text;
}

// ──────────── Step 1: メニュー選択 ────────────

function renderMenuStep(container) {
  const customer = state.customer;
  const isFirstVisit = customer?.is_first_visit;

  // 初回/再来フィルタリング
  const filteredMenus = state.menus.filter(m => {
    if (m.is_first_visit_only && !isFirstVisit) return false;
    if (m.is_revisit_only && isFirstVisit) return false;
    return true;
  });

  // カテゴリ別にグルーピング
  const categories = {};
  filteredMenus.forEach(m => {
    const cat = m.category_name || "その他";
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(m);
  });

  container.innerHTML = `
    <p class="step-title">メニューを選択してください</p>
    ${Object.entries(categories).map(([cat, menus]) => `
      <div class="category-label">${escapeHtml(cat)}</div>
      ${menus.map(m => `
        <div class="select-card ${state.selectedMenu?.id === m.id ? "selected" : ""}"
             onclick="selectMenu(${JSON.stringify(m).replace(/"/g, '&quot;')})">
          <div class="card-title">${escapeHtml(m.name)}</div>
          <div class="card-sub">
            ${m.duration_minutes}分
            ${m.price != null ? ` &nbsp;·&nbsp; ¥${m.price.toLocaleString()}` : ""}
            ${m.description ? ` &nbsp;·&nbsp; ${escapeHtml(m.description)}` : ""}
          </div>
        </div>
      `).join("")}
    `).join("")}
  `;

  if (state.selectedMenu) enableNext();
}

function selectMenu(menu) {
  state.selectedMenu = menu;
  // カード選択スタイル更新
  document.querySelectorAll(".select-card").forEach(el => el.classList.remove("selected"));
  event.currentTarget.classList.add("selected");
  enableNext();
}

// ──────────── Step 2: スタッフ選択 ────────────

function renderStaffStep(container) {
  container.innerHTML = `
    <p class="step-title">担当を選択してください</p>
    <div class="select-card ${state.selectedStaff === null ? "selected" : ""}"
         onclick="selectStaff(null)">
      <div class="card-inner">
        <div style="width:48px;height:48px;border-radius:50%;background:#f0f2f5;display:flex;align-items:center;justify-content:center;font-size:22px;margin-right:12px;flex-shrink:0">🎲</div>
        <div>
          <div class="card-title">指名なし（おまかせ）</div>
          <div class="card-sub">空きのあるスタッフが担当します</div>
        </div>
      </div>
    </div>
    ${state.staffList.map(s => `
      <div class="select-card ${state.selectedStaff?.id === s.id ? "selected" : ""}"
           onclick='selectStaff(${JSON.stringify(s)})'>
        <div class="card-inner">
          ${s.image_url
            ? `<img class="staff-avatar" src="${s.image_url}" alt="${escapeHtml(s.name)}">`
            : `<div style="width:48px;height:48px;border-radius:50%;background:var(--line-green-light);display:flex;align-items:center;justify-content:center;font-size:20px;margin-right:12px;flex-shrink:0;color:var(--line-green-dark);font-weight:700">${escapeHtml(s.name).charAt(0)}</div>`
          }
          <div>
            <div class="card-title">${escapeHtml(s.name)}${s.role ? ` <span style="font-weight:400;font-size:12px;color:#868e96">${escapeHtml(s.role)}</span>` : ""}</div>
            ${s.bio ? `<div class="card-sub">${escapeHtml(s.bio)}</div>` : ""}
          </div>
        </div>
      </div>
    `).join("")}
  `;

  // スタッフは「指名なし」がデフォルト選択状態
  if (state.selectedStaff !== undefined) enableNext();
}

function selectStaff(staff) {
  state.selectedStaff = staff;
  state.selectedDate = null;
  state.selectedSlot = null;
  document.querySelectorAll(".select-card").forEach(el => el.classList.remove("selected"));
  event.currentTarget.classList.add("selected");
  enableNext();
}

// ──────────── Step 3: 日時選択 ────────────

function renderDateStep(container) {
  const now = new Date();
  state.calendarYear = state.calendarYear || now.getFullYear();
  state.calendarMonth = state.calendarMonth !== null ? state.calendarMonth : now.getMonth();

  container.innerHTML = `
    <p class="step-title">日時を選択してください</p>
    <div id="calendar-area"></div>
    <div id="slots-area"></div>
  `;

  renderCalendar();
  if (state.selectedDate) renderSlots(state.selectedDate);
}

function renderCalendar() {
  const year = state.calendarYear;
  const month = state.calendarMonth;
  const today = new Date();
  today.setHours(0,0,0,0);

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const weekdays = ["日","月","火","水","木","金","土"];

  let html = `
    <div class="month-nav">
      <button class="btn btn-sm btn-outline" onclick="changeMonth(-1)">‹ 前月</button>
      <strong>${year}年${month+1}月</strong>
      <button class="btn btn-sm btn-outline" onclick="changeMonth(1)">次月 ›</button>
    </div>
    <div class="cal-grid">
      ${weekdays.map(d => `<div class="cal-day-header">${d}</div>`).join("")}
      ${Array(firstDay).fill('<div></div>').join("")}
  `;

  for (let d = 1; d <= daysInMonth; d++) {
    const date = new Date(year, month, d);
    const dateStr = `${year}-${String(month+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    const isPast = date < today;
    const isSelected = state.selectedDate === dateStr;

    html += `<button class="cal-day ${isSelected ? "selected" : ""}"
      ${isPast ? "disabled" : `onclick="selectDate('${dateStr}')"`}
    >${d}</button>`;
  }

  html += `</div>`;
  document.getElementById("calendar-area").innerHTML = html;
}

async function selectDate(dateStr) {
  state.selectedDate = dateStr;
  state.selectedSlot = null;
  document.getElementById("btn-next").disabled = true;

  renderCalendar();

  const slotsArea = document.getElementById("slots-area");
  slotsArea.innerHTML = '<div style="padding:16px;text-align:center;color:var(--gray-500)">空き枠を確認中...</div>';

  try {
    const staffId = state.selectedStaff?.id || "";
    const data = await liffApi.get(
      `/liff/stores/${state.storeId}/availability?date=${dateStr}&menu_id=${state.selectedMenu.id}&staff_id=${staffId}`
    );
    renderSlots(dateStr, data.slots);
  } catch (err) {
    slotsArea.innerHTML = `<div style="padding:16px;text-align:center;color:var(--danger)">${err.message}</div>`;
  }
}

function renderSlots(dateStr, slots = []) {
  const slotsArea = document.getElementById("slots-area");
  if (!slots.length) {
    slotsArea.innerHTML = '<div style="padding:16px;text-align:center;color:var(--gray-500)">この日は空き枠がありません</div>';
    return;
  }

  slotsArea.innerHTML = `
    <h3 style="margin:16px 0 8px;font-size:14px">${formatDateJa(dateStr + "T00:00:00")} の空き枠</h3>
    <div class="slot-grid">
      ${slots.map(s => `
        <button class="slot-btn ${state.selectedSlot?.start === s.start ? "selected" : ""}"
          onclick='selectSlot(${JSON.stringify(s)})'>
          ${formatTime(s.start)}
          ${s.staff_name ? `<br><span style="font-size:10px">${escapeHtml(s.staff_name)}</span>` : ""}
        </button>
      `).join("")}
    </div>
  `;
}

function selectSlot(slot) {
  state.selectedSlot = slot;
  document.querySelectorAll(".slot-btn").forEach(b => b.classList.remove("selected"));
  event.currentTarget.classList.add("selected");
  enableNext();
}

function changeMonth(delta) {
  state.calendarMonth += delta;
  if (state.calendarMonth < 0) { state.calendarMonth = 11; state.calendarYear--; }
  if (state.calendarMonth > 11) { state.calendarMonth = 0; state.calendarYear++; }
  renderCalendar();
}

// ──────────── Step 4: 顧客情報入力 ────────────

function renderInfoStep(container) {
  const c = state.customer;
  const isNew = !c?.name;

  container.innerHTML = `
    <p class="step-title">お客様情報を入力してください</p>
    <div class="form-group">
      <label>お名前 <span style="color:var(--danger)">*</span></label>
      <input type="text" id="i-name" value="${escapeHtml(c?.name || "")}" placeholder="山田 花子">
    </div>
    <div class="form-group">
      <label>ふりがな</label>
      <input type="text" id="i-kana" value="${escapeHtml(c?.name_kana || "")}" placeholder="やまだ はなこ">
    </div>
    <div class="form-group">
      <label>電話番号 <span style="color:var(--danger)">*</span></label>
      <input type="tel" id="i-phone" value="${escapeHtml(c?.phone || "")}" placeholder="090-1234-5678">
    </div>
    <div class="form-group">
      <label>メールアドレス</label>
      <input type="email" id="i-email" value="${escapeHtml(c?.email || "")}" placeholder="email@example.com">
    </div>
    <div class="form-group">
      <label>アレルギー・ご注意事項</label>
      <textarea id="i-allergy" placeholder="カラー剤アレルギーなど"></textarea>
    </div>
    <div class="form-group">
      <label>ご要望・備考</label>
      <textarea id="i-notes" placeholder="ご希望のスタイルや気になることをどうぞ"></textarea>
    </div>
    ${isNew ? '<p class="form-hint">初回ご利用ありがとうございます。次回以降は自動でご入力されます。</p>' : ""}
  `;

  // 入力変化で次へボタン有効化チェック
  ["i-name", "i-phone"].forEach(id => {
    document.getElementById(id).addEventListener("input", checkInfoValidity);
  });

  checkInfoValidity();
}

function checkInfoValidity() {
  const name = document.getElementById("i-name")?.value?.trim();
  const phone = document.getElementById("i-phone")?.value?.trim();
  if (name && phone) enableNext("確認へ進む");
}

// ──────────── Step 5: 確認画面 ────────────

function renderConfirmStep(container) {
  const menu = state.selectedMenu;
  const staff = state.selectedStaff;
  const slot = state.selectedSlot;
  const name = document.getElementById("i-name")?.value || state.customer?.name;
  const phone = document.getElementById("i-phone")?.value || state.customer?.phone;

  container.innerHTML = `
    <p class="step-title">予約内容を確認してください</p>
    <div class="confirm-card">
      <dl>
        <div class="confirm-row"><dt>メニュー</dt><dd>${escapeHtml(menu.name)}</dd></div>
        <div class="confirm-row"><dt>担当</dt><dd>${staff ? escapeHtml(staff.name) : "指名なし"}</dd></div>
        <div class="confirm-row"><dt>日時</dt><dd>${formatDateJa(slot.start)}<br>${formatTime(slot.start)}〜${formatTime(slot.end)}</dd></div>
        <div class="confirm-row"><dt>お名前</dt><dd>${escapeHtml(name || "")}</dd></div>
        <div class="confirm-row"><dt>電話番号</dt><dd>${escapeHtml(phone || "")}</dd></div>
        <div class="confirm-row"><dt>料金</dt><dd>${menu.price != null ? `¥${menu.price.toLocaleString()}` : "店頭にてご確認"}</dd></div>
      </dl>
    </div>
    <p style="font-size:12px;color:#adb5bd;text-align:center;padding:0 8px">
      「予約を確定する」を押すと予約が完了します。<br>
      LINEに確認メッセージが届きます。
    </p>
  `;

  enableNext("予約を確定する");
}

// ──────────── 予約送信 ────────────

async function submitReservation() {
  const btn = document.getElementById("btn-next");
  btn.disabled = true;
  btn.textContent = "送信中...";

  const name = document.getElementById("i-name")?.value;
  const phone = document.getElementById("i-phone")?.value;
  const email = document.getElementById("i-email")?.value;
  const kana = document.getElementById("i-kana")?.value;
  const notes = document.getElementById("i-notes")?.value;
  const allergy = document.getElementById("i-allergy")?.value;

  try {
    const res = await liffApi.post(
      `/liff/reservations?store_id=${state.storeId}`,
      {
        menu_id: state.selectedMenu.id,
        staff_id: state.selectedStaff?.id || null,
        start_datetime: state.selectedSlot.start,
        notes: notes || null,
        is_first_visit: state.customer?.is_first_visit,
        customer_name: name,
        customer_phone: phone,
        customer_email: email || null,
        customer_name_kana: kana || null,
        extra_data: allergy ? { allergy_notes: allergy } : {},
      }
    );

    // 完了画面表示
    document.getElementById("loading-overlay").style.display = "none";
    document.querySelector(".progress-bar").style.display = "none";
    document.getElementById("content").innerHTML = `
      <div class="complete-screen">
        <div class="complete-icon">🎉</div>
        <h2 style="font-size:20px;font-weight:800;margin-bottom:8px;color:#1a1a2e">予約が完了しました！</h2>
        <p style="color:#868e96;margin-bottom:24px;font-size:14px">
          LINEに予約確認メッセージをお送りしました。
        </p>
        <div class="complete-detail">
          <div class="confirm-row"><dt>予約番号</dt><dd style="font-family:monospace">${res.confirmation_code}</dd></div>
          <div class="confirm-row"><dt>メニュー</dt><dd>${escapeHtml(state.selectedMenu.name)}</dd></div>
          <div class="confirm-row"><dt>担当</dt><dd>${state.selectedStaff ? escapeHtml(state.selectedStaff.name) : "指名なし"}</dd></div>
          <div class="confirm-row"><dt>日時</dt><dd>${formatDateJa(state.selectedSlot.start)}<br>${formatTime(state.selectedSlot.start)}</dd></div>
        </div>
        <button class="btn-line" onclick="liff.closeWindow()">LINEに戻る</button>
      </div>
    `;
    document.getElementById("btn-next").style.display = "none";
    document.getElementById("btn-back").style.display = "none";

  } catch (err) {
    showError(err.message);
    btn.disabled = false;
    btn.textContent = "予約を確定する";
  }
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
