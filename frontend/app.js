// ============================================================================
// AlphaBuf — منطق الواجهة
// كل التفاعل (فلترة، ترتيب، فتح تفاصيل سهم) بيحصل في المتصفح من غير أي طلب جديد
// للسيرفر، إلا لما تحتاج بيانات فعلاً جديدة (فحص جديد، أخبار سهم معين).
// ============================================================================

const API_BASE = "";

let state = {
  sectors: {},
  results: [],
  dropped: [],
  totalStocks: 0,
  sortCol: null,
  sortDir: "desc",
  autoRefreshTimer: null,
  progressPollTimer: null,
  searchTimer: null,
  liveQuotesTimer: null,
  liveQuoteRequestInFlight: false,
  macroNewsTimer: null,
  macroNewsRequestInFlight: false,
  stockNewsTimer: null,
  stockNewsRequestTicker: null,
  activeStockTicker: null,
  lastCache: null,
  lastScanConfig: null,
  categoryFilters: {},
  columnFilters: {},
  sectorHorizons: {},
  columnOrders: loadColumnOrders(),
  user: null,
  authMode: "login",
  favorites: new Map(),
};

function loadColumnOrders() {
  try {
    const saved = JSON.parse(localStorage.getItem("alphabuf-column-orders") || "{}");
    return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
  } catch {
    return {};
  }
}

function saveColumnOrder(tableId, columns) {
  state.columnOrders[tableId] = columns;
  try {
    localStorage.setItem("alphabuf-column-orders", JSON.stringify(state.columnOrders));
  } catch {
    // Reordering remains available for this page when browser storage is unavailable.
  }
}

function scanConfigsMatch(first, second) {
  if (!first || !second) return false;
  return JSON.stringify({ ...first, sectors: [...(first.sectors || [])].sort() })
    === JSON.stringify({ ...second, sectors: [...(second.sectors || [])].sort() });
}

function enrichResult(row) {
  // تقييم واجهة تفسيري فقط: يجمع الإشارات الموجودة بالفعل ولا يستبدل منطق التحليل بالخادم.
  let score = 50;
  const decision = String(row["قرار السوينغ"] || "");
  const rsi = Number(row.RSI);
  const mfi = Number(row.MFI);
  const liquidity = Number(row["السيولة"]);

  if (/🔥|اشترِ الآن/.test(decision)) score += 20;
  else if (/اشترِ/.test(decision)) score += 12;
  else if (/لا تشترِ|⛔|❌/.test(decision)) score -= 18;
  if (Number.isFinite(rsi) && rsi >= 45 && rsi <= 68) score += 7;
  else if (Number.isFinite(rsi) && (rsi > 75 || rsi < 25)) score -= 6;
  if (Number.isFinite(mfi) && mfi >= 50) score += 7;
  if (Number.isFinite(liquidity) && liquidity >= 1.5) score += 8;
  if (String(row["مستوى المخاطرة"] || "").includes("مرتفع")) score -= 7;

  return { ...row, "قوة الإشارة": Math.max(0, Math.min(100, Math.round(score))) };
}

function signalLabel(score) {
  if (score >= 75) return "قوية";
  if (score >= 55) return "متوازنة";
  return "حذرة";
}

const RESULT_COLUMNS = [
  ["اسم الشركة", "الشركة", "text"],
  ["الرمز", "الرمز", "text"],
  ["قوة الإشارة", "قوة الإشارة", "score"],
  ["قرار السوينغ", "قرار السوينغ", "badge"],
  ["نصيحة المالك", "نصيحة المالك", "badge"],
  ["نوع السهم", "تصنيف فني", "text"],
  ["مستوى المخاطرة", "المخاطر", "text"],
  ["حالة EGX33 Shariah", "حالة EGX33 Shariah", "text"],
  ["القطاع", "القطاع", "text"],
  ["السعر", "السعر", "num"],
  ["سعر شراء مقترح", "نقطة دخول", "num"],
  ["سعر بيع مقترح", "نقطة خروج", "num"],
  ["وقف الخسارة", "وقف الخسارة", "num"],
  ["هدف جني الأرباح", "هدف أول", "num"],
  ["مصدر السعر", "المصدر", "text"],
  ["التغير %", "التغير %", "pct"],
  ["تقدير أسبوع", "مدى حركة أسبوعي", "forecast"],
  ["تقدير شهر", "مدى حركة شهري", "forecast"],
  ["تقدير ربع سنوي", "مدى حركة ربع سنوي", "forecast"],
  ["تقدير نصف سنوي", "مدى حركة نصف سنوي", "forecast"],
  ["تقدير سنوي", "مدى حركة سنوي", "forecast"],
  ["RSI", "RSI", "num"],
  ["MFI", "MFI", "num"],
  ["السيولة", "السيولة", "num"],
];

const GROWTH_COLUMNS = [
  ["اسم الشركة", "الشركة", "text"],
  ["الرمز", "الرمز", "text"],
  ["القطاع", "القطاع", "text"],
  ["السعر", "السعر", "num"],
  ["التغير %", "التغير %", "pct"],
  ["MFI", "MFI", "num"],
  ["السيولة", "السيولة", "num"],
  ["القيمة السوقية", "القيمة السوقية", "num"],
  ["متوسط 50 يوم", "SMA50", "num"],
  ["متوسط 200 يوم", "SMA200", "num"],
  ["قرار السوينغ", "قرار السوينغ", "badge"],
];

async function init() {
  await loadCurrentUser();
  recordVisit();
  await Promise.all([loadSectors(), loadTimeframes(), loadMacroPrices()]);
  bindEvents();
  await initializeLatestScan();
  startLiveQuotesPolling();
}

function updateUserControls() {
  const user = state.user;
  document.getElementById("userState").textContent = user?.kind === "account" ? user.email : "زائر";
  document.getElementById("authOpen").hidden = Boolean(user?.kind === "account");
  document.getElementById("logoutBtn").hidden = !user;
  document.getElementById("adminOpen").hidden = !user?.is_admin;
  document.getElementById("manualNewsRetry").hidden = !user?.is_admin;
}

async function loadCurrentUser() {
  try {
    const response = await fetch(`${API_BASE}/api/auth/me`);
    const data = await response.json();
    state.user = data.user;
  } catch {
    state.user = null;
  }
  updateUserControls();
  await loadFavorites();
}

async function loadFavorites() {
  if (state.user?.kind !== "account") {
    state.favorites = new Map();
    renderFavorites();
    return;
  }
  try {
    const response = await fetch(`${API_BASE}/api/favorites`);
    const data = await response.json();
    state.favorites = new Map((data.items || []).map(item => [item.ticker, item]));
  } catch {
    state.favorites = new Map();
  }
  renderFavorites();
}

function renderFavorites() {
  const container = document.getElementById("favoritesList");
  const count = document.getElementById("favoritesCount");
  if (!container || !count) return;
  if (state.user?.kind !== "account") {
    count.textContent = "حساب مطلوب";
    container.innerHTML = `<p class="text-tertiary">سجّل دخولك أو أنشئ حساباً لحفظ الأسهم ومتابعتها من أي جهاز.</p><button class="btn btn-ghost" id="favoritesLoginBtn">تسجيل الدخول</button>`;
    document.getElementById("favoritesLoginBtn")?.addEventListener("click", () => openOverlay("authOverlay"));
    return;
  }
  const items = [...state.favorites.values()];
  count.textContent = `${items.length} سهم`;
  if (!items.length) {
    container.innerHTML = '<p class="text-tertiary">افتح تفاصيل أي سهم من نتائج الفحص ثم اضغط «إضافة إلى المفضلة».</p>';
    return;
  }
  container.innerHTML = items.map(item => {
    const latest = state.results.find(row => row["الرمز"] === item.ticker);
    const change = Number(latest?.["التغير %"]);
    const changeText = Number.isFinite(change) ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%` : "—";
    const changeClass = change > 0 ? "pct-up" : change < 0 ? "pct-down" : "";
    return `<article class="favorite-card" data-favorite-ticker="${escapeHtml(item.ticker)}"><div><strong>${escapeHtml(latest?.["اسم الشركة"] || item.name)}</strong><small>${escapeHtml(latest?.["القطاع"] || item.sector)} · <span class="num">${escapeHtml(item.ticker)}</span></small></div><div class="favorite-price"><b class="num">${latest?.["السعر"] ?? "—"}</b><span class="num ${changeClass}">${changeText}</span></div><button type="button" class="top-action" data-remove-favorite="${escapeHtml(item.ticker)}">إزالة</button></article>`;
  }).join("");
  container.querySelectorAll("[data-remove-favorite]").forEach(button => button.addEventListener("click", () => toggleFavoriteByTicker(button.dataset.removeFavorite)));
  container.querySelectorAll("[data-favorite-ticker]").forEach(card => card.addEventListener("click", event => {
    if (event.target.closest("button")) return;
    const row = state.results.find(item => item["الرمز"] === card.dataset.favoriteTicker);
    if (row) openStockDetail(row);
  }));
}

async function toggleFavorite(row) {
  if (state.user?.kind !== "account") {
    openOverlay("authOverlay");
    document.getElementById("authError").textContent = "سجّل الدخول لحفظ المفضلات داخل حسابك.";
    return;
  }
  const ticker = row["الرمز"];
  if (state.favorites.has(ticker)) {
    await toggleFavoriteByTicker(ticker);
    return;
  }
  const response = await fetch(`${API_BASE}/api/favorites`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker, name: row["اسم الشركة"], sector: row["القطاع"] }) });
  const data = await response.json();
  if (!response.ok) return;
  state.favorites.set(data.item.ticker, data.item);
  renderFavorites();
  const button = document.getElementById("favoriteToggle");
  if (button) button.textContent = "★ إزالة من المفضلة";
}

async function toggleFavoriteByTicker(ticker) {
  const response = await fetch(`${API_BASE}/api/favorites/${encodeURIComponent(ticker)}`, { method: "DELETE" });
  if (!response.ok) return;
  state.favorites.delete(ticker);
  renderFavorites();
  const button = document.getElementById("favoriteToggle");
  if (button) button.textContent = "☆ إضافة إلى المفضلة";
}

function openOverlay(id) {
  const overlay = document.getElementById(id);
  overlay.classList.add("open");
  overlay.setAttribute("aria-hidden", "false");
}

function closeOverlay(id) {
  const overlay = document.getElementById(id);
  overlay.classList.remove("open");
  overlay.setAttribute("aria-hidden", "true");
}

function setAuthMode(mode) {
  state.authMode = mode;
  document.querySelectorAll("[data-auth-mode]").forEach(button => {
    button.classList.toggle("active", button.dataset.authMode === mode);
  });
  document.getElementById("authSubmit").textContent = mode === "register" ? "إنشاء الحساب" : "تسجيل الدخول";
  document.getElementById("authPassword").autocomplete = mode === "register" ? "new-password" : "current-password";
  document.getElementById("authError").textContent = "";
}

async function submitAuth(event) {
  event.preventDefault();
  const error = document.getElementById("authError");
  error.textContent = "";
  const payload = { email: document.getElementById("authEmail").value, password: document.getElementById("authPassword").value };
  try {
    const response = await fetch(`${API_BASE}/api/auth/${state.authMode}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "تعذر إتمام العملية");
    state.user = data.user;
    updateUserControls();
    await loadFavorites();
    closeOverlay("authOverlay");
  } catch (err) {
    error.textContent = err.message || "تعذر إتمام العملية";
  }
}

async function continueAsGuest() {
  const response = await fetch(`${API_BASE}/api/auth/guest`, { method: "POST" });
  const data = await response.json();
  if (response.ok) {
    state.user = data.user;
    updateUserControls();
    await loadFavorites();
    closeOverlay("authOverlay");
  }
}

async function logout() {
  await fetch(`${API_BASE}/api/auth/logout`, { method: "POST" });
  state.user = null;
  updateUserControls();
  await loadFavorites();
}

function recordVisit() {
  fetch(`${API_BASE}/api/telemetry/visit`, { method: "POST" }).catch(() => {});
}

async function openAdminDashboard() {
  openOverlay("adminOverlay");
  const target = document.getElementById("adminMetrics");
  target.textContent = "جارٍ تحميل الإحصاءات…";
  try {
    const response = await fetch(`${API_BASE}/api/admin/metrics`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "تعذر تحميل الإحصاءات");
    const days = (data.daily || []).map(item => `${escapeHtml(item.visit_day)}: <strong>${Number(item.visits)}</strong>`).join(" · ") || "لا توجد زيارات مسجلة بعد";
    target.innerHTML = `<div class="metric-card"><strong>${Number(data.total_visits)}</strong><span>إجمالي الزيارات اليومية المسجلة</span></div>
      <div class="metric-card"><strong>${Number(data.unique_visitors)}</strong><span>زوار فريدون تقريبياً</span></div>
      <div class="metric-card"><strong>${Number(data.accounts)}</strong><span>حسابات مستخدمين</span></div>
      <div class="metric-days">آخر 7 أيام: ${days}</div>`;
  } catch (err) {
    target.textContent = err.message || "تعذر تحميل الإحصاءات";
  }
}

async function downloadAdminBackup() {
  const button = document.getElementById("adminBackupBtn");
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "جارٍ تجهيز النسخة…";
  try {
    const response = await fetch(`${API_BASE}/api/admin/backup`);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "تعذر إنشاء النسخة الاحتياطية");
    }
    const disposition = response.headers.get("content-disposition") || "";
    const filename = disposition.match(/filename=\"?([^\";]+)\"?/)?.[1] || "alphabuf-backup.sqlite3";
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message || "تعذر تنزيل النسخة الاحتياطية");
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

async function loadSectors() {
  const resp = await fetch(`${API_BASE}/api/sectors`);
  const data = await resp.json();
  state.sectors = data.sectors;
  const container = document.getElementById("sectorList");
  container.innerHTML = Object.keys(data.sectors).map(sector => `
    <label class="checkbox-row">
      <input type="checkbox" class="sector-checkbox" value="${sector}">
      ${sector} (${data.sectors[sector].length})
    </label>
  `).join("");
}

async function loadTimeframes() {
  const resp = await fetch(`${API_BASE}/api/timeframes`);
  const data = await resp.json();
  const select = document.getElementById("timeframeSelect");
  select.innerHTML = data.timeframes.map(tf => `<option value="${tf}">${tf}</option>`).join("");
}

async function loadMacroPrices() {
  try {
    const resp = await fetch(`${API_BASE}/api/macro/prices`);
    const data = await resp.json();
    const el = document.getElementById("pulseItems");
    const entries = Object.entries(data);
    if (entries.length === 0) {
      el.textContent = "تعذّر جلب أسعار السوق العالمية حالياً";
      return;
    }
    el.innerHTML = entries.map(([label, info]) => {
      const dir = info.change_pct >= 0 ? "up" : "down";
      const sign = info.change_pct >= 0 ? "+" : "";
      return `
        <span class="pulse-item">
          <span class="pulse-label">${label}</span>
          <span class="pulse-value">${info.price}</span>
          <span class="pulse-delta ${dir}">${sign}${info.change_pct}%</span>
        </span>`;
    }).join("");
  } catch (e) {
    document.getElementById("pulseItems").textContent = "تعذّر جلب أسعار السوق العالمية";
  }
}

async function initializeLatestScan() {
  const status = document.getElementById("scanStatus");
  setScanStatus("جاري التحقق من أحدث فحص محفوظ…");
  showScanProgress("التحقق من بيانات السوق…", null);
  try {
    const response = await fetch(`${API_BASE}/api/scan/latest`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);

    if (data.status === "ready" || data.status === "refreshing") {
      applyScanData(data);
      setScanStatus(data.status === "refreshing"
        ? "نعرض أحدث فحص محفوظ، ويجري تحديث بيانات الإطار اليومي في الخلفية."
        : `تم تحميل أحدث بيانات الفحص اليومي المحفوظة. ${formatCacheExpiry(data.cache?.expires_at)}`, "success");
      scheduleAutoRefresh(data.cache || {});
      if (data.status === "refreshing") pollLatestScan();
      else hideScanProgress();
      return;
    }

    if (data.status === "running") {
      setScanStatus("يتم تجهيز أول فحص للسوق على الخادم؛ ستظهر النتائج تلقائيًا عند اكتماله.");
      updateProgress(data.progress);
      pollLatestScan();
      return;
    }

    status.textContent = "لا توجد نتيجة بعد؛ جارٍ بدء أول فحص للسوق.";
    await runScan({ automatic: true });
  } catch (error) {
    setScanStatus(`تعذّر تحميل الفحص المحفوظ: ${error.message}`, "error");
    hideScanProgress();
  }
}

async function pollLatestScan() {
  clearTimeout(state.progressPollTimer);
  try {
    const response = await fetch(`${API_BASE}/api/scan/latest`, { cache: "no-store" });
    const data = await response.json();
    if (data.status === "running") {
      updateProgress(data.progress);
      state.progressPollTimer = setTimeout(pollLatestScan, 2000);
      return;
    }
    if (data.status === "ready" || data.status === "refreshing") {
      applyScanData(data);
      setScanStatus(data.status === "refreshing"
        ? "تم تحميل النتيجة السابقة؛ تحديث الفحص اليومي مستمر في الخلفية."
        : `اكتمل الفحص اليومي على الخادم، وعُرضت أحدث البيانات. ${formatCacheExpiry(data.cache?.expires_at)}`, "success");
      if (data.status === "refreshing") {
        updateProgress(data.progress);
        state.progressPollTimer = setTimeout(pollLatestScan, 2000);
      } else {
        hideScanProgress();
        scheduleAutoRefresh(data.cache || {});
      }
    }
  } catch {
    state.progressPollTimer = setTimeout(pollLatestScan, 5000);
  }
}

function showScanProgress(label, progress = null) {
  document.getElementById("scanProgressWrap").hidden = false;
  document.getElementById("scanProgressText").textContent = label;
  updateProgress(progress);
}

function updateProgress(progress) {
  const bar = document.getElementById("scanProgress");
  const percent = document.getElementById("scanProgressPercent");
  const text = document.getElementById("scanProgressText");
  if (!progress || !progress.total) {
    bar.removeAttribute("value");
    percent.textContent = "…";
    return;
  }
  bar.value = progress.percent || 0;
  percent.textContent = `${progress.percent || 0}%`;
  text.textContent = `تم تحليل ${progress.completed} من ${progress.total} سهم`;
}

function hideScanProgress() {
  document.getElementById("scanProgressWrap").hidden = true;
}

function applyScanData(data) {
  if (!Array.isArray(data.results) || !Array.isArray(data.dropped)) return;
  state.results = data.results.map(enrichResult)
    .sort((first, second) => second["قوة الإشارة"] - first["قوة الإشارة"]);
  state.sortCol = "قوة الإشارة";
  state.sortDir = "desc";
  state.dropped = data.dropped;
  state.totalStocks = data.total_stocks;
  state.lastCache = data.cache || null;
  state.lastScanConfig = data.scan_config || null;
  state.sectorHorizons = data.sector_horizons || {};
  renderStats();
  renderSectorPerformance(state.results);
  applySearch();
  renderGrowthTable(state.results);
  renderFavorites();
  renderDroppedTable(state.dropped);
  renderHistory(data.history || []);
  document.getElementById("exportBtn").disabled = state.results.length === 0;
  updateScanButtonState();
}

function getCurrentScanConfig() {
  return {
    sectors: Array.from(document.querySelectorAll(".sector-checkbox:checked")).map(el => el.value).sort(),
    timeframe: document.getElementById("timeframeSelect").value,
    min_daily_turnover: parseFloat(document.getElementById("minTurnover").value) || 0,
    use_investing_primary: document.getElementById("useInvestingPrimary").checked,
  };
}

function updateScanButtonState() {
  const button = document.getElementById("scanBtn");
  const cachedConfig = state.lastScanConfig;
  const currentConfig = getCurrentScanConfig();
  const matches = scanConfigsMatch(cachedConfig, currentConfig);
  const hasFreshResult = matches && state.lastCache?.expires_at && Date.parse(state.lastCache.expires_at) > Date.now();
  button.textContent = hasFreshResult
    ? `✅ أحدث فحص ${currentConfig.timeframe} متاح — عرض أو إعادة الفحص`
    : `🚀 فحص ${currentConfig.timeframe || "السوق"}`;
}

async function runScan(options = {}) {
  const btn = document.getElementById("scanBtn");
  const automatic = options.automatic === true;
  let forceRefresh = options.forceRefresh === true;
  const currentConfig = getCurrentScanConfig();
  const currentIsCachedConfig = scanConfigsMatch(state.lastScanConfig, currentConfig);
  if (!automatic && currentIsCachedConfig && state.lastCache?.expires_at && Date.parse(state.lastCache.expires_at) > Date.now()) {
    const expiresLabel = formatCacheExpiry(state.lastCache.expires_at);
    const refreshConfirmed = window.confirm(`الفحص موجود بالفعل وهو أحدث بيانات لهذا الإطار الزمني.\n${expiresLabel}\n\nهل تريد إعادة الفحص الآن؟\nموافق: إعادة الفحص الآن\nإلغاء: عرض أحدث نتيجة محفوظة`);
    if (!refreshConfirmed) {
      setScanStatus(`تم الإبقاء على أحدث بيانات الإطار الحالي. ${expiresLabel}`, "success");
      return;
    }
    forceRefresh = true;
  }
  if (!automatic) clearTimeout(state.autoRefreshTimer);
  clearTimeout(state.progressPollTimer);
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> ${automatic ? "جاري تحديث بيانات الفحص…" : "جاري الفحص…"}`;
  setScanStatus(automatic ? "بدأ التحديث التلقائي حسب صلاحية الإطار الزمني…" : "جاري تحميل بيانات السوق وتحليل الأسهم…");
  showScanProgress("جاري تجهيز الأسهم…", null);

  const payload = {
    ...currentConfig,
    force_refresh: forceRefresh,
  };

  const pollProgress = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/scan/status`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), cache: "no-store",
      });
      const progressData = await response.json();
      updateProgress(progressData.progress);
    } catch { /* Keep the progress indicator alive if one status poll fails. */ }
  };
  await pollProgress();
  state.progressPollTimer = setInterval(pollProgress, 1500);

  try {
    const resp = await fetch(`${API_BASE}/api/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const responseText = await resp.text();
    let data;
    try {
      data = responseText ? JSON.parse(responseText) : {};
    } catch {
      const message = responseText.trim().slice(0, 500) || "استجابة فارغة من الخادم";
      throw new Error(`الخادم رجّع استجابة غير صالحة (HTTP ${resp.status}): ${message}`);
    }
    if (!resp.ok) {
      throw new Error(data.detail || data.message || `فشل الطلب (HTTP ${resp.status})`);
    }
    if (!Array.isArray(data.results) || !Array.isArray(data.dropped)) {
      throw new Error("استجابة الفحص ناقصة: لم تصل قوائم النتائج والاستبعادات بالشكل المتوقع.");
    }
    applyScanData(data);
    const cache = data.cache || {};
    if (cache.status === "cached") {
      setScanStatus(`تم عرض نتيجة محفوظة · إجمالي الأسهم: ${data.total_stocks} · ${formatCacheExpiry(cache.expires_at)}`, "success");
    } else if (cache.status === "refreshing") {
      setScanStatus(`نعرض آخر نتيجة محفوظة، ويجري تحديثها الآن في الخلفية · ${formatCacheExpiry(cache.expires_at)}`);
    } else {
      setScanStatus(`اكتمل الفحص: ${data.results.length} سهم مطابق من ${data.total_stocks} · زمن الفحص ${data.elapsed_seconds ?? "—"} ثانية. ${formatCacheExpiry(cache.expires_at)}`, "success");
    }
    scheduleAutoRefresh(cache);
    document.getElementById("scanProgress").value = 100;
    document.getElementById("scanProgressPercent").textContent = "100%";
    document.getElementById("scanProgressText").textContent = "اكتمل الفحص";
    setTimeout(hideScanProgress, 1200);
  } catch (e) {
    setScanStatus(`فشل الفحص: ${e.message}`, "error");
  } finally {
    clearInterval(state.progressPollTimer);
    btn.disabled = false;
    updateScanButtonState();
  }
}

function setScanStatus(message, tone = "") {
  const status = document.getElementById("scanStatus");
  status.textContent = message;
  status.className = `scan-status visible ${tone}`.trim();
}

function formatCacheExpiry(value) {
  if (!value) return "موعد التحديث التلقائي غير متاح";
  const expiry = new Date(value);
  return `التحديث التالي ${expiry.toLocaleString("ar-EG")}`;
}

function scheduleAutoRefresh(cache) {
  clearTimeout(state.autoRefreshTimer);
  const scheduledConfig = state.lastScanConfig && {
    ...state.lastScanConfig,
    sectors: [...(state.lastScanConfig.sectors || [])],
  };
  const refreshIfStillRelevant = () => {
    // لا تبدأ فحصاً جديداً لإعدادات غيّرها المستخدم منذ تحميل النتيجة.
    if (scheduledConfig && scanConfigsMatch(getCurrentScanConfig(), scheduledConfig)) {
      runScan({ automatic: true });
    }
  };
  if (cache.status === "refreshing") {
    state.autoRefreshTimer = setTimeout(refreshIfStillRelevant, 10000);
    return;
  }
  const expiresAt = Date.parse(cache.expires_at || "");
  if (Number.isNaN(expiresAt)) return;
  const delay = Math.max(1000, expiresAt - Date.now());
  state.autoRefreshTimer = setTimeout(refreshIfStillRelevant, Math.min(delay, 2147480000));
}

function renderStats() {
  document.getElementById("statRow").style.display = "flex";
  document.getElementById("statTotal").textContent = state.totalStocks;
  document.getElementById("statMatched").textContent = state.results.length;
  document.getElementById("statExcluded").textContent = state.dropped.length;
  const avgChange = state.results.length
    ? (state.results.reduce((s, r) => s + (Number(r["التغير %"]) || 0), 0) / state.results.length).toFixed(2)
    : "0.00";
  document.getElementById("statAvgChange").textContent = avgChange + "%";
  const summary = document.getElementById("signalSummary");
  if (summary) {
    const strong = state.results.filter(row => row["قوة الإشارة"] >= 75).length;
    const balanced = state.results.filter(row => row["قوة الإشارة"] >= 55 && row["قوة الإشارة"] < 75).length;
    summary.innerHTML = `<span><strong>${strong}</strong> إشارة قوية</span><span><strong>${balanced}</strong> فرصة متوازنة</span><span>التقييم للتصفية والمقارنة، وليس توصية</span>`;
    summary.hidden = false;
  }
}

function updateLiveQuoteStatus(message, tone = "") {
  const element = document.getElementById("liveQuoteStatus");
  if (!element) return;
  element.textContent = message;
  element.dataset.tone = tone;
}

function scheduleLiveQuotes(delay = 60000) {
  clearTimeout(state.liveQuotesTimer);
  state.liveQuotesTimer = setTimeout(refreshLiveQuotes, delay);
}

async function refreshLiveQuotes() {
  if (document.hidden) {
    scheduleLiveQuotes();
    return;
  }
  if (state.liveQuoteRequestInFlight) return;
  state.liveQuoteRequestInFlight = true;
  try {
    const response = await fetch(`${API_BASE}/api/market/live-quotes`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "تعذر تحميل الأسعار");
    const quotes = data.quotes || {};
    let updated = false;
    state.results = state.results.map(row => {
      const quote = quotes[String(row["الرمز"] || "").toUpperCase()];
      const price = Number(quote?.price);
      if (!Number.isFinite(price)) return row;
      updated = true;
      const next = { ...row, "السعر": price, "مصدر السعر": "متابعة تلقائية للسوق" };
      const change = Number(quote.change_pct);
      if (Number.isFinite(change)) next["التغير %"] = change;
      return next;
    });
    if (updated) {
      renderStats();
      renderSectorPerformance(state.results);
      applySearch();
      renderGrowthTable(state.results);
      renderFavorites();
    }
    updateLiveQuoteStatus(`تحديث تلقائي للأسعار: ${new Date().toLocaleTimeString("ar-EG")}`, "success");
  } catch {
    updateLiveQuoteStatus("تعذر التحديث التلقائي للأسعار؛ ستتم إعادة المحاولة", "error");
  } finally {
    state.liveQuoteRequestInFlight = false;
    scheduleLiveQuotes();
  }
}

function startLiveQuotesPolling() {
  clearTimeout(state.liveQuotesTimer);
  refreshLiveQuotes();
}

function renderSectorPerformance(rows) {
  const panel = document.getElementById("sectorPerformancePanel");
  const body = document.getElementById("sectorPerformanceBody");
  const count = document.getElementById("sectorPerformanceCount");
  const chart = document.getElementById("sectorPerformanceChart");
  if (!rows || rows.length === 0) {
    panel.style.display = "none";
    body.replaceChildren();
    chart.replaceChildren();
    return;
  }

  const groups = new Map();
  rows.forEach(row => {
    const sector = row["القطاع"] || "غير مصنف";
    if (!groups.has(sector)) groups.set(sector, []);
    groups.get(sector).push(row);
  });

  const summaries = [...groups.entries()].map(([sector, stocks]) => {
    const ranked = stocks.filter(stock => Number.isFinite(Number(stock["التغير %"])))
      .sort((a, b) => Number(b["التغير %"]) - Number(a["التغير %"]));
    const average = ranked.length
      ? ranked.reduce((total, stock) => total + Number(stock["التغير %"]), 0) / ranked.length
      : null;
    return { sector, stocks, ranked, average };
  }).sort((a, b) => (b.average ?? -Infinity) - (a.average ?? -Infinity));

  const largestMove = Math.max(1, ...summaries.map(item => Math.abs(item.average ?? 0)));
  chart.innerHTML = summaries.map(({ sector, average }) => {
    const width = Math.min(100, Math.abs(average ?? 0) / largestMove * 100);
    const trend = average > 0 ? "up" : average < 0 ? "down" : "flat";
    return `<div class="sector-chart-row"><span>${escapeHtml(sector)}</span><div class="sector-chart-track"><i class="${trend}" style="width:${width}%"></i></div><b class="num ${trend === "up" ? "pct-up" : trend === "down" ? "pct-down" : ""}">${average === null ? "—" : `${average > 0 ? "+" : ""}${average.toFixed(2)}%`}</b></div>`;
  }).join("");

  body.innerHTML = summaries.map(({ sector, stocks, ranked, average }) => {
    const leader = ranked[0];
    const avgClass = average > 0 ? "pct-up" : average < 0 ? "pct-down" : "";
    const leaderChange = leader ? Number(leader["التغير %"]) : null;
    const leaderClass = leaderChange > 0 ? "pct-up" : leaderChange < 0 ? "pct-down" : "";
    const stockList = stocks.slice().sort((a, b) => Number(b["التغير %"]) - Number(a["التغير %"])).slice(0, 12)
      .map(stock => `<li><span>${escapeHtml(stock["اسم الشركة"] || "—")}</span><b class="num ${Number(stock["التغير %"]) > 0 ? "pct-up" : Number(stock["التغير %"]) < 0 ? "pct-down" : ""}">${Number.isFinite(Number(stock["التغير %"])) ? `${Number(stock["التغير %"]) > 0 ? "+" : ""}${Number(stock["التغير %"]).toFixed(2)}%` : "—"}</b></li>`).join("");
    return `
      <tr>
        <td>${escapeHtml(sector)}</td>
        <td><span class="sector-count-popover" tabindex="0">${stocks.length}<span class="sector-stock-tooltip" role="tooltip"><strong>${escapeHtml(sector)}</strong><small>أول ${Math.min(stocks.length, 12)} شركة حسب التغير</small><ul>${stockList}</ul></span></span></td>
        <td>${average === null ? "—" : `<span class="num ${avgClass}">${average > 0 ? "+" : ""}${average.toFixed(2)}%</span>`}</td>
        <td>${leader ? `<div class="sector-leader"><span class="sector-leader-name">${escapeHtml(leader["اسم الشركة"] || "—")}</span><span class="sector-leader-ticker">${escapeHtml(leader["الرمز"] || "")}</span><span class="num ${leaderClass}">${leaderChange > 0 ? "+" : ""}${leaderChange.toFixed(2)}%</span></div>` : "—"}</td>
      </tr>`;
  }).join("");

  count.textContent = `${summaries.length} قطاع`;
  panel.style.display = "block";
}

function renderHistory(history) {
  const panel = document.getElementById("historyPanel");
  const overallBody = document.getElementById("historyOverallBody");
  const sectorBody = document.getElementById("historySectorBody");
  const description = document.getElementById("historyDescription");
  const count = document.getElementById("historyCount");
  if (!history.length) {
    panel.style.display = "none";
    overallBody.replaceChildren();
    sectorBody.replaceChildren();
    return;
  }

  const latest = history.at(-1);
  const previous = history.at(-2);
  overallBody.innerHTML = [...history].reverse().slice(0, 10).map(item => {
    const scanReturn = Number.isFinite(Number(item.scan_return_pct))
      ? `${formatPercent(item.scan_return_pct)}<small class="horizon-asof">على ${item.compared_stock_count || 0} سهم مشترك</small>`
      : '<span class="text-tertiary">يلزم فحصان بأسعار قابلة للمقارنة</span>';
    return `<tr><td>${escapeHtml(new Date(item.captured_at).toLocaleString("ar-EG"))}</td>
      <td class="num">${item.matched_count} / ${item.total_stocks}</td>
      <td>${formatPercent(item.average_change)}</td><td>${scanReturn}</td></tr>`;
  }).join("");

  const sectorNames = new Set([
    ...Object.keys(latest.sector_performance || {}),
    ...Object.keys(previous?.sector_performance || {}),
  ]);
  const horizonSummary = state.sectorHorizons || {};
  sectorBody.innerHTML = [...sectorNames].sort((a, b) => a.localeCompare(b, "ar")).map(sector => {
    const horizons = horizonSummary[sector]?.periods || {};
    const cells = ["ربع سنوي", "نصف سنوي", "سنوي"].map(label => {
      const item = horizons[label];
      if (!item || item.current_return == null) return "<td class=\"text-tertiary\">بيانات تاريخية غير مكتملة من المصدر</td>";
      const asOf = item.captured_at ? new Date(item.captured_at).toLocaleDateString("ar-EG") : "من أسعار السهم التاريخية";
      const delta = item.change_points == null ? "لا توجد لقطة مقارنة محفوظة بعد" : `مقارنة باللقطة: ${item.change_points > 0 ? "+" : ""}${item.change_points.toFixed(2)} نقطة`;
      return `<td>${formatPercent(item.current_return)}<small class="horizon-asof">${escapeHtml(asOf)} · ${escapeHtml(delta)}</small></td>`;
    }).join("");
    return `<tr><td>${escapeHtml(sector)}</td>${cells}</tr>`;
  }).join("");

  const timestamp = new Date(latest.captured_at).toLocaleString("ar-EG");
  description.textContent = previous
    ? `آخر مقارنة ${timestamp} مقابل ${new Date(previous.captured_at).toLocaleString("ar-EG")} · محفوظة لكل إعدادات الفحص.`
    : `تم حفظ أول نقطة مقارنة في ${timestamp}. ستظهر مقارنة زمنية بعد الفحص التالي.`;
  count.textContent = `${history.length} لقطة محفوظة`;
  document.getElementById("historyPanel").style.display = "block";
}

function formatPercent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  const number = Number(value);
  return `<span class="num ${number > 0 ? "pct-up" : number < 0 ? "pct-down" : ""}">${number > 0 ? "+" : ""}${number.toFixed(2)}%</span>`;
}

function formatDelta(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "<span class=\"text-tertiary\">لا توجد مقارنة بعد</span>";
  const number = Number(value);
  const label = number > 0 ? "تحسن" : number < 0 ? "تراجع" : "بدون تغيير";
  return `<span class="num history-delta ${number > 0 ? "pct-up" : number < 0 ? "pct-down" : ""}">${label} ${number > 0 ? "+" : ""}${number.toFixed(2)} نقطة مئوية</span>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatMixedDirectionText(value) {
  const text = String(value).replace(/\u200e/g, "");
  const mixedRun = /[A-Za-z][A-Za-z0-9.+/#-]*|[+-]?\d+(?:[.,]\d+)?(?:%|x)?/g;
  let html = "";
  let start = 0;
  for (const match of text.matchAll(mixedRun)) {
    html += escapeHtml(text.slice(start, match.index));
    html += `<bdi class="bidi-ltr" dir="ltr">${escapeHtml(match[0])}</bdi>`;
    start = match.index + match[0].length;
  }
  return html + escapeHtml(text.slice(start));
}

function formatCell(value, type) {
  if (type === "score") {
    const score = Number(value);
    if (!Number.isFinite(score)) return '<span style="color:var(--text-tertiary)">—</span>';
    const tone = score >= 75 ? "strong" : score >= 55 ? "balanced" : "cautious";
    return `<span class="signal-score ${tone}"><b>${score}</b><small>${signalLabel(score)}</small></span>`;
  }
  if (type === "forecast") {
    if (value === null || value === undefined || typeof value !== "object" || value.low_pct === undefined || value.high_pct === undefined) {
      return '<span class="forecast-unavailable" title="تحتاج بيانات يومية تاريخية كافية">غير متاح</span>';
    }
    return `<span class="forecast-range" title="نطاق سعري تاريخي تقريبي: ${value.low_price} إلى ${value.high_price}">${value.low_pct > 0 ? "+" : ""}${value.low_pct}% إلى ${value.high_pct > 0 ? "+" : ""}${value.high_pct}%</span>`;
  }
  if (value === null || value === undefined) return '<span style="color:var(--text-tertiary)">—</span>';
  if (type === "num") return `<span class="num">${escapeHtml(typeof value === "number" ? value.toLocaleString("en-US") : value)}</span>`;
  if (type === "pct") {
    const cls = value >= 0 ? "pct-up" : "pct-down";
    const sign = value >= 0 ? "+" : "";
    return `<span class="num ${cls}">${escapeHtml(sign)}${escapeHtml(value)}%</span>`;
  }
  if (type === "badge") {
    const cls = /اشترِ|استمر|احتفظ/.test(value) ? "pct-up" : (/لا تشترِ|اخرج|جني/.test(value) ? "pct-down" : "");
    return `<span class="badge ${cls}">${escapeHtml(value)}</span>`;
  }
  return escapeHtml(value);
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value, window.location.origin);
    return url.protocol === "https:" ? url.href : "";
  } catch {
    return "";
  }
}

function renderTable(rows, columns, headEl, bodyEl, emptyEl, onRowClick) {
  const tableId = headEl.closest("table")?.id || "default";
  if (!rows || rows.length === 0) {
    bodyEl.innerHTML = "";
    emptyEl.style.display = "block";
    if (tableId !== "resultsTable") {
      headEl.innerHTML = "";
      return;
    }
    emptyEl.textContent = state.results.length
      ? "لا توجد نتائج مطابقة للفلاتر الحالية؛ امسح الفلاتر لعرضها مجدداً."
      : "ابدأ فحص عشان تشوف النتائج هنا.";
  } else {
    emptyEl.style.display = "none";
    emptyEl.textContent = "ابدأ فحص عشان تشوف النتائج هنا.";
  }
  const validKeys = new Set(columns.map(([key]) => key));
  const savedOrder = Array.isArray(state.columnOrders[tableId]) ? state.columnOrders[tableId] : [];
  const storedOrder = savedOrder.filter(key => validKeys.has(key));
  const orderMap = new Map(storedOrder.map((key, index) => [key, index]));
  const orderedColumns = [...columns].sort((a, b) =>
    (orderMap.get(a[0]) ?? Number.MAX_SAFE_INTEGER) - (orderMap.get(b[0]) ?? Number.MAX_SAFE_INTEGER));
  headEl.innerHTML = orderedColumns.map(([key, label, type]) => {
    const filterRows = tableId === "resultsTable" ? state.results : rows;
    const filter = tableId === "resultsTable" ? renderColumnFilter(key, label, type, filterRows) : "";
    return `<th data-key="${escapeHtml(key)}" draggable="true" title="اسحب علامة ⠿ لتغيير مكان العمود"><div class="table-heading-label"><span class="column-drag-handle" aria-hidden="true">⠿</span><button type="button" class="column-sort" data-sort-key="${escapeHtml(key)}">${escapeHtml(label)}</button></div>${filter}</th>`;
  }).join("");
  bodyEl.innerHTML = rows.map(row => `
    <tr data-ticker="${escapeHtml(row["الرمز"])}">
      ${orderedColumns.map(([key, , type]) => `<td>${formatCell(row[key], type)}</td>`).join("")}
    </tr>
  `).join("");

  // مستمع واحد للجدول بدلاً من مستمع لكل صف في كل إعادة رسم.
  bodyEl.onclick = onRowClick ? event => {
    const tr = event.target.closest("tr[data-ticker]");
    if (!tr || !bodyEl.contains(tr)) return;
    onRowClick(rows.find(row => row["الرمز"] === tr.dataset.ticker));
  } : null;

  let draggedColumn = null;
  headEl.querySelectorAll("th").forEach(th => {
    th.addEventListener("dragstart", event => {
      if (event.target.closest("input,select,button")) {
        event.preventDefault();
        return;
      }
      draggedColumn = th.dataset.key;
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", draggedColumn);
      th.classList.add("column-dragging");
    });
    th.addEventListener("dragend", () => {
      draggedColumn = null;
      th.classList.remove("column-dragging");
      headEl.querySelectorAll("th").forEach(cell => cell.classList.remove("column-drop-target"));
    });
    th.addEventListener("dragover", event => {
      if (!draggedColumn) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      th.classList.add("column-drop-target");
    });
    th.addEventListener("dragleave", () => th.classList.remove("column-drop-target"));
    th.addEventListener("drop", event => {
      if (!draggedColumn) return;
      event.preventDefault();
      th.classList.remove("column-drop-target");
      const sourceKey = event.dataTransfer.getData("text/plain") || draggedColumn;
      const keys = orderedColumns.map(column => column[0]);
      const from = keys.indexOf(sourceKey);
      const to = keys.indexOf(th.dataset.key);
      if (from < 0 || to < 0 || from === to) return;
      keys.splice(to, 0, keys.splice(from, 1)[0]);
      saveColumnOrder(tableId, keys);
      if (tableId === "resultsTable") applySearch();
      else renderTable(rows, columns, headEl, bodyEl, emptyEl, onRowClick);
    });
    th.querySelector(".column-sort")?.addEventListener("click", event => {
      event.stopPropagation();
      const key = th.dataset.key;
      const dir = (state.sortCol === key && state.sortDir === "desc") ? "asc" : "desc";
      state.sortCol = key;
      state.sortDir = dir;
      const sorted = [...rows].sort((a, b) => {
        const av = a[key], bv = b[key];
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        if (typeof av === "number") return dir === "desc" ? bv - av : av - bv;
        return dir === "desc" ? String(bv).localeCompare(String(av), "ar") : String(av).localeCompare(String(bv), "ar");
      });
      renderTable(sorted, columns, headEl, bodyEl, emptyEl, onRowClick);
    });
    th.querySelectorAll("input,select,button").forEach(control => {
      control.addEventListener("click", event => event.stopPropagation());
      control.addEventListener("dragstart", event => event.preventDefault());
    });
    th.querySelectorAll("input:not([data-filter-mode='multi']),select").forEach(control => {
      control.addEventListener(control.tagName === "SELECT" ? "change" : "input", scheduleSearch);
    });

    const multiFilter = th.querySelector("[data-multi-filter]");
    if (multiFilter) {
      const filterKey = multiFilter.dataset.multiFilter;
      const toggle = multiFilter.querySelector(".multi-filter-toggle");
      const setExpanded = open => toggle?.setAttribute("aria-expanded", String(open));
      toggle?.addEventListener("click", event => {
        event.stopPropagation();
        const willOpen = !multiFilter.classList.contains("open");
        document.querySelectorAll(".multi-filter.open").forEach(filter => {
          filter.classList.remove("open");
          filter.querySelector(".multi-filter-toggle")?.setAttribute("aria-expanded", "false");
        });
        multiFilter.classList.toggle("open", willOpen);
        setExpanded(willOpen);
      });
      multiFilter.querySelectorAll("input[data-filter-mode='multi']").forEach(checkbox => {
        checkbox.addEventListener("change", () => {
          state.columnFilters[filterKey] = [...multiFilter.querySelectorAll("input[data-filter-mode='multi']:checked")]
            .map(input => input.value);
          applySearch();
        });
      });
      multiFilter.querySelector(".multi-filter-clear")?.addEventListener("click", event => {
        event.stopPropagation();
        state.columnFilters[filterKey] = [];
        applySearch();
      });
    }
  });
}

function renderColumnFilter(key, label, type, rows) {
  if (key === "اسم الشركة" || key === "الرمز") {
    const text = state.columnFilters[key]?.text || "";
    return `<input class="column-filter" type="search" value="${escapeHtml(text)}" data-filter-key="${escapeHtml(key)}" data-filter-mode="text" aria-label="بحث ${escapeHtml(label)}" placeholder="بحث…">`;
  }
  if (["num", "pct", "forecast", "score"].includes(type)) {
    const metric = type === "forecast" ? "low_pct" : "";
    const values = state.columnFilters[key] || {};
    return `<div class="column-filter column-filter-range">
      <input type="number" step="any" value="${escapeHtml(values.min ?? "")}" data-filter-key="${escapeHtml(key)}" data-bound="min" ${metric ? `data-metric="${metric}"` : ""} aria-label="أقل ${escapeHtml(label)}" placeholder="من">
      <input type="number" step="any" value="${escapeHtml(values.max ?? "")}" data-filter-key="${escapeHtml(key)}" data-bound="max" ${type === "forecast" ? 'data-metric="high_pct"' : ""} aria-label="أعلى ${escapeHtml(label)}" placeholder="إلى">
    </div>`;
  }
  const values = [...new Set(rows.map(row => row[key]).filter(value => value !== null && value !== undefined && String(value).trim() !== ""))]
    .sort((a, b) => String(a).localeCompare(String(b), "ar"));
  if (!values.length) return "";
  const saved = state.columnFilters[key];
  const selectedValues = Array.isArray(saved) ? saved : saved ? [saved] : [];
  const selectionLabel = selectedValues.length ? `مختار: ${selectedValues.length}` : "الكل";
  return `<div class="multi-filter" data-multi-filter="${escapeHtml(key)}">
    <button type="button" class="multi-filter-toggle" aria-expanded="false" aria-label="فلترة ${escapeHtml(label)}">${selectionLabel}<span aria-hidden="true">⌄</span></button>
    <div class="multi-filter-menu" role="group" aria-label="اختيارات فلتر ${escapeHtml(label)}">
      <button type="button" class="multi-filter-clear">مسح الاختيار</button>
      ${values.map(value => `<label class="multi-filter-option"><input type="checkbox" value="${escapeHtml(value)}" data-filter-key="${escapeHtml(key)}" data-filter-mode="multi" ${selectedValues.includes(String(value)) ? "checked" : ""}><span>${escapeHtml(value)}</span></label>`).join("")}
    </div>
  </div>`;
}

function renderResultsTable(rows) {
  renderTable(rows, RESULT_COLUMNS,
    document.getElementById("resultsHead"), document.getElementById("resultsBody"),
    document.getElementById("resultsEmpty"), openStockDetail);
}

function renderGrowthTable(allResults) {
  const growthRows = allResults.filter(r => {
    const change = r["التغير %"];
    const mfi = r["MFI"];
    const vol = r["السيولة"];
    const cap = r["القيمة السوقية"];
    const sma50 = r["متوسط 50 يوم"];
    const sma200 = r["متوسط 200 يوم"];
    return change >= 1 && change <= 4
      && mfi !== null && mfi > 40
      && vol > 1.5
      && cap !== null && cap > 2000000000
      && sma50 !== null && sma200 !== null && sma50 > sma200;
  });
  renderTable(growthRows, GROWTH_COLUMNS,
    document.getElementById("growthHead"), document.getElementById("growthBody"),
    document.getElementById("growthEmpty"), openStockDetail);
}

function renderDroppedTable(rows) {
  const body = document.getElementById("droppedBody");
  const empty = document.getElementById("droppedEmpty");
  if (!rows || rows.length === 0) {
    body.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  body.innerHTML = rows.map(r => `
    <tr>
      <td>${escapeHtml(r["القطاع"] || "")}</td>
      <td>${escapeHtml(r["اسم الشركة"] || "")}</td>
      <td class="num">${escapeHtml(r["الرمز"] || "")}</td>
      <td>${escapeHtml(r["سبب الاستبعاد"] || "")}</td>
    </tr>
  `).join("");
}

function applySearch() {
  const q = document.getElementById("searchBox").value.trim();
  const activeFilter = document.activeElement;
  const activeFilterDetails = activeFilter?.matches?.("[data-filter-key]")
    ? {
      filterKey: activeFilter.dataset.filterKey,
      bound: activeFilter.dataset.bound,
      filterMode: activeFilter.dataset.filterMode,
      tagName: activeFilter.tagName,
      caret: activeFilter.type === "search" ? activeFilter.selectionStart : null,
    }
    : null;
  const controls = document.querySelectorAll("#resultsHead [data-filter-key]");
  controls.forEach(control => {
    const key = control.dataset.filterKey;
    if (document.activeElement === control) {
      if (control.dataset.filterMode === "text") {
        state.columnFilters[key] = { text: control.value };
      } else if (control.dataset.filterMode === "multi") {
        const filter = control.closest("[data-multi-filter]");
        state.columnFilters[key] = filter
          ? [...filter.querySelectorAll("input[data-filter-mode='multi']:checked")].map(input => input.value)
          : [];
      } else if (control.tagName === "SELECT") {
        state.columnFilters[key] = [...control.selectedOptions].map(option => option.value);
      } else {
        state.columnFilters[key] ||= {};
        state.columnFilters[key][control.dataset.bound] = control.value;
      }
    }
  });
  const filtered = state.results.filter(row => {
    const matchesSearch = !q || (row["اسم الشركة"] || "").includes(q)
      || (row["الرمز"] || "").toUpperCase().includes(q.toUpperCase());
    if (!matchesSearch) return false;

    return Object.entries(state.columnFilters).every(([key, filter]) => {
      const rawValue = row[key];
      if (Array.isArray(filter)) return filter.length === 0 || filter.includes(String(rawValue ?? ""));
      if (typeof filter === "string") return !filter || String(rawValue ?? "") === filter;
      if (filter && typeof filter.text === "string") {
        return !filter.text || String(rawValue ?? "").toLocaleLowerCase("ar").includes(filter.text.toLocaleLowerCase("ar"));
      }
      return Object.entries(filter || {}).every(([bound, boundValue]) => {
        if (boundValue === "") return true;
        const metric = RESULT_COLUMNS.find(column => column[0] === key)?.[2] === "forecast"
          ? (bound === "min" ? "low_pct" : "high_pct") : null;
        const value = metric && rawValue && typeof rawValue === "object" ? rawValue[metric] : rawValue;
        if (value === null || value === undefined || !Number.isFinite(Number(value))) return false;
        return bound === "min" ? Number(value) >= Number(boundValue) : Number(value) <= Number(boundValue);
      });
    });
  });
  renderResultsTable(filtered);
  if (activeFilterDetails) {
    if (activeFilterDetails.filterMode === "multi") {
      const multiFilter = [...document.querySelectorAll("#resultsHead [data-multi-filter]")]
        .find(filter => filter.dataset.multiFilter === activeFilterDetails.filterKey);
      if (multiFilter) {
        multiFilter.classList.add("open");
        multiFilter.querySelector(".multi-filter-toggle")?.setAttribute("aria-expanded", "true");
      }
    }
    const replacement = [...document.querySelectorAll("#resultsHead [data-filter-key]")].find(control =>
      control.dataset.filterKey === activeFilterDetails.filterKey
      && control.dataset.bound === activeFilterDetails.bound
      && control.dataset.filterMode === activeFilterDetails.filterMode
      && control.tagName === activeFilterDetails.tagName);
    if (replacement) {
      replacement.focus();
      if (replacement.type === "search" && typeof replacement.setSelectionRange === "function") {
        const caret = activeFilterDetails.caret;
        if (caret !== null) replacement.setSelectionRange(caret, caret);
      }
      if (replacement.type === "number" && replacement.value) {
        const end = replacement.value.length;
        replacement.setSelectionRange(end, end);
      }
    }
  }
}

function scheduleSearch() {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(applySearch, 180);
}

async function openStockDetail(row) {
  const overlay = document.getElementById("detailOverlay");
  const content = document.getElementById("detailContent");
  overlay.classList.add("open");
  content.innerHTML = `
    <h2 style="margin-top:0;">${escapeHtml(row["اسم الشركة"])} <span class="num" style="color:var(--text-secondary);">(${escapeHtml(row["الرمز"])})</span></h2>
    <button type="button" class="top-action favorite-detail-button" id="favoriteToggle">${state.favorites.has(row["الرمز"]) ? "★ إزالة من المفضلة" : "☆ إضافة إلى المفضلة"}</button>
    <section class="detail-signal-card">
      <div class="detail-score"><strong>${row["قوة الإشارة"] ?? "—"}</strong><span>قوة الإشارة</span></div>
      <div><strong>${escapeHtml(row["قرار السوينغ"] || "انتظر")}</strong><p>${escapeHtml(row["نوع السهم"] || "غير محدد")} · مخاطرة ${escapeHtml(row["مستوى المخاطرة"] || "غير محددة")}</p></div>
    </section>
    <div class="detail-tabs" role="tablist" aria-label="تفاصيل السهم">
      <button type="button" class="detail-tab active" data-detail-tab="overview">الملخص</button>
      <button type="button" class="detail-tab" data-detail-tab="strategy">الخطة</button>
      <button type="button" class="detail-tab" data-detail-tab="news">الأخبار</button>
    </div>
    <section class="detail-section active" data-detail-section="overview">
      <div class="panel"><strong>🧭 التصنيف الفني والمخاطر</strong><p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["سبب التصنيف"] || "لا يوجد تفسير متاح.")}</p></div>
      <div class="panel"><strong>☪️ حالة EGX33 Shariah</strong><p>${escapeHtml(row["حالة EGX33 Shariah"] || "غير متاح")}</p><p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["شرح حالة EGX33 Shariah"] || "تعرض عضوية المؤشر فقط وليست فتوى أو فحصاً شرعياً مستقلاً.")}</p></div>
    </section>
    <section class="detail-section" data-detail-section="strategy">
      <div class="panel"><strong>🎯 استراتيجية الدخول والخروج</strong><p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["استراتيجية الدخول والخروج"] || "—")}</p></div>
      <div class="panel"><strong>⚡ قرار السوينغ</strong><p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["شرح السوينغ"] || "—")}</p></div>
      <div class="panel"><strong>🏦 نصيحة المالك</strong><p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["شرح نصيحة المالك"] || "—")}</p></div>
    </section>
    <section class="detail-section" data-detail-section="news"><div class="panel" id="newsPanel"><span class="loading-spinner"></span> جاري جلب الأخبار والإعلانات…</div></section>
  `;

  content.querySelector("#favoriteToggle")?.addEventListener("click", () => toggleFavorite(row));

  content.querySelectorAll("[data-detail-tab]").forEach(button => {
    button.addEventListener("click", () => {
      const tab = button.dataset.detailTab;
      content.querySelectorAll("[data-detail-tab]").forEach(item => item.classList.toggle("active", item === button));
      content.querySelectorAll("[data-detail-section]").forEach(section => section.classList.toggle("active", section.dataset.detailSection === tab));
    });
  });

  startStockNewsAutoRefresh(row);
}

const STOCK_NEWS_AUTO_REFRESH_MS = 10 * 60 * 1000;

function closeStockDetail() {
  document.getElementById("detailOverlay").classList.remove("open");
  clearInterval(state.stockNewsTimer);
  state.stockNewsTimer = null;
  state.activeStockTicker = null;
}

async function refreshStockNews(row) {
  const ticker = row["الرمز"];
  if (!ticker || state.stockNewsRequestTicker === ticker) return;
  state.stockNewsRequestTicker = ticker;
  const panel = document.getElementById("newsPanel");
  if (state.activeStockTicker === ticker && panel) {
    panel.innerHTML = '<span class="loading-spinner"></span> جاري تحديث الأخبار والإعلانات…';
  }
  try {
    const resp = await fetch(`${API_BASE}/api/stock/${encodeURIComponent(ticker)}/news?company_name=${encodeURIComponent(row["اسم الشركة"])}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (state.activeStockTicker === ticker) renderNewsPanel(data);
  } catch {
    const activePanel = document.getElementById("newsPanel");
    if (state.activeStockTicker === ticker && activePanel) {
      activePanel.textContent = "تعذّر تحديث الأخبار الآن؛ ستتم إعادة المحاولة تلقائيًا.";
    }
  } finally {
    if (state.stockNewsRequestTicker === ticker) state.stockNewsRequestTicker = null;
  }
}

function startStockNewsAutoRefresh(row) {
  clearInterval(state.stockNewsTimer);
  state.activeStockTicker = row["الرمز"];
  refreshStockNews(row);
  state.stockNewsTimer = setInterval(() => {
    const isOpen = document.getElementById("detailOverlay").classList.contains("open");
    if (isOpen && document.visibilityState === "visible" && state.activeStockTicker === row["الرمز"]) {
      refreshStockNews(row);
    }
  }, STOCK_NEWS_AUTO_REFRESH_MS);
}

function renderNewsPanel(data) {
  const panel = document.getElementById("newsPanel");
  if (!panel) return;
  let html = "<strong>📰 الأخبار والإعلانات والبيانات الأساسية</strong>";
  const snapshot = data.mubasher || {};
  const snapshotUrl = safeExternalUrl(snapshot.url);
  if (snapshotUrl) {
    html += `<p><a href="${escapeHtml(snapshotUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);">🌐 صفحة السهم على مباشر</a></p>`;
  }
  const fundamentals = [
    ["السعر", snapshot.price], ["التغير %", snapshot.change_pct], ["إغلاق سابق", snapshot.prev_close],
    ["افتتاح", snapshot.open], ["أعلى", snapshot.high], ["أدنى", snapshot.low],
    ["حجم التداول", snapshot.volume], ["قيمة التداول", snapshot.turnover],
    ["القيمة السوقية", snapshot.market_cap], ["القيمة الدفترية", snapshot.book_value],
    ["مضاعف القيمة الدفترية", snapshot.pb_ratio], ["ربحية السهم", snapshot.eps],
    ["مضاعف الربحية", snapshot.pe_ratio], ["القيمة الاسمية", snapshot.par_value],
  ].filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "");
  if (fundamentals.length) {
    html += `<div class="stock-fundamentals">${fundamentals.map(([label, value]) =>
      `<div class="stock-fundamental"><span>${escapeHtml(label)}</span><strong dir="ltr">${escapeHtml(value)}</strong></div>`
    ).join("")}</div><small class="news-meta">البيانات الأساسية من مباشر؛ قد يتأخر التحديث بحسب المصدر.</small>`;
  } else {
    html += `<p class="news-meta">بيانات الأساسيات غير متاحة من المصدر الآن.</p>`;
  }

  if (data.news && data.news.length > 0) {
    html += `<h4>آخر الأخبار والإفصاحات (${data.news.length})</h4>`;
    html += data.news.map(n => {
      const isAnnouncement = n.item_type === "إعلان";
      const icon = isAnnouncement ? "📢" : "📰";
      let sentimentHtml = "";
      if (n.sentiment_pct) {
        const p = n.sentiment_pct;
        sentimentHtml = `<span class="num pct-up">${escapeHtml(p.positive)}%</span> إيجابي · <span class="num">${escapeHtml(p.neutral)}%</span> محايد · <span class="num pct-down">${escapeHtml(p.negative)}%</span> سلبي`;
      } else {
        sentimentHtml = escapeHtml(n.sentiment_label || "تحليل المشاعر غير متاح");
      }
      const title = escapeHtml(n.headline || "خبر بدون عنوان");
      const newsUrl = safeExternalUrl(n.link);
      const link = newsUrl ? `<a href="${escapeHtml(newsUrl)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title;

      const pdfUrl = safeExternalUrl(n.pdf_url);
      const pdfBadge = pdfUrl ? `<a href="${escapeHtml(pdfUrl)}" target="_blank" rel="noopener noreferrer" class="news-pdf-badge" style="display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:4px; background:rgba(239,68,68,0.15); color:#f87171; font-size:11px; text-decoration:none; margin-right:6px; border:1px solid rgba(239,68,68,0.3);" title="تحميل ملف الإفصاح الرسمي">📄 إفصاح PDF</a>` : "";

      let fundamentalHtml = "";
      if (n.fundamental_type || n.fundamental_impact) {
        fundamentalHtml = `<div class="news-fundamental" style="margin-top:5px; font-size:12px; color:var(--text-secondary); background:rgba(255,255,255,0.03); padding:5px 8px; border-radius:4px; border-right:3px solid var(--accent, #38bdf8);">` +
          `${n.fundamental_type ? `<strong style="color:var(--accent, #38bdf8);">🎯 [${escapeHtml(n.fundamental_type)}]</strong> ` : ""}` +
          `${escapeHtml(n.fundamental_impact || "")}` +
          `</div>`;
      }

      return `<div class="news-item"><div>${icon} ${sentimentHtml} ${pdfBadge}</div><div>${link}</div>${fundamentalHtml}<div class="news-meta">${escapeHtml([n.source, n.date].filter(Boolean).join(" · "))}</div></div>`;
    }).join("");
  } else {
    html += `<p style="color:var(--text-secondary);">${data.errors?.length ? "تعذّر الوصول لمصادر الأخبار حالياً." : "لا توجد أخبار حديثة مطابقة من المصادر المتاحة."}</p>`;
  }

  if (data.errors && data.errors.length > 0) {
    html += `<details style="margin-top:var(--space-3);"><summary style="cursor:pointer; color:var(--text-secondary);">⚠️ تفاصيل حالة المصادر</summary><pre style="white-space:pre-wrap; font-size:12px; color:var(--text-tertiary);">${escapeHtml(data.errors.join("\n"))}</pre></details>`;
  }
  panel.innerHTML = html;
}

async function loadMacroNews(force = false) {
  const container = document.getElementById("macroNewsList");
  container.innerHTML = '<span class="loading-spinner"></span> جاري الجلب…';
  const resp = await fetch(`${API_BASE}/api/macro/news${force ? "?force=true" : ""}`);
  const data = await resp.json();
  if (!data.items || data.items.length === 0) {
    container.innerHTML = `<p style="color:var(--text-secondary);">${escapeHtml(data.error || "مفيش أخبار حالياً")}</p>`;
    return;
  }
  container.innerHTML = data.items.map(n => {
    const url = safeExternalUrl(n.link);
    const title = escapeHtml(n.title || "خبر بدون عنوان");
    return `
    <div class="news-item">
      <div>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title}</div>
      <div class="news-meta">${escapeHtml([n.source, n.date].filter(Boolean).join(" · "))}</div>
    </div>`;
  }).join("");
}

async function loadFedAnalysis(force = false) {
  const container = document.getElementById("fedNewsList");
  container.innerHTML = '<span class="loading-spinner"></span> جاري الجلب والتحليل…';
  const resp = await fetch(`${API_BASE}/api/macro/fed-analysis${force ? "?force=true" : ""}`);
  const data = await resp.json();
  let html = "";
  if (data.news && data.news.length > 0) {
    html += data.news.map(n => {
      const url = safeExternalUrl(n.link);
      const title = escapeHtml(n.title || "خبر بدون عنوان");
      return `
      <div class="news-item">
        <div>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${title}</a>` : title}</div>
        <div class="news-meta">${escapeHtml(n.date || "")}</div>
      </div>`;
    }).join("");
    html += `<div class="panel" style="margin-top:var(--space-3);"><strong>🤖 تحليل الـ AI:</strong>
      <p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(data.analysis || "تعذّر توليد التحليل.")}</p></div>`;
  } else {
    html = `<p style="color:var(--text-secondary);">مفيش أخبار حالياً.</p>`;
  }
  container.innerHTML = html;
}

const MACRO_NEWS_AUTO_REFRESH_MS = 10 * 60 * 1000;

function isMacroTabActive() {
  return document.querySelector(".tab-btn.active")?.dataset.tab === "macro";
}

async function refreshMacroNews(force = false) {
  if (state.macroNewsRequestInFlight) return;
  state.macroNewsRequestInFlight = true;
  try {
    const [macroResult, fedResult] = await Promise.allSettled([loadMacroNews(force), loadFedAnalysis(force)]);
    if (macroResult.status === "rejected") {
      document.getElementById("macroNewsList").innerHTML = '<p style="color:var(--text-secondary);">تعذر تحديث الأخبار الآن؛ ستتم إعادة المحاولة تلقائيًا.</p>';
    }
    if (fedResult.status === "rejected") {
      document.getElementById("fedNewsList").innerHTML = '<p style="color:var(--text-secondary);">تعذر تحديث تحليل الفيدرالي الآن؛ ستتم إعادة المحاولة تلقائيًا.</p>';
    }
  } finally {
    state.macroNewsRequestInFlight = false;
  }
}

function startMacroNewsAutoRefresh() {
  clearInterval(state.macroNewsTimer);
  refreshMacroNews();
  state.macroNewsTimer = setInterval(() => {
    if (document.visibilityState === "visible" && isMacroTabActive()) refreshMacroNews();
  }, MACRO_NEWS_AUTO_REFRESH_MS);
}

function stopMacroNewsAutoRefresh() {
  clearInterval(state.macroNewsTimer);
  state.macroNewsTimer = null;
}

function switchTab(tabName) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tabName));
  document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
  document.getElementById(`tab-${tabName}`).style.display = "block";
  if (tabName === "favorites") renderFavorites();
  if (tabName === "macro") startMacroNewsAutoRefresh();
  else stopMacroNewsAutoRefresh();
}

async function exportExcel() {
  const selectedSectors = Array.from(document.querySelectorAll(".sector-checkbox:checked")).map(el => el.value);
  const payload = {
    sectors: selectedSectors,
    timeframe: document.getElementById("timeframeSelect").value,
    min_daily_turnover: parseFloat(document.getElementById("minTurnover").value) || 0,
    use_investing_primary: document.getElementById("useInvestingPrimary").checked,
  };
  const resp = await fetch(`${API_BASE}/api/scan/excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "AlphaBuf_Scan.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

function bindEvents() {
  document.addEventListener("click", event => {
    if (event.target.closest(".multi-filter")) return;
    document.querySelectorAll(".multi-filter.open").forEach(filter => {
      filter.classList.remove("open");
      filter.querySelector(".multi-filter-toggle")?.setAttribute("aria-expanded", "false");
    });
  });
  document.getElementById("authOpen").addEventListener("click", () => openOverlay("authOverlay"));
  document.getElementById("authClose").addEventListener("click", () => closeOverlay("authOverlay"));
  document.getElementById("adminClose").addEventListener("click", () => closeOverlay("adminOverlay"));
  document.getElementById("logoutBtn").addEventListener("click", logout);
  document.getElementById("adminOpen").addEventListener("click", openAdminDashboard);
  document.getElementById("adminBackupBtn").addEventListener("click", downloadAdminBackup);
  document.getElementById("authForm").addEventListener("submit", submitAuth);
  document.getElementById("guestBtn").addEventListener("click", continueAsGuest);
  document.querySelectorAll("[data-auth-mode]").forEach(button => button.addEventListener("click", () => setAuthMode(button.dataset.authMode)));
  document.getElementById("scanBtn").addEventListener("click", runScan);
  document.getElementById("exportBtn").addEventListener("click", exportExcel);
  document.getElementById("searchBox").addEventListener("input", scheduleSearch);
  document.getElementById("resetFiltersBtn").addEventListener("click", () => {
    state.columnFilters = {};
    document.getElementById("searchBox").value = "";
    renderResultsTable(state.results);
    applySearch();
  });
  document.getElementById("detailClose").addEventListener("click", closeStockDetail);
  document.getElementById("detailOverlay").addEventListener("click", (e) => {
    if (e.target.id === "detailOverlay") closeStockDetail();
  });
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  document.getElementById("macroNewsBtn").addEventListener("click", loadMacroNews);
  document.getElementById("fedNewsBtn").addEventListener("click", loadFedAnalysis);
  document.getElementById("manualNewsRetryBtn").addEventListener("click", async event => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "جاري إعادة المحاولة…";
    try {
      await refreshMacroNews(true);
    } finally {
      button.disabled = false;
      button.textContent = "↻ إعادة المحاولة اليدوية";
    }
  });
  document.getElementById("timeframeSelect").addEventListener("change", updateScanButtonState);
  document.getElementById("minTurnover").addEventListener("input", updateScanButtonState);
  document.getElementById("useInvestingPrimary").addEventListener("change", updateScanButtonState);
  document.getElementById("sectorList").addEventListener("change", updateScanButtonState);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) startLiveQuotesPolling();
    if (!document.hidden && isMacroTabActive()) refreshMacroNews();
    if (!document.hidden && state.activeStockTicker) {
      const row = state.results.find(item => item["الرمز"] === state.activeStockTicker);
      if (row) refreshStockNews(row);
    }
  });
}

init();
