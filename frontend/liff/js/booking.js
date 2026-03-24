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
    <h2 style="font-size:16px;font-weight:600;margin-bottom:16px">メニューを選択してください</h2>
    ${Object.entries(categories).map(([cat, menus]) => `
      <h3 style="font-size:13px;color:var(--gray-500);margin:12px 0 6px">${escapeHtml(cat)}</h3>
      ${menus.map(m => `
        <div class="select-card ${state.selectedMenu?.id === m.id ? "selected" : ""}"
             onclick="selectMenu(${JSON.stringify(m).replace(/"/g, '&quot;')})">
          <div class="card-title">${escapeHtml(m.name)}</div>
          <div class="card-sub">
            ${m.duration_minutes}分
            ${m.price != null ? ` / ¥${m.price.toLocaleString()}` : ""}
            ${m.description ? ` / ${escapeHtml(m.description)}` : ""}
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
    <h2 style="font-size:16px;font-weight:600;margin-bottom:16px">担当を選択してください</h2>
    <div class="select-card ${state.selectedStaff === null ? "selected" : ""}"
         onclick="selectStaff(null)">
      <div class="card-title">指名なし（おまかせ）</div>
      <div class="card-sub">空きのあるスタッフが担当します</div>
    </div>
    ${state.staffList.map(s => `
      <div class="select-card ${state.selectedStaff?.id === s.id ? "selected" : ""}"
           onclick='selectStaff(${JSON.stringify(s)})'>
        ${s.image_url ? `<img src="${s.image_url}" style="width:48px;height:48px;border-radius:50%;float:left;margin-right:12px">` : ""}
        <div class="card-title">${escapeHtml(s.name)} ${s.role ? `<span style="font-weight:400;font-size:12px">${escapeHtml(s.role)}</span>` : ""}</div>
        ${s.bio ? `<div class="card-sub">${escapeHtml(s.bio)}</div>` : ""}
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
    <h2 style="font-size:16px;font-weight:600;margin-bottom:8px">日時を選択してください</h2>
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
    <h2 style="font-size:16px;font-weight:600;margin-bottom:16px">お客様情報を入力してください</h2>
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
    <h2 style="font-size:16px;font-weight:600;margin-bottom:16px">予約内容を確認してください</h2>
    <div style="background:#fff;border-radius:var(--radius);padding:16px;margin-bottom:16px">
      <dl>
        <div class="confirm-row"><dt>メニュー</dt><dd>${escapeHtml(menu.name)}</dd></div>
        <div class="confirm-row"><dt>担当</dt><dd>${staff ? escapeHtml(staff.name) : "指名なし"}</dd></div>
        <div class="confirm-row"><dt>日時</dt><dd>${formatDateJa(slot.start)} ${formatTime(slot.start)}〜${formatTime(slot.end)}</dd></div>
        <div class="confirm-row"><dt>お名前</dt><dd>${escapeHtml(name || "")}</dd></div>
        <div class="confirm-row"><dt>電話番号</dt><dd>${escapeHtml(phone || "")}</dd></div>
        <div class="confirm-row" style="border:none"><dt>料金</dt><dd>${menu.price != null ? `¥${menu.price.toLocaleString()}` : "店頭にてご確認"}</dd></div>
      </dl>
    </div>
    <p style="font-size:12px;color:var(--gray-500);text-align:center">
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
      <div style="text-align:center;padding:32px 16px">
        <div style="font-size:48px;margin-bottom:16px">✅</div>
        <h2 style="font-size:20px;font-weight:700;margin-bottom:8px">予約が完了しました</h2>
        <p style="color:var(--gray-500);margin-bottom:24px">
          LINEに予約確認メッセージをお送りしました。
        </p>
        <div style="background:#f9fafb;border-radius:8px;padding:16px;margin-bottom:24px;text-align:left">
          <div style="margin-bottom:8px"><strong>予約番号:</strong> ${res.confirmation_code}</div>
          <div style="margin-bottom:8px"><strong>メニュー:</strong> ${escapeHtml(state.selectedMenu.name)}</div>
          <div style="margin-bottom:8px"><strong>担当:</strong> ${state.selectedStaff ? escapeHtml(state.selectedStaff.name) : "指名なし"}</div>
          <div><strong>日時:</strong> ${formatDateJa(state.selectedSlot.start)} ${formatTime(state.selectedSlot.start)}</div>
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
