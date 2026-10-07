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
  lastCache: null,
  lastScanConfig: null,
  categoryFilters: {},
  columnFilters: {},
  sectorHorizons: {},
  columnOrders: loadColumnOrders(),
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

const RESULT_COLUMNS = [
  ["اسم الشركة", "الشركة", "text"],
  ["الرمز", "الرمز", "text"],
  ["قرار السوينغ", "قرار السوينغ", "badge"],
  ["نصيحة المالك", "نصيحة المالك", "badge"],
  ["نوع السهم", "تصنيف فني", "text"],
  ["مستوى المخاطرة", "المخاطر", "text"],
  ["الفلتر الشرعي (أولي)", "فلتر شرعي أولي", "text"],
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
  await Promise.all([loadSectors(), loadTimeframes(), loadMacroPrices()]);
  bindEvents();
  await initializeLatestScan();
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
  state.results = data.results;
  state.dropped = data.dropped;
  state.totalStocks = data.total_stocks;
  state.lastCache = data.cache || null;
  state.lastScanConfig = data.scan_config || null;
  state.sectorHorizons = data.sector_horizons || {};
  renderStats(data);
  renderSectorPerformance(state.results);
  applySearch();
  renderGrowthTable(state.results);
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
  const matches = cachedConfig
    && JSON.stringify({ ...cachedConfig, sectors: [...(cachedConfig.sectors || [])].sort() }) === JSON.stringify(currentConfig);
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
  const currentIsCachedConfig = state.lastScanConfig
    && JSON.stringify({ ...state.lastScanConfig, sectors: [...(state.lastScanConfig.sectors || [])].sort() })
      === JSON.stringify(currentConfig);
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
  if (cache.status === "refreshing") {
    state.autoRefreshTimer = setTimeout(() => runScan({ automatic: true }), 10000);
    return;
  }
  const expiresAt = Date.parse(cache.expires_at || "");
  if (Number.isNaN(expiresAt)) return;
  const delay = Math.max(1000, expiresAt - Date.now());
  state.autoRefreshTimer = setTimeout(() => runScan({ automatic: true }), Math.min(delay, 2147480000));
}

function renderStats(data) {
  document.getElementById("statRow").style.display = "flex";
  document.getElementById("statTotal").textContent = data.total_stocks;
  document.getElementById("statMatched").textContent = data.results.length;
  document.getElementById("statExcluded").textContent = data.dropped.length;
  const avgChange = data.results.length
    ? (data.results.reduce((s, r) => s + (r["التغير %"] || 0), 0) / data.results.length).toFixed(2)
    : "0.00";
  document.getElementById("statAvgChange").textContent = avgChange + "%";
}

function renderSectorPerformance(rows) {
  const panel = document.getElementById("sectorPerformancePanel");
  const body = document.getElementById("sectorPerformanceBody");
  const count = document.getElementById("sectorPerformanceCount");
  if (!rows || rows.length === 0) {
    panel.style.display = "none";
    body.replaceChildren();
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

  body.innerHTML = summaries.map(({ sector, stocks, ranked, average }) => {
    const leader = ranked[0];
    const avgClass = average > 0 ? "pct-up" : average < 0 ? "pct-down" : "";
    const leaderChange = leader ? Number(leader["التغير %"]) : null;
    const leaderClass = leaderChange > 0 ? "pct-up" : leaderChange < 0 ? "pct-down" : "";
    return `
      <tr>
        <td>${escapeHtml(sector)}</td>
        <td class="num">${stocks.length}</td>
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
  const overallDelta = latest.average_change != null && previous?.average_change != null
    ? latest.average_change - previous.average_change : null;
  overallBody.innerHTML = [...history].reverse().slice(0, 10).map((item, index, rows) => {
    const older = rows[index + 1];
    const delta = item.average_change != null && older?.average_change != null
      ? item.average_change - older.average_change : null;
    return `<tr><td>${escapeHtml(new Date(item.captured_at).toLocaleString("ar-EG"))}</td>
      <td class="num">${item.matched_count} / ${item.total_stocks}</td>
      <td>${formatPercent(item.average_change)}</td><td>${formatDelta(delta)}</td></tr>`;
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
      if (!item || item.current_return == null) return "<td>غير متاح — يلزم تاريخ شموع أطول</td>";
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
  if (overallDelta !== null && history.length > 1) {
    description.dataset.latestDelta = overallDelta.toFixed(2);
  }
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

  if (onRowClick) {
    bodyEl.querySelectorAll("tr").forEach(tr => {
      tr.addEventListener("click", () => {
        const ticker = tr.dataset.ticker;
        const row = rows.find(r => r["الرمز"] === ticker);
        onRowClick(row);
      });
    });
  }

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
    th.querySelectorAll("input,select").forEach(control => {
      control.addEventListener("click", event => event.stopPropagation());
      control.addEventListener("dragstart", event => event.preventDefault());
      control.addEventListener(control.tagName === "SELECT" ? "change" : "input", applySearch);
    });
  });
}

function renderColumnFilter(key, label, type, rows) {
  if (key === "اسم الشركة" || key === "الرمز") {
    const text = state.columnFilters[key]?.text || "";
    return `<input class="column-filter" type="search" value="${escapeHtml(text)}" data-filter-key="${escapeHtml(key)}" data-filter-mode="text" aria-label="بحث ${escapeHtml(label)}" placeholder="بحث…">`;
  }
  if (["num", "pct", "forecast"].includes(type)) {
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
  const selectedValue = state.columnFilters[key] || "";
  return `<select class="column-filter" data-filter-key="${escapeHtml(key)}" aria-label="فلترة ${escapeHtml(label)}">
    <option value="">الكل</option>${values.map(value => `<option value="${escapeHtml(value)}" ${String(value) === selectedValue ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}
  </select>`;
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
      <td>${r["القطاع"] || ""}</td>
      <td>${r["اسم الشركة"] || ""}</td>
      <td class="num">${r["الرمز"] || ""}</td>
      <td>${r["سبب الاستبعاد"] || ""}</td>
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
      } else if (control.tagName === "SELECT") state.columnFilters[key] = control.value;
      else {
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

async function openStockDetail(row) {
  const overlay = document.getElementById("detailOverlay");
  const content = document.getElementById("detailContent");
  overlay.classList.add("open");
  content.innerHTML = `
    <h2 style="margin-top:0;">${escapeHtml(row["اسم الشركة"])} <span class="num" style="color:var(--text-secondary);">(${escapeHtml(row["الرمز"])})</span></h2>
    <div class="panel">
      <strong>🧭 التصنيف الفني والمخاطر</strong>
      <p>${escapeHtml(row["نوع السهم"] || "غير محدد")} · مستوى المخاطرة: ${escapeHtml(row["مستوى المخاطرة"] || "غير محدد")}</p>
      <p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["سبب التصنيف"] || "لا يوجد تفسير متاح.")}</p>
    </div>
    <div class="panel">
      <strong>☪️ الفلتر الشرعي الأولي — ليس اعتمادًا أو فتوى</strong>
      <p>${escapeHtml(row["الفلتر الشرعي (أولي)"] || "غير محسوم")}</p>
      <p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["شرح الفلتر الشرعي"] || "يستلزم فحصًا ماليًا ومراجعة مختصة.")}</p>
    </div>
    <div class="panel">
      <strong>🎯 استراتيجية الدخول والخروج</strong>
      <p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["استراتيجية الدخول والخروج"] || "—")}</p>
    </div>
    <div class="panel">
      <strong>⚡ قرار السوينغ</strong>
      <p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["شرح السوينغ"] || "—")}</p>
    </div>
    <div class="panel">
      <strong>🏦 نصيحة المالك</strong>
      <p class="mixed-direction-text" dir="rtl">${formatMixedDirectionText(row["شرح نصيحة المالك"] || "—")}</p>
    </div>
    <div class="panel" id="newsPanel">
      <span class="loading-spinner"></span> جاري جلب الأخبار والإعلانات…
    </div>
  `;

  try {
    const resp = await fetch(`${API_BASE}/api/stock/${encodeURIComponent(row["الرمز"])}/news?company_name=${encodeURIComponent(row["اسم الشركة"])}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    renderNewsPanel(data);
  } catch (e) {
    const panel = document.getElementById("newsPanel");
    if (panel) panel.textContent = "تعذّر جلب الأخبار حالياً؛ جرّب فتح التفاصيل مرة أخرى.";
  }
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

async function loadMacroNews() {
  const container = document.getElementById("macroNewsList");
  container.innerHTML = '<span class="loading-spinner"></span> جاري الجلب…';
  const resp = await fetch(`${API_BASE}/api/macro/news`);
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

async function loadFedAnalysis() {
  const container = document.getElementById("fedNewsList");
  container.innerHTML = '<span class="loading-spinner"></span> جاري الجلب والتحليل…';
  const resp = await fetch(`${API_BASE}/api/macro/fed-analysis`);
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

function switchTab(tabName) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tabName));
  document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
  document.getElementById(`tab-${tabName}`).style.display = "block";
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
  document.getElementById("scanBtn").addEventListener("click", runScan);
  document.getElementById("exportBtn").addEventListener("click", exportExcel);
  document.getElementById("searchBox").addEventListener("input", applySearch);
  document.getElementById("resetFiltersBtn").addEventListener("click", () => {
    state.columnFilters = {};
    document.getElementById("searchBox").value = "";
    renderResultsTable(state.results);
    applySearch();
  });
  document.getElementById("detailClose").addEventListener("click", () => {
    document.getElementById("detailOverlay").classList.remove("open");
  });
  document.getElementById("detailOverlay").addEventListener("click", (e) => {
    if (e.target.id === "detailOverlay") e.target.classList.remove("open");
  });
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
  document.getElementById("macroNewsBtn").addEventListener("click", loadMacroNews);
  document.getElementById("fedNewsBtn").addEventListener("click", loadFedAnalysis);
  document.getElementById("timeframeSelect").addEventListener("change", updateScanButtonState);
  document.getElementById("minTurnover").addEventListener("input", updateScanButtonState);
  document.getElementById("useInvestingPrimary").addEventListener("change", updateScanButtonState);
  document.getElementById("sectorList").addEventListener("change", updateScanButtonState);
}

init();
