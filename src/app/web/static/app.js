const stateBadgeMap = {
  live: "正常",
  degraded: "降级",
  sample: "样例",
  unavailable: "不可用",
  unknown: "未知",
  compatible: "兼容",
  loading: "加载中...",
};

const confidenceMap = { high: "高", medium: "中", low: "低" };
const signalMap = {
  breakout: "突破",
  constructive: "偏强",
  neutral: "中性",
  pressured: "承压",
  unavailable: "不可用",
};
const trendMap = { up: "上行", down: "下行", flat: "持平", unavailable: "不可用" };
const macroFrequencyMap = { daily: "日度", monthly: "月度", quarterly: "季度", yearly: "年度", unavailable: "未知" };
const NEWS_MODE_LABELS = { hybrid: "Hybrid", api: "API", upstream: "Upstream" };
const NEWS_MODE_OPTIONS = [
  { value: "hybrid", label: "Hybrid" },
  { value: "api", label: "API" },
  { value: "upstream", label: "Upstream" },
];
const MARKET_CHART_RANGE_OPTIONS = [
  { key: "7d", label: "1周", days: 7, minCoverageDays: 4 },
  { key: "30d", label: "1月", days: 30, minCoverageDays: 20 },
  { key: "90d", label: "3月", days: 90, minCoverageDays: 75 },
  { key: "180d", label: "6月", days: 180, minCoverageDays: 150 },
];
const MACRO_CHART_RANGE_OPTIONS = [
  { key: "1y", label: "近1年", days: 366, minCoverageDays: 180, minPoints: 4 },
  { key: "2y", label: "近2年", days: 731, minCoverageDays: 360, minPoints: 6 },
  { key: "5y", label: "近5年", days: 1826, minCoverageDays: 720, minPoints: 10 },
  { key: "all", label: "全部", days: null, minCoverageDays: 0, minPoints: 2 },
];

const MODULE_CONFIGS = [
  {
    id: "news",
    label: "新闻情报",
    description: "科技、财经、政策新闻",
    loadingMessage: "新闻频道正在后台加载...",
  },
  {
    id: "macro",
    label: "宏观指标",
    description: "宏观数据",
    loadingMessage: "宏观指标正在后台加载...",
  },
  {
    id: "market",
    label: "市场模型",
    description: "技术指标",
    loadingMessage: "市场模型正在后台加载...",
  },
  {
    id: "events",
    label: "事件展望",
    description: "未来展望",
    loadingMessage: "事件展望正在后台加载...",
  },
  {
    id: "push",
    label: "推送中心",
    description: "邮件配置、日报预览与定时任务",
    loadingMessage: "推送中心正在加载...",
  },
  {
    id: "status",
    label: "数据状态",
    description: "状态监控",
    loadingMessage: "数据状态正在后台加载...",
  },
];

const viewState = {
  modules: MODULE_CONFIGS.map((module) => ({
    ...module,
    note: "等待加载",
    status: "loading",
    details: [],
    loading: true,
    loaded: false,
    error: "",
  })),
  activeModuleId: "news",
  activeDetailByModule: {},
  activeMarketChartRangeByDetail: {},
  activeMacroChartRangeBySection: {},
  pendingRequestByModule: {},
  refreshTimerByModule: {},
  generatedAt: "",
  coverageNote: "",
};

let legacyDashboardPromise = null;
const marketChartInstances = new Map();

function getCurrentTheme() {
  const theme = document.documentElement.getAttribute("data-theme");
  return theme === "light" ? "light" : "dark";
}

function persistTheme(theme) {
  try {
    window.localStorage.setItem("dashboard-theme", theme);
  } catch (error) {}
}

function renderThemeToggle() {
  const button = document.getElementById("themeToggle");
  if (!button) {
    return;
  }
  const theme = getCurrentTheme();
  const nextLabel = theme === "light" ? "切换到暗色模式" : "切换到浅色模式";
  button.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
  button.setAttribute("aria-label", nextLabel);
  button.setAttribute("title", nextLabel);
}

function applyTheme(theme, { persist = true } = {}) {
  document.documentElement.setAttribute("data-theme", theme === "light" ? "light" : "dark");
  if (persist) {
    persistTheme(theme === "light" ? "light" : "dark");
  }
  renderThemeToggle();
  const module = currentModule();
  const detail = currentDetail(module);
  if (module?.id === "macro") {
    renderMacroOverviewCharts(module);
  } else if (detail?.kind === "market") {
    renderMarketTrendChart(detail.section, getActiveMarketChartRange(detail.id, detail.section));
  }
}

function initThemeToggle() {
  const button = document.getElementById("themeToggle");
  if (!button) {
    return;
  }
  renderThemeToggle();
  button.addEventListener("click", () => {
    applyTheme(getCurrentTheme() === "light" ? "dark" : "light");
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function normalizeNewsUrl(value) {
  const text = String(value ?? "").trim();
  return text.startsWith("http://") || text.startsWith("https://") ? text : "";
}

function normalizeSummaryText(value, maxChars = 100) {
  const compact = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!compact) {
    return "";
  }
  return Array.from(compact).slice(0, maxChars).join("");
}

function loadingSpinner(label = "加载中...", inline = false) {
  return `<span class="loading-spinner ${inline ? "loading-spinner-inline" : ""}" aria-hidden="true"></span><span>${escapeHtml(label)}</span>`;
}

function statusBadge(status) {
  if (status === "loading") {
    return `<span class="badge loading">${loadingSpinner(stateBadgeMap.loading, true)}</span>`;
  }
  return `<span class="badge ${escapeHtml(status)}">${escapeHtml(stateBadgeMap[status] || status)}</span>`;
}

function detailItem(label, value) {
  return `<div class="detail-item"><span class="detail-label">${escapeHtml(label)}</span><span class="detail-value">${escapeHtml(value)}</span></div>`;
}

function getRequestedNewsMode() {
  const params = new URLSearchParams(window.location.search);
  const value = params.get("news_mode") || "hybrid";
  return NEWS_MODE_LABELS[value] ? value : "hybrid";
}

function setRequestedNewsMode(mode) {
  const params = new URLSearchParams(window.location.search);
  if (mode === "hybrid") {
    params.delete("news_mode");
  } else {
    params.set("news_mode", mode);
  }
  const query = params.toString();
  legacyDashboardPromise = null;
  window.history.replaceState({}, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
}

function buildModuleApiUrl(moduleId, { forceRefresh = false } = {}) {
  const params = new URLSearchParams();
  if (moduleId === "news" || moduleId === "status") {
    const newsMode = getRequestedNewsMode();
    if (newsMode !== "hybrid") {
      params.set("news_mode", newsMode);
    }
  }
  if (forceRefresh) {
    params.set("refresh", "1");
  }
  const query = params.toString();
  return `/api/frontend/modules/${moduleId}${query ? `?${query}` : ""}`;
}

function buildLegacyApiUrl({ forceRefresh = false } = {}) {
  const params = new URLSearchParams();
  const newsMode = getRequestedNewsMode();
  if (newsMode !== "hybrid") {
    params.set("news_mode", newsMode);
  }
  if (forceRefresh) {
    params.set("refresh", "1");
  }
  const query = params.toString();
  return `/api/frontend/dashboard${query ? `?${query}` : ""}`;
}

function parseHash() {
  const raw = window.location.hash.replace(/^#/, "").trim();
  if (!raw) {
    return { moduleId: "news", detailId: "" };
  }
  const [moduleId, detailId = ""] = raw.split("/");
  return { moduleId, detailId };
}

function groupStatus(items) {
  if (!items?.length) {
    return "compatible";
  }
  const statuses = items.map((item) => item.status);
  if (statuses.includes("degraded")) {
    return "degraded";
  }
  if (statuses.includes("live")) {
    return "live";
  }
  if (statuses.includes("sample")) {
    return "sample";
  }
  return statuses[0] || "compatible";
}

function modulePayloadFromLegacy(payload, moduleId) {
  if (moduleId === "macro") {
    const sections = payload.macro_sections || [];
    return {
      generated_at: payload.generated_at,
      module: {
        id: "macro",
        label: "瀹忚鎸囨爣",
        note: `${sections.length} 缁勫姣斿浘`,
        description: "瀹樻柟瀹忚鍘嗗彶搴忓垪涓庡樊鍊兼瘮杈?",
        status: groupStatus(sections),
        details: sections.map((section) => ({
          id: section.key,
          label: section.title,
          kind: "macro",
          note: section.summary,
          section,
        })),
      },
    };
  }

  if (moduleId === "news") {
    const sections = payload.news_sections || [];
    return {
      generated_at: payload.generated_at,
      news_mode: payload.news_mode,
      news_mode_options: payload.news_mode_options || NEWS_MODE_OPTIONS,
      upstream_service_status: payload.upstream_service_status,
      module: {
        id: "news",
        label: "新闻情报",
        note: `${sections.length} 个频道`,
        description: "科技、财经、政策新闻",
        status: groupStatus(sections),
        details: sections.map((section) => ({
          id: section.key,
          label: section.title,
          kind: "news",
          note: `${section.item_count || 0} 条`,
          section,
        })),
      },
    };
  }

  if (moduleId === "market") {
    const sections = payload.market_sections || [];
    return {
      generated_at: payload.generated_at,
      module: {
        id: "market",
        label: "市场模型",
        note: `${sections.length} 个模型`,
        description: "技术指标",
        status: groupStatus(sections),
        details: sections.map((section) => ({
          id: section.key,
          label: section.label,
          kind: "market",
          note: signalMap[section.signal] || section.signal,
          section,
        })),
      },
    };
  }

  if (moduleId === "events") {
    const sections = payload.event_sections || [];
    return {
      generated_at: payload.generated_at,
      module: {
        id: "events",
        label: "事件展望",
        note: `${sections.length} 个窗口`,
        description: "未来展望",
        status: groupStatus(sections),
        details: sections.map((section) => ({
          id: section.key,
          label: section.title,
          kind: "events",
          note: `${(section.items || []).length} 条`,
          section,
        })),
      },
    };
  }

  if (moduleId === "push") {
    return {
      generated_at: payload.generated_at,
      module: {
        id: "push",
        label: "推送中心",
        note: "需要前端模块接口",
        description: "请使用 /api/frontend/modules/push 获取完整推送配置。",
        status: "compatible",
        details: [
          {
            id: "workspace",
            label: "推送配置",
            kind: "push",
            note: "frontend-api",
            section: {
              channel_type_options: [],
              source_module_options: [],
              style_options: [],
              config: {},
              preview: {
                ok: false,
                subject: "推送预览不可用",
                html_body: "",
                text_body: "",
              },
            },
          },
        ],
      },
    };
  }

  const sections = payload.data_status || [];
  return {
    generated_at: payload.generated_at,
    coverage_note: payload.coverage_note,
    module: {
      id: "status",
      label: "数据状态",
      note: `${sections.length} 个模块`,
      description: "状态监控",
      status: groupStatus(sections),
      details: sections.map((section) => ({
        id: section.key,
        label: section.label,
        kind: "status",
        note: stateBadgeMap[section.status] || section.status,
        section,
      })),
    },
  };
}

async function fetchLegacyDashboard({ forceRefresh = false } = {}) {
  if (forceRefresh) {
    legacyDashboardPromise = null;
  }
  if (!legacyDashboardPromise) {
    legacyDashboardPromise = fetch(buildLegacyApiUrl({ forceRefresh }), {
      headers: { Accept: "application/json" },
    }).then(async (response) => {
      if (!response.ok) {
        throw new Error(`legacy HTTP ${response.status}`);
      }
      return response.json();
    }).catch((error) => {
      legacyDashboardPromise = null;
      throw error;
    });
  }
  return legacyDashboardPromise;
}

function currentModule() {
  return viewState.modules.find((module) => module.id === viewState.activeModuleId) || viewState.modules[0];
}

function currentDetail(module) {
  if (!module?.details?.length) {
    return null;
  }
  const detailId = viewState.activeDetailByModule[module.id] || module.details[0]?.id;
  return module.details.find((detail) => detail.id === detailId) || module.details[0];
}

function parseTradeDate(value) {
  const text = String(value ?? "").trim();
  if (!text) {
    return null;
  }
  const parsed = new Date(`${text}T00:00:00Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getMarketRangeOption(rangeKey) {
  return MARKET_CHART_RANGE_OPTIONS.find((option) => option.key === rangeKey) || MARKET_CHART_RANGE_OPTIONS[2];
}

function filterMarketChartPointsByRange(points, rangeKey) {
  const option = getMarketRangeOption(rangeKey);
  const datedPoints = (Array.isArray(points) ? points : []).filter((point) => parseTradeDate(point.trade_date));
  if (!datedPoints.length) {
    return [];
  }
  const latestDate = parseTradeDate(datedPoints[datedPoints.length - 1].trade_date);
  if (!latestDate) {
    return datedPoints;
  }
  const startDate = new Date(latestDate.getTime() - ((option.days - 1) * 24 * 60 * 60 * 1000));
  const filtered = datedPoints.filter((point) => {
    const tradeDate = parseTradeDate(point.trade_date);
    return tradeDate && tradeDate >= startDate;
  });
  return filtered.length >= 2 ? filtered : datedPoints;
}

function getAvailableMarketChartRanges(points) {
  const datedPoints = (Array.isArray(points) ? points : []).filter((point) => parseTradeDate(point.trade_date));
  if (!datedPoints.length) {
    return MARKET_CHART_RANGE_OPTIONS.map((option) => ({ ...option, available: false }));
  }
  const firstDate = parseTradeDate(datedPoints[0].trade_date);
  const lastDate = parseTradeDate(datedPoints[datedPoints.length - 1].trade_date);
  const coverageDays = firstDate && lastDate ? Math.max(0, Math.round((lastDate - firstDate) / (24 * 60 * 60 * 1000))) : 0;
  return MARKET_CHART_RANGE_OPTIONS.map((option) => ({
    ...option,
    available: coverageDays >= option.minCoverageDays && filterMarketChartPointsByRange(datedPoints, option.key).length >= 2,
  }));
}

function getActiveMarketChartRange(detailId, section) {
  const points = Array.isArray(section?.chart_points) ? section.chart_points : [];
  const rangeOptions = getAvailableMarketChartRanges(points);
  const saved = viewState.activeMarketChartRangeByDetail[detailId];
  if (saved && rangeOptions.some((option) => option.key === saved && option.available)) {
    return saved;
  }
  const preferred = ["90d", "30d", "7d", "180d"];
  const fallback = preferred.find((key) => rangeOptions.some((option) => option.key === key && option.available))
    || rangeOptions.find((option) => option.available)?.key
    || "30d";
  viewState.activeMarketChartRangeByDetail[detailId] = fallback;
  return fallback;
}

function renderMarketChartRangeSwitch(detailId, section) {
  const points = Array.isArray(section?.chart_points) ? section.chart_points : [];
  const rangeOptions = getAvailableMarketChartRanges(points);
  if (!rangeOptions.some((option) => option.available)) {
    return "";
  }
  const activeRange = getActiveMarketChartRange(detailId, section);
  return `
    <div class="chart-range-switch" role="group" aria-label="历史范围切换">
      ${rangeOptions
        .map((option) => `
          <button
            type="button"
            class="chart-range-button ${option.key === activeRange ? "active" : ""}"
            data-market-range="${escapeHtml(option.key)}"
            ${option.available ? "" : "disabled"}
            title="${escapeHtml(option.available ? `切换到${option.label}` : `${option.label}数据不足，暂不可切换`)}"
          >${escapeHtml(option.label)}</button>
        `)
        .join("")}
    </div>
  `;
}

function getMacroRangeOption(rangeKey) {
  return MACRO_CHART_RANGE_OPTIONS.find((option) => option.key === rangeKey) || MACRO_CHART_RANGE_OPTIONS[1];
}

function filterMacroSeriesByRange(points, rangeKey, { fallbackToAll = true } = {}) {
  const option = getMacroRangeOption(rangeKey);
  const datedPoints = (Array.isArray(points) ? points : []).filter((point) => parseTradeDate(point.period_end));
  if (!datedPoints.length || rangeKey === "all" || !option.days) {
    return datedPoints;
  }
  const lastDate = parseTradeDate(datedPoints[datedPoints.length - 1].period_end);
  if (!lastDate) {
    return datedPoints;
  }
  const startDate = new Date(lastDate.getTime() - option.days * 24 * 60 * 60 * 1000);
  const filtered = datedPoints.filter((point) => {
    const periodDate = parseTradeDate(point.period_end);
    return periodDate && periodDate >= startDate;
  });
  return fallbackToAll && filtered.length < 2 ? datedPoints : filtered;
}

function collectMacroLabels(primaryPoints, secondaryPoints) {
  const labels = [];
  const seen = new Set();
  [...primaryPoints, ...secondaryPoints].forEach((point) => {
    const label = point.period_label || point.period_end;
    if (label && !seen.has(label)) {
      seen.add(label);
      labels.push(label);
    }
  });
  return labels;
}

function buildMacroCoverageLabel(primaryPoints, secondaryPoints) {
  const datedPoints = [...primaryPoints, ...secondaryPoints]
    .filter((point) => parseTradeDate(point.period_end))
    .sort((left, right) => left.period_end.localeCompare(right.period_end));
  if (!datedPoints.length) {
    return "暂无历史区间";
  }
  const first = datedPoints[0];
  const last = datedPoints[datedPoints.length - 1];
  return `${first.period_label || first.period_end} - ${last.period_label || last.period_end}`;
}

function getAvailableMacroChartRanges(section) {
  const primaryPoints = Array.isArray(section?.primary?.points) ? section.primary.points : [];
  const secondaryPoints = Array.isArray(section?.secondary?.points) ? section.secondary.points : [];
  const datedPoints = [...primaryPoints, ...secondaryPoints]
    .filter((point) => parseTradeDate(point.period_end))
    .sort((left, right) => left.period_end.localeCompare(right.period_end));
  if (!datedPoints.length) {
    return MACRO_CHART_RANGE_OPTIONS.map((option) => ({ ...option, available: false }));
  }
  const firstDate = parseTradeDate(datedPoints[0].period_end);
  const lastDate = parseTradeDate(datedPoints[datedPoints.length - 1].period_end);
  const coverageDays = firstDate && lastDate ? Math.max(0, Math.round((lastDate - firstDate) / (24 * 60 * 60 * 1000))) : 0;
  return MACRO_CHART_RANGE_OPTIONS.map((option) => {
    if (option.key === "all") {
      return { ...option, available: collectMacroLabels(primaryPoints, secondaryPoints).length >= option.minPoints };
    }
    const filteredPrimary = filterMacroSeriesByRange(primaryPoints, option.key, { fallbackToAll: false });
    const filteredSecondary = filterMacroSeriesByRange(secondaryPoints, option.key, { fallbackToAll: false });
    return {
      ...option,
      available:
        coverageDays >= option.minCoverageDays
        && collectMacroLabels(filteredPrimary, filteredSecondary).length >= option.minPoints,
    };
  });
}

function getActiveMacroChartRange(sectionKey, section) {
  const rangeOptions = getAvailableMacroChartRanges(section);
  const saved = viewState.activeMacroChartRangeBySection[sectionKey];
  if (saved && rangeOptions.some((option) => option.key === saved && option.available)) {
    return saved;
  }
  const preferred = ["2y", "1y", "5y", "all"];
  const fallback = preferred.find((key) => rangeOptions.some((option) => option.key === key && option.available))
    || rangeOptions.find((option) => option.available)?.key
    || "all";
  viewState.activeMacroChartRangeBySection[sectionKey] = fallback;
  return fallback;
}

function renderMacroChartRangeSwitch(sectionKey, section) {
  const rangeOptions = getAvailableMacroChartRanges(section);
  if (!rangeOptions.some((option) => option.available)) {
    return "";
  }
  const activeRange = getActiveMacroChartRange(sectionKey, section);
  return `
    <div class="chart-range-switch" role="group" aria-label="宏观历史范围切换">
      ${rangeOptions
        .map((option) => `
          <button
            type="button"
            class="chart-range-button ${option.key === activeRange ? "active" : ""}"
            data-macro-range="${escapeHtml(option.key)}"
            data-macro-section="${escapeHtml(sectionKey)}"
            ${option.available ? "" : "disabled"}
            title="${escapeHtml(option.available ? `切换到${option.label}` : `${option.label}数据不足，暂不可切换`)}"
          >${escapeHtml(option.label)}</button>
        `)
        .join("")}
    </div>
  `;
}

function formatMacroChartValue(value, unit = "") {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  const abs = Math.abs(value);
  const digits = unit === "ratio" ? 4 : abs >= 100 ? 0 : abs >= 10 ? 1 : 2;
  if (unit === "%" || unit === "pct") {
    return `${value.toFixed(Math.max(1, digits))}%`;
  }
  if (unit === "tn yuan") {
    return `${value.toFixed(2)}万亿`;
  }
  if (unit === "CNY/USD") {
    return `${value.toFixed(4)}`;
  }
  if (unit === "ratio") {
    return value.toFixed(4);
  }
  return `${value.toFixed(digits)}${unit ? ` ${unit}` : ""}`;
}

function updateGeneratedAt(value) {
  if (!value) {
    return;
  }
  viewState.generatedAt = value;
  document.getElementById("generatedAt").textContent = `更新时间: ${value}`;
}

function updateCoverageNote(value) {
  const note = document.getElementById("coverageNote");
  if (!note) {
    return;
  }
  viewState.coverageNote = value || "";
  note.textContent = value || "";
  note.hidden = !value;
}

function renderModeSwitch(meta = {}) {
  const root = document.getElementById("newsModeSwitch");
  const mode = meta.news_mode || getRequestedNewsMode();
  const options = meta.news_mode_options || NEWS_MODE_OPTIONS;
  const upstreamStatus = meta.upstream_service_status || {
    status: "loading",
    detail: "新闻模式状态加载中...",
  };
  document.getElementById("newsModeTag").textContent = NEWS_MODE_LABELS[mode] || mode;

  root.innerHTML = `
    <div class="mode-switch-stack">
      <div class="mode-switch-group">
        ${options
          .map(
            (option) =>
              `<button type="button" class="mode-switch-button ${option.value === mode ? "active" : ""}" data-news-mode="${escapeHtml(option.value)}">${escapeHtml(option.label)}</button>`,
          )
          .join("")}
      </div>
      <div class="mode-status mode-status-${escapeHtml(upstreamStatus.status)}">
        <span class="mode-status-label">Upstream</span>
        <span class="mode-status-text">${upstreamStatus.status === "loading" ? loadingSpinner("加载中...", true) : escapeHtml(upstreamStatus.status)}</span>
        <span class="mode-status-detail">${escapeHtml(upstreamStatus.detail || "")}</span>
      </div>
    </div>
  `;

  root.querySelectorAll("[data-news-mode]").forEach((node) => {
    node.addEventListener("click", () => {
      const nextMode = node.getAttribute("data-news-mode");
      if (!nextMode || nextMode === mode) {
        return;
      }
      setRequestedNewsMode(nextMode);
      renderModeSwitch({
        news_mode: nextMode,
        news_mode_options: options,
        upstream_service_status: { status: "loading", detail: "正在切换新闻数据源..." },
      });
      loadModule("news", { resetContent: true });
      loadModule("status", { resetContent: true });
    });
  });
}

function renderTickerFromState() {
  const root = document.getElementById("marketTicker");
  const lines = [];
  const marketModule = viewState.modules.find((module) => module.id === "market");
  if (marketModule?.loaded && !marketModule.error) {
    for (const detail of marketModule.details.slice(0, 6)) {
      lines.push({
        name: detail.label,
        value: `${detail.section.close_value} / ${signalMap[detail.section.signal] || detail.section.signal}`,
      });
    }
  }

  if (!lines.length) {
    root.innerHTML = `<span class="ticker-empty ticker-loading">${loadingSpinner("摘要数据加载中...", true)}</span>`;
    return;
  }

  root.innerHTML = `<div class="ticker-track">${lines
    .map(
      (item) =>
        `<span class="ticker-item"><span class="name">${escapeHtml(item.name)}</span><span class="value">${escapeHtml(item.value)}</span></span>`,
    )
    .join("")}</div>`;
}

function renderHeadlineList(items, emptyText = "暂无内容") {
  if (!items?.length) {
    return `<ol class="headline-list"><li class="placeholder">${escapeHtml(emptyText)}</li></ol>`;
  }
  return `<ol class="headline-list">${items
    .map((item) => {
      const url = normalizeNewsUrl(item.url);
      const title = url
        ? `<a class="headline-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.rank)} ${escapeHtml(item.title)}</a>`
        : `<span class="headline-link disabled">${escapeHtml(item.rank)} ${escapeHtml(item.title)}</span>`;
      return `<li><p class="headline-title">${title}</p><p class="headline-meta">${escapeHtml(item.source)} | ${escapeHtml(item.published_at)} | ${escapeHtml(item.tag)}</p></li>`;
    })
    .join("")}</ol>`;
}

function buildLineChart(points) {
  const valid = points.filter((point) => typeof point.value === "number");
  if (!valid.length) {
    return `<div class="chart-empty">暂无可绘制数据</div>`;
  }
  const width = 640;
  const height = 190;
  const left = 44;
  const right = 18;
  const top = 16;
  const innerWidth = width - left - right;
  const innerHeight = height - top - 28;
  const values = valid.map((point) => point.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const pad = (max - min) * 0.15;
  min -= pad;
  max += pad;
  const toX = (index) => left + (innerWidth * index) / Math.max(valid.length - 1, 1);
  const toY = (value) => top + ((max - value) / (max - min)) * innerHeight;
  const path = valid.map((point, index) => `${index === 0 ? "M" : "L"} ${toX(index).toFixed(2)} ${toY(point.value).toFixed(2)}`).join(" ");
  const area = `${path} L ${toX(valid.length - 1).toFixed(2)} ${toY(min).toFixed(2)} L ${toX(0).toFixed(2)} ${toY(min).toFixed(2)} Z`;
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none"><path d="${area}" fill="rgba(47, 93, 98, 0.10)"></path><path d="${path}" fill="none" stroke="#2f5d62" stroke-width="2.4"></path></svg>`;
}

function disposeMarketCharts() {
  marketChartInstances.forEach((chart) => {
    try {
      chart.dispose();
    } catch (error) {}
  });
  marketChartInstances.clear();
}

function marketChartEmptyState(message) {
  return `<div class="chart-empty market-chart-empty">${escapeHtml(message)}</div>`;
}

function renderMarketTrendChart(section, rangeKey = "30d") {
  const root = document.getElementById("marketTrendChart");
  if (!root) {
    disposeMarketCharts();
    return;
  }
  const points = Array.isArray(section?.chart_points) ? section.chart_points : [];
  const filteredPoints = filterMarketChartPointsByRange(points, rangeKey);
  if (!filteredPoints.length) {
    disposeMarketCharts();
    root.innerHTML = marketChartEmptyState("暂无可绘制历史数据");
    return;
  }
  if (!window.echarts) {
    disposeMarketCharts();
    root.innerHTML = marketChartEmptyState("ECharts 未加载，无法绘制历史趋势图");
    return;
  }

  root.innerHTML = "";
  const computedStyle = window.getComputedStyle(document.documentElement);
  const ink = (computedStyle.getPropertyValue("--ink") || "#e7edf5").trim();
  const muted = (computedStyle.getPropertyValue("--muted") || "#91a0b1").trim();
  const line = (computedStyle.getPropertyValue("--line") || "rgba(140, 160, 180, 0.18)").trim();
  const accent = (computedStyle.getPropertyValue("--accent") || "#f6a313").trim();
  const accent2 = (computedStyle.getPropertyValue("--accent-2") || "#31b8c4").trim();
  const ok = (computedStyle.getPropertyValue("--ok") || "#37c48d").trim();
  const danger = (computedStyle.getPropertyValue("--danger") || "#ff5f72").trim();

  const chart = window.echarts.getInstanceByDom(root) || window.echarts.init(root);
  marketChartInstances.set("marketTrendChart", chart);

  chart.setOption(
    {
      animation: false,
      color: [accent, accent2, danger],
      grid: { left: 52, right: 54, top: 40, bottom: 42 },
      legend: {
        top: 8,
        textStyle: { color: muted, fontSize: 11 },
        data: ["Close", "M20", "Deviation"],
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: getCurrentTheme() === "light" ? "rgba(255,255,255,0.95)" : "rgba(10,13,17,0.96)",
        borderColor: line,
        textStyle: { color: ink },
        valueFormatter(value) {
          if (typeof value !== "number") {
            return value;
          }
          return Number.isInteger(value) ? `${value}` : value.toFixed(2);
        },
      },
      xAxis: {
        type: "category",
        data: filteredPoints.map((point) => point.trade_date),
        boundaryGap: false,
        axisLabel: { color: muted, fontSize: 10, hideOverlap: true },
        axisLine: { lineStyle: { color: line } },
      },
      yAxis: [
        {
          type: "value",
          scale: true,
          axisLabel: { color: muted, fontSize: 10 },
          splitLine: { lineStyle: { color: line, type: "dashed" } },
        },
        {
          type: "value",
          scale: true,
          axisLabel: {
            color: muted,
            fontSize: 10,
            formatter(value) {
              return `${value}%`;
            },
          },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "Close",
          type: "line",
          yAxisIndex: 0,
          showSymbol: false,
          smooth: false,
          lineStyle: { width: 2 },
          data: filteredPoints.map((point) => point.close_price),
        },
        {
          name: "M20",
          type: "line",
          yAxisIndex: 0,
          showSymbol: false,
          smooth: false,
          connectNulls: false,
          lineStyle: { width: 1.8, type: "dashed" },
          data: filteredPoints.map((point) => point.ma20_price),
        },
        {
          name: "Deviation",
          type: "bar",
          yAxisIndex: 1,
          barMaxWidth: 10,
          itemStyle: {
            color(params) {
              const value = Number(params.value || 0);
              if (value > 0) {
                return danger;
              }
              if (value < 0) {
                return ok;
              }
              return muted;
            },
          },
          markLine: {
            symbol: "none",
            lineStyle: { color: line, type: "dashed" },
            data: [{ yAxis: 0 }],
          },
          data: filteredPoints.map((point) => point.deviation_pct),
        },
      ],
    },
    true,
  );
  chart.resize();
}

function renderMacroComparisonChart(section, rootId, rangeKey = "all") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  const primary = section?.primary || null;
  const secondary = section?.secondary || null;
  const primaryPoints = filterMacroSeriesByRange(
    Array.isArray(primary?.points) ? primary.points : [],
    rangeKey,
  );
  const secondaryPoints = filterMacroSeriesByRange(
    Array.isArray(secondary?.points) ? secondary.points : [],
    rangeKey,
  );
  if (!primaryPoints.length && !secondaryPoints.length) {
    root.innerHTML = marketChartEmptyState("暂无可绘制的宏观历史序列");
    return;
  }
  if (!window.echarts) {
    root.innerHTML = marketChartEmptyState("ECharts 未加载，无法绘制宏观对比图");
    return;
  }

  root.innerHTML = "";
  const computedStyle = window.getComputedStyle(document.documentElement);
  const ink = (computedStyle.getPropertyValue("--ink") || "#e7edf5").trim();
  const muted = (computedStyle.getPropertyValue("--muted") || "#91a0b1").trim();
  const line = (computedStyle.getPropertyValue("--line") || "rgba(140, 160, 180, 0.18)").trim();
  const accent2 = (computedStyle.getPropertyValue("--accent-2") || "#31b8c4").trim();
  const ok = (computedStyle.getPropertyValue("--ok") || "#37c48d").trim();
  const labels = collectMacroLabels(primaryPoints, secondaryPoints);
  const valueByLabel = (points) => {
    const map = new Map();
    points.forEach((point) => map.set(point.period_label || point.period_end, point.value));
    return labels.map((label) => (map.has(label) ? map.get(label) : null));
  };
  const legendData = [primary?.label, secondary?.label].filter(Boolean);
  const series = [];
  if (primary) {
    series.push({
      name: primary.label,
      type: "line",
      showSymbol: labels.length <= 18,
      symbolSize: 6,
      smooth: 0.18,
      lineStyle: { width: 2.4 },
      data: valueByLabel(primaryPoints),
    });
  }
  if (secondary) {
    series.push({
      name: secondary.label,
      type: "line",
      showSymbol: labels.length <= 18,
      symbolSize: 6,
      smooth: 0.18,
      lineStyle: { width: 2.4 },
      data: valueByLabel(secondaryPoints),
    });
  }
  const chart = window.echarts.getInstanceByDom(root) || window.echarts.init(root);
  marketChartInstances.set(rootId, chart);
  chart.setOption(
    {
      animation: false,
      color: [accent2, ok],
      grid: { left: 54, right: 24, top: 48, bottom: 42 },
      legend: {
        top: 8,
        textStyle: { color: muted, fontSize: 11 },
        data: legendData,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: getCurrentTheme() === "light" ? "rgba(255,255,255,0.95)" : "rgba(10,13,17,0.96)",
        borderColor: line,
        textStyle: { color: ink },
        valueFormatter(value) {
          return formatMacroChartValue(value, primary?.unit || "");
        },
      },
      xAxis: {
        type: "category",
        data: labels,
        boundaryGap: false,
        axisLabel: { color: muted, fontSize: 10, hideOverlap: true },
        axisLine: { lineStyle: { color: line } },
      },
      yAxis: {
        type: "value",
        scale: true,
        axisLabel: {
          color: muted,
          fontSize: 10,
          formatter(value) {
            return formatMacroChartValue(value, primary?.unit || "");
          },
        },
        splitLine: { lineStyle: { color: line, type: "dashed" } },
      },
      series,
    },
    true,
  );
  chart.resize();
}

function getLatestMacroDelta(section) {
  const deltaPoints = Array.isArray(section?.delta_points) ? section.delta_points : [];
  return deltaPoints.length ? deltaPoints[deltaPoints.length - 1] : null;
}

function renderMacroSourceLinks(section) {
  const explicitSources = Array.isArray(section?.sources) ? section.sources : [];
  const fallbackSources = [section?.primary, section?.secondary]
    .filter(Boolean)
    .map((item) => ({ label: item.source_label, url: item.source_url }));
  const sourceItems = (explicitSources.length ? explicitSources : fallbackSources)
    .filter((item) => item && item.label);

  if (!sourceItems.length) {
    return '<span class="card-meta">来源: 暂无数据源信息</span>';
  }

  return `
    <div class="macro-source-links">
      <span class="card-meta">来源:</span>
      ${sourceItems
        .map((item) => {
          const label = escapeHtml(item.label || "数据源");
          const url = String(item.url || "").trim();
          if (!url) {
            return `<span class="macro-source-link is-text">${label}</span>`;
          }
          return `<a class="macro-source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(url)}">${label}</a>`;
        })
        .join("")}
    </div>
  `;
}

function renderMacroMetricStrip(item, tone = "primary") {
  return `
    <article class="macro-metric-strip ${tone}">
      <div class="macro-metric-top">
        <h5>${escapeHtml(item.label)}</h5>
        <span class="macro-metric-chip">${escapeHtml(macroFrequencyMap[item.frequency] || item.frequency || "未知")}</span>
      </div>
      <div class="macro-metric-main">
        <span class="macro-metric-value">${escapeHtml(item.latest_value)}</span>
        <span class="macro-metric-trend ${escapeHtml(item.trend)}">${escapeHtml(trendMap[item.trend] || item.trend || "未知")}</span>
      </div>
      <p class="macro-metric-meta">${escapeHtml(item.change_label)}</p>
      <p class="macro-metric-meta">${escapeHtml(item.period_label)} | ${escapeHtml(item.updated_at)}</p>
    </article>
  `;
}

function renderMacroCard(section) {
  const sectionKey = section.key || section.primary?.key || section.secondary?.key || "macro";
  const activeRange = getActiveMacroChartRange(sectionKey, section);
  const rangeSwitch = renderMacroChartRangeSwitch(sectionKey, section);
  const latestDelta = getLatestMacroDelta(section);
  const filteredPrimary = filterMacroSeriesByRange(section.primary?.points || [], activeRange);
  const filteredSecondary = filterMacroSeriesByRange(section.secondary?.points || [], activeRange);
  const coverageLabel = buildMacroCoverageLabel(filteredPrimary, filteredSecondary);
  const context = section.primary?.context || section.secondary?.context || "";
  const summaryItems = [renderMacroMetricStrip(section.primary, "primary")];
  if (section.secondary) {
    summaryItems.push(renderMacroMetricStrip(section.secondary, "secondary"));
  }
  const quickMeta = [
    `覆盖 ${coverageLabel}`,
    latestDelta && section.delta_label
      ? `${section.delta_label} ${formatMacroChartValue(latestDelta.value, section.primary.unit || "")}`
      : "",
  ].filter(Boolean);
  return `
    <article class="info-card macro-grid-card">
      <div class="card-head macro-card-head">
        <div class="macro-card-title">
          <h4>${escapeHtml(section.title)}</h4>
          <p class="card-meta">${escapeHtml(section.description || "")}</p>
        </div>
        <div class="market-chart-tools">${rangeSwitch}${statusBadge(section.status)}</div>
      </div>
      <div class="macro-summary-grid">
        ${summaryItems.join("")}
      </div>
      <div class="macro-chart-panel">
        <div class="macro-panel-meta">
          <span class="macro-panel-label">${escapeHtml(section.summary)}</span>
          ${quickMeta.map((item) => `<span class="macro-panel-pill">${escapeHtml(item)}</span>`).join("")}
        </div>
        <div id="macroCompareChart-${escapeHtml(sectionKey)}" class="market-trend-chart macro-trend-chart" aria-label="${escapeHtml(`${section.title}走势`)}"></div>
      </div>
      <div class="macro-card-foot">
        ${renderMacroSourceLinks(section)}
        ${context ? `<p class="card-meta">${escapeHtml(context)}</p>` : ""}
      </div>
    </article>
  `;
}

function renderMacroOverview(module) {
  if (!module.details?.length) {
    return `<article class="info-card"><p class="detail-copy">当前宏观模块暂无可展示内容。</p></article>`;
  }
  return `
    <div class="content-stack">
      <article class="info-card macro-overview-intro">
        <div class="card-head">
          <h4>${escapeHtml(module.label)}总览</h4>
          ${statusBadge(module.status)}
        </div>
        <p class="detail-copy">紧凑看板模式。大屏单行 3 到 4 张卡片，保留关键数值、趋势和来源链接，弱化冗余说明。</p>
      </article>
      <div class="macro-overview-grid">
        ${module.details.map((detail) => renderMacroCard(detail.section)).join("")}
      </div>
    </div>
  `;
}

function renderMacroOverviewCharts(module) {
  if (module?.id !== "macro") {
    return;
  }
  (module.details || []).forEach((detail) => {
    const sectionKey = detail.section?.key || detail.id;
    const activeRange = getActiveMacroChartRange(sectionKey, detail.section);
    renderMacroComparisonChart(detail.section, `macroCompareChart-${sectionKey}`, activeRange);
  });
}

function renderTable(headers, rows, options = {}) {
  const classes = ["terminal-table"];
  if (options.compact) {
    classes.push("compact");
  }
  if (options.tableClass) {
    classes.push(options.tableClass);
  }
  const rowStyle = options.columnsTemplate ? ` style="grid-template-columns:${escapeHtml(options.columnsTemplate)};"` : "";
  return `
    <div class="${classes.join(" ")}">
      <div class="terminal-row terminal-row-header"${rowStyle}>
        ${headers.map((header) => `<div class="terminal-cell ${header.className || ""}">${escapeHtml(header.label)}</div>`).join("")}
      </div>
      ${
        rows.length
          ? rows
              .map(
                (row) => `
                  <div class="terminal-row"${rowStyle}>
                    ${row
                      .map((cell) => `<div class="terminal-cell ${cell.className || ""}">${cell.html ?? escapeHtml(cell.text ?? "")}</div>`)
                      .join("")}
                  </div>
                `,
              )
              .join("")
          : `<div class="terminal-row terminal-row-empty"><div class="terminal-cell">${escapeHtml(options.emptyText || "暂无内容")}</div></div>`
      }
    </div>
  `;
}

function renderNewsTable(section) {
  const rows = (section.items || []).map((item) => {
    const url = normalizeNewsUrl(item.url);
    const summary = normalizeSummaryText(item.summary);
    const title = url
      ? `<a class="headline-link news-title-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</a>`
      : `<span class="headline-link news-title-link disabled" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>`;
    const metaParts = [];
    if (item.source) {
      metaParts.push(`<span class="news-title-meta-item">${escapeHtml(item.source)}</span>`);
    }
    if (item.published_at) {
      metaParts.push(`<span class="news-title-meta-item cell-mono">${escapeHtml(item.published_at)}</span>`);
    }
    if (item.tag) {
      metaParts.push(`<span class="news-title-meta-item news-title-meta-tag">${escapeHtml(String(item.tag).toUpperCase())}</span>`);
    }
    const titleCell = `
      <div class="news-title-cell">
        ${title}
        ${metaParts.length ? `<div class="news-title-meta">${metaParts.join('<span class="news-title-meta-separator">/</span>')}</div>` : ""}
      </div>
    `;
    const summaryCell = summary
      ? `<span class="news-summary-text" title="${escapeHtml(summary)}">${escapeHtml(summary)}</span>`
      : `<span class="news-summary-empty">-</span>`;
    return [
      { text: String(item.rank), className: "cell-mono cell-rank" },
      { html: titleCell, className: "cell-title" },
      { html: summaryCell, className: "cell-summary" },
    ];
  });
  return renderTable(
    [
      { label: "Rank", className: "cell-mono cell-rank" },
      { label: "Title", className: "cell-title" },
      { label: "Summary", className: "cell-summary" },
    ],
    rows,
    {
      emptyText: "暂无新闻内容",
      columnsTemplate: "56px minmax(0, 1fr) minmax(0, 2fr)",
      tableClass: "news-table",
    },
  );
}

function renderEventsTable(items) {
  const rows = [];
  for (const section of items || []) {
    for (const item of section.items || []) {
      rows.push([
        { text: item.expected_date || section.title, className: "cell-mono" },
        { text: item.region || "-", className: "cell-tight cell-cyan" },
        { text: item.title, className: "cell-grow" },
        { text: item.impact_summary || "-", className: "cell-grow cell-muted" },
        { text: confidenceMap[item.confidence] || item.confidence, className: "cell-tight" },
        { text: item.source, className: "cell-muted" },
      ]);
    }
  }
  return renderTable(
    [
      { label: "Date", className: "cell-mono" },
      { label: "Region" },
      { label: "Event", className: "cell-grow" },
      { label: "Summary", className: "cell-grow" },
      { label: "Confidence" },
      { label: "Source" },
    ],
    rows,
    { emptyText: "暂无事件展望数据" },
  );
}

function renderOfficialLinkCard(links) {
  if (!links?.length) {
    return "";
  }
  return `
    <article class="info-card">
      <div class="card-head">
        <h4>Official Links</h4>
        <span class="tab-note">${escapeHtml(`${links.length} sources`)}</span>
      </div>
      <div class="quick-links">
        ${links
          .map(
            (link) =>
              `<a href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(link.url)}">${escapeHtml(`${link.region} · ${link.label}`)}</a>`,
          )
          .join("")}
      </div>
    </article>
  `;
}

function renderMarketSummaryTable(module, detail) {
  const rows = (module.details || [])
    .map((item) => `
      <div class="terminal-row market-summary-row" style="grid-template-columns:minmax(140px, 1.5fr) repeat(3, minmax(110px, 1fr));">
        <div class="terminal-cell cell-grow ${item.id === detail.id ? "cell-accent" : ""}">${escapeHtml(item.label)}</div>
        <div class="terminal-cell cell-mono">${escapeHtml(item.section.close_value)}</div>
        <div class="terminal-cell cell-mono">${escapeHtml(item.section.ma20_value)}</div>
        <div class="terminal-cell cell-mono">${escapeHtml(item.section.deviation_pct)}</div>
      </div>
    `)
    .join("");

  return `
    <article class="info-card market-summary-card">
      <div class="card-head">
        <h4>大盘指数汇总</h4>
        <span class="tab-note">${escapeHtml(`${module.details.length} 个指数`)}</span>
      </div>
      <p class="card-meta">鱼盆模型跟踪</p>
      <div class="table-scroll">
        <div class="terminal-table compact">
          <div class="terminal-row terminal-row-header" style="grid-template-columns:minmax(140px, 1.5fr) repeat(3, minmax(110px, 1fr));">
            <div class="terminal-cell cell-grow">指数</div>
            <div class="terminal-cell cell-mono">收盘点位</div>
            <div class="terminal-cell cell-mono">M20</div>
            <div class="terminal-cell cell-mono">乖离率</div>
          </div>
          ${
            rows
              || `<div class="terminal-row terminal-row-empty"><div class="terminal-cell">暂无大盘指数汇总数据</div></div>`
          }
        </div>
      </div>
    </article>
  `;
}

function renderMarketSnapshotCard(detail, historyWindow) {
  return `
    <article class="info-card market-snapshot-card">
      <div class="card-head">
        <h4>实时市场快照</h4>
        ${statusBadge(detail.section.status)}
      </div>
      <p class="card-meta">${escapeHtml(detail.section.trade_date || "-")} | ${escapeHtml(detail.label)}</p>
      <div class="detail-grid market-snapshot-grid">
        ${detailItem("收盘价", detail.section.close_value || "-")}
        ${detailItem("MA20", detail.section.ma20_value || "-")}
        ${detailItem("模型信号", signalMap[detail.section.signal] || detail.section.signal || "-")}
        ${detailItem("偏离", detail.section.deviation_pct || "-")}
        ${detailItem("交易日", detail.section.trade_date || "-")}
        ${detailItem("历史窗口", historyWindow || "-")}
      </div>
      <div class="detail-item market-detail-story">
        <span class="detail-label">说明</span>
        <span class="detail-value cell-muted">${escapeHtml(detail.section.explanation || "-")}</span>
      </div>
    </article>
  `;
}

function splitCsvValues(value) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderPushSourceOptions(options, selectedIds, inputName) {
  return (options || [])
    .map((option) => `
      <label class="push-check ${option.enabled ? "" : "disabled"}">
        <input
          type="checkbox"
          ${option.enabled ? "" : "disabled"}
          ${selectedIds.includes(option.id) ? "checked" : ""}
          ${inputName ? `${inputName}="${escapeHtml(option.id)}"` : ""}
        />
        <span class="push-check-copy">
          <strong>${escapeHtml(option.label)}</strong>
          <span>${escapeHtml(option.description || "")}</span>
        </span>
      </label>
    `)
    .join("");
}

function renderPushScheduleRow(schedule, index, moduleOptions) {
  const moduleIds = Array.isArray(schedule?.module_ids) ? schedule.module_ids : ["market"];
  const safeIndex = Number(index) || 0;
  return `
    <div class="push-schedule-row" data-push-schedule-row="${safeIndex}">
      <div class="push-schedule-head">
        <h5>任务 ${safeIndex + 1}</h5>
        <button type="button" class="retry-button push-inline-button" data-remove-schedule="${safeIndex}">移除</button>
      </div>
      <div class="push-form-grid">
        <label class="push-field">
          <span>任务名称</span>
          <input type="text" data-schedule-name value="${escapeHtml(schedule?.name || `推送任务 ${safeIndex + 1}`)}" />
        </label>
        <label class="push-field">
          <span>执行时间</span>
          <input type="text" data-schedule-times value="${escapeHtml((schedule?.times || ["08:00"]).join(", "))}" placeholder="08:00, 12:05, 17:00" />
        </label>
        <label class="push-field">
          <span>时区</span>
          <input type="text" data-schedule-timezone value="${escapeHtml(schedule?.timezone || "Asia/Shanghai")}" />
        </label>
        <label class="push-toggle">
          <input type="checkbox" data-schedule-enabled ${schedule?.enabled === false ? "" : "checked"} />
          <span>启用任务</span>
        </label>
      </div>
      <div class="push-check-grid">
        ${renderPushSourceOptions(moduleOptions, moduleIds, "data-schedule-module")}
      </div>
    </div>
  `;
}

function renderPushWorkspace(detail) {
  const section = detail.section || {};
  const config = section.config || {};
  const configPath = section.config_path || ".data/push_center.json";
  const email = config.email || {};
  const preview = section.preview || {};
  const recentRuns = Array.isArray(section.recent_runs) ? section.recent_runs : [];
  const moduleOptions = section.source_module_options || [];
  const styleOptions = section.style_options || [];
  const schedules = Array.isArray(config.schedules) && config.schedules.length
    ? config.schedules
    : [{ name: "市场日报", times: ["08:00", "12:05", "17:00"], timezone: "Asia/Shanghai", enabled: true, module_ids: config.selected_module_ids || ["market"] }];
  const flash = section.flash || null;
  return `
    <div class="content-stack push-layout" data-push-workspace>
      <div class="grid-two push-grid">
        <article class="info-card push-control-card push-config-card">
          <div class="card-head">
            <h4>推送配置</h4>
            ${statusBadge(preview.ok === false ? "degraded" : "compatible")}
          </div>
          <p class="detail-copy">先配置投递方式与 SMTP 参数，再选择可用于日报的模块与样式。</p>
          ${flash ? `<div class="push-flash push-flash-${escapeHtml(flash.status || "compatible")}">${escapeHtml(flash.message || "")}</div>` : ""}
          <div class="push-form-grid">
            <label class="push-field">
              <span>推送方式</span>
              <select data-push-channel-type>
                ${(section.channel_type_options || []).map((option) => `
                  <option value="${escapeHtml(option.id)}" ${option.id === "email" ? "selected" : ""} ${option.enabled ? "" : "disabled"}>
                    ${escapeHtml(option.label)}${option.enabled ? "" : " (即将支持)"}
                  </option>
                `).join("")}
              </select>
            </label>
            <label class="push-field">
              <span>日报样式</span>
              <select data-push-style>
                ${styleOptions.map((option) => `
                  <option value="${escapeHtml(option.id)}" ${config.report_style === option.id ? "selected" : ""}>
                    ${escapeHtml(option.label)}${option.recommended ? " (推荐)" : ""}
                  </option>
                `).join("")}
              </select>
            </label>
          </div>
          <div class="push-check-grid">
            ${renderPushSourceOptions(moduleOptions, config.selected_module_ids || ["market"], "data-push-module")}
          </div>
          <div class="push-form-grid push-email-grid">
            <label class="push-field">
              <span>SMTP 服务器</span>
              <input type="text" data-push-email-field="smtp_server" value="${escapeHtml(email.smtp_server || "")}" placeholder="smtp.gmail.com" />
            </label>
            <label class="push-field">
              <span>端口</span>
              <input type="number" data-push-email-field="smtp_port" value="${escapeHtml(email.smtp_port || 587)}" />
            </label>
            <label class="push-field">
              <span>用户名</span>
              <input type="text" data-push-email-field="username" value="${escapeHtml(email.username || "")}" placeholder="bot@example.com" />
            </label>
            <label class="push-field">
              <span>密码 / App Password</span>
              <input type="password" data-push-email-field="password" value="${escapeHtml(email.password || "")}" placeholder="SMTP 密码" />
            </label>
            <label class="push-field">
              <span>发件人</span>
              <input type="text" data-push-email-field="from_address" value="${escapeHtml(email.from_address || "")}" placeholder="bot@example.com" />
            </label>
            <label class="push-field">
              <span>收件人</span>
              <input type="text" data-push-email-field="to_addresses" value="${escapeHtml(email.to_addresses || "")}" placeholder="a@example.com, b@example.com" />
            </label>
          </div>
          <label class="push-toggle">
            <input type="checkbox" data-push-email-field="use_tls" ${email.use_tls === false ? "" : "checked"} />
            <span>启用 STARTTLS</span>
          </label>
          <div class="push-action-row">
            <button type="button" class="module-refresh-button" data-push-action="save">保存配置</button>
            <button type="button" class="module-refresh-button" data-push-action="preview">刷新预览</button>
            <button type="button" class="retry-button" data-push-action="send">立即推送</button>
          </div>
        </article>

        <article class="info-card push-preview-card">
          <div class="card-head">
            <h4>日报预览</h4>
            <span class="tab-note">${escapeHtml(preview.style || config.report_style || "newspaper")}</span>
          </div>
          <div class="detail-grid">
            ${detailItem("Subject", preview.subject || "推送预览不可用")}
            ${detailItem("Modules", (preview.selected_module_ids || config.selected_module_ids || []).join(", ") || "market")}
            ${detailItem("Generated", preview.generated_at || "-")}
          </div>
          ${preview.ok === false && preview.error ? `<p class="market-warning">${escapeHtml(preview.error)}</p>` : ""}
          <iframe id="pushPreviewFrame" class="push-preview-frame" title="Push preview"></iframe>
        </article>
      </div>

      <article class="info-card push-control-card push-schedule-card">
          <div class="card-head">
            <h4>定时任务</h4>
            <div class="push-schedule-actions">
              <button type="button" class="module-refresh-button" data-push-action="save">保存定时配置</button>
              <button type="button" class="module-refresh-button" data-add-schedule>新增任务</button>
            </div>
          </div>
          <p class="detail-copy">可以为不同模块分别配置不同推送时间。目前默认已预置 08:00 / 12:05 / 17:00，修改后需要点击保存配置。</p>
          <p class="card-meta">当前配置文件: ${escapeHtml(configPath)}</p>
          <div id="pushScheduleList" class="content-stack">
            ${schedules.map((schedule, index) => renderPushScheduleRow(schedule, index, moduleOptions)).join("")}
          </div>
      </article>

      <article class="info-card push-control-card">
        <div class="card-head">
          <h4>最近执行记录</h4>
          <span class="tab-note">${escapeHtml(String(recentRuns.length))}</span>
        </div>
        ${renderPushRecentRunsTable(recentRuns)}
      </article>
    </div>
  `;
}

function renderPushRecentRunsTable(runs) {
  const rows = (runs || []).map((run) => [
    { text: run.executed_at || "-", className: "cell-mono cell-tight" },
    { html: statusBadge(run.status || "unknown"), className: "cell-tight" },
    { text: run.trigger || "-", className: "cell-tight" },
    { text: run.job_name || "-", className: "cell-grow" },
    { text: run.detail || "-", className: "cell-grow" },
  ]);
  return renderTable(
    [
      { label: "Executed", className: "cell-mono cell-tight" },
      { label: "Status", className: "cell-tight" },
      { label: "Trigger", className: "cell-tight" },
      { label: "Job", className: "cell-grow" },
      { label: "Detail", className: "cell-grow" },
    ],
    rows,
    {
      compact: true,
      emptyText: "暂无推送记录",
      columnsTemplate: "180px 96px 88px minmax(120px, 1fr) minmax(180px, 2fr)",
      tableClass: "push-runs-table",
    },
  );
}

function currentPushDetail() {
  const module = viewState.modules.find((item) => item.id === "push");
  if (!module) {
    return null;
  }
  return module.details.find((detail) => detail.kind === "push") || module.details[0] || null;
}

function updatePushSection(nextSection) {
  const detail = currentPushDetail();
  if (!detail) {
    return;
  }
  detail.section = {
    ...(detail.section || {}),
    ...(nextSection || {}),
  };
}

function renderPushPreviewFrame(preview) {
  const frame = document.getElementById("pushPreviewFrame");
  if (!frame) {
    return;
  }
  const fallback = `<!DOCTYPE html><html><body style="font-family:Segoe UI,sans-serif;padding:24px;color:#555;">${escapeHtml(preview?.error || "暂无预览")}</body></html>`;
  frame.srcdoc = preview?.ok === false ? fallback : (preview?.html_body || fallback);
}

function collectPushDraft() {
  const detail = currentPushDetail();
  const section = detail?.section || {};
  const selectedModuleIds = Array.from(document.querySelectorAll("[data-push-module]:checked"))
    .map((node) => node.getAttribute("data-push-module"))
    .filter(Boolean);
  const schedules = Array.from(document.querySelectorAll("[data-push-schedule-row]")).map((row, index) => ({
    id: row.getAttribute("data-push-schedule-row") || `schedule-${index + 1}`,
    name: row.querySelector("[data-schedule-name]")?.value || `推送任务 ${index + 1}`,
    enabled: Boolean(row.querySelector("[data-schedule-enabled]")?.checked),
    timezone: row.querySelector("[data-schedule-timezone]")?.value || "Asia/Shanghai",
    times: splitCsvValues(row.querySelector("[data-schedule-times]")?.value || ""),
    module_ids: Array.from(row.querySelectorAll("[data-schedule-module]:checked"))
      .map((node) => node.getAttribute("data-schedule-module"))
      .filter(Boolean),
    channel_types: ["email"],
  }));
  return {
    ...(section.config || {}),
    selected_module_ids: selectedModuleIds.length ? selectedModuleIds : ["market"],
    report_style: document.querySelector("[data-push-style]")?.value || "newspaper",
    email: {
      enabled: true,
      smtp_server: document.querySelector("[data-push-email-field='smtp_server']")?.value || "",
      smtp_port: Number(document.querySelector("[data-push-email-field='smtp_port']")?.value || 587),
      username: document.querySelector("[data-push-email-field='username']")?.value || "",
      password: document.querySelector("[data-push-email-field='password']")?.value || "",
      from_address: document.querySelector("[data-push-email-field='from_address']")?.value || "",
      to_addresses: document.querySelector("[data-push-email-field='to_addresses']")?.value || "",
      use_tls: Boolean(document.querySelector("[data-push-email-field='use_tls']")?.checked),
    },
    schedules,
  };
}

async function requestPushApi(path, payload, method = "POST") {
  const response = await fetch(path, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ config: payload }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function renderLoadingCard(message) {
  return `<article class="info-card loading-card"><div class="card-head"><h4>数据加载中</h4>${statusBadge("loading")}</div><div class="loading-card-copy">${loadingSpinner(message || "模块数据正在加载...", false)}</div></article>`;
}

function renderErrorCard(message, moduleId) {
  return `<article class="info-card"><div class="card-head"><h4>加载失败</h4>${statusBadge("unavailable")}</div><p class="detail-copy">${escapeHtml(message || "模块数据暂时不可用。")}</p><button type="button" class="retry-button" data-retry-module="${escapeHtml(moduleId)}">重新加载</button></article>`;
}

function renderModuleContent(module, detail) {
  if (module.id === "macro") {
    return renderMacroOverview(module);
  }

  if (detail.kind === "news") {
    return `<div class="content-stack"><article class="info-card"><div class="card-head"><h4>${escapeHtml(detail.section.title)}</h4>${statusBadge(detail.section.status)}</div><p class="detail-copy">${escapeHtml(detail.section.description)}</p></article><div class="table-scroll">${renderNewsTable(detail.section)}</div></div>`;
  }
  if (detail.kind === "market") {
    const historyWindow = detail.section.data_window_label || "最近可用窗口";
    const activeRange = getActiveMarketChartRange(detail.id, detail.section);
    const activeRangeLabel = getMarketRangeOption(activeRange).label;
    const rangeSwitch = renderMarketChartRangeSwitch(detail.id, detail.section);
    const historyWarning = detail.section.history_warning
      ? `<p class="market-warning">${escapeHtml(detail.section.history_warning)}</p>`
      : "";
    return `<div class="content-stack"><div class="market-focus-row"><article class="info-card market-chart-panel"><div class="card-head"><h4>${escapeHtml(detail.label)} Trend</h4><div class="market-chart-tools">${rangeSwitch}${statusBadge(detail.section.status)}</div></div><p class="card-meta">显示范围: ${escapeHtml(activeRangeLabel)} | 历史覆盖: ${escapeHtml(historyWindow)} | 组合图展示收盘价、M20 与乖离率。</p><div id="marketTrendChart" class="market-trend-chart" aria-label="${escapeHtml(`${detail.label} 历史趋势图`)}"></div>${historyWarning}</article>${renderMarketSnapshotCard(detail, historyWindow)}</div>${renderMarketSummaryTable(module, detail)}</div>`;
  }
  if (detail.kind === "events") {
    return `<div class="content-stack"><article class="info-card"><div class="card-head"><h4>${escapeHtml(detail.section.title)}</h4>${statusBadge(detail.section.status)}</div><p class="detail-copy">当前窗口收录 ${(detail.section.items || []).length} 条事件。</p></article>${renderEventsTable([detail.section])}${renderOfficialLinkCard(detail.section.official_links || [])}</div>`;
  }
  if (detail.kind === "push") {
    return renderPushWorkspace(detail);
  }
  if (detail.kind === "status") {
    return renderTable(
      [
        { label: "Field" },
        { label: "Value", className: "cell-grow" },
      ],
      [
        [{ text: "模块", className: "cell-tight cell-cyan" }, { text: detail.section.label, className: "cell-grow" }],
        [{ text: "状态", className: "cell-tight cell-cyan" }, { html: statusBadge(detail.section.status), className: "cell-grow" }],
        [{ text: "说明", className: "cell-tight cell-cyan" }, { text: detail.section.detail, className: "cell-grow cell-muted" }],
      ],
    );
  }
  return `<article class="info-card"><p class="detail-copy">暂无内容。</p></article>`;
}

function renderModuleNav() {
  document.getElementById("moduleNav").innerHTML = viewState.modules
    .map(
      (module) =>
        `<button type="button" class="module-button ${module.id === viewState.activeModuleId ? "active" : ""}" data-module-id="${escapeHtml(module.id)}">${statusBadge(module.loading ? "loading" : module.error ? "unavailable" : module.status)}<span class="module-button-title">${escapeHtml(module.label)}</span><span class="module-button-note">${escapeHtml(module.note || "等待加载")}</span></button>`,
    )
    .join("");

  document.querySelectorAll("[data-module-id]").forEach((node) => {
    node.addEventListener("click", () => navigate(node.getAttribute("data-module-id"), ""));
  });
}

function bindContentActions() {
  document.querySelectorAll("[data-detail-id]").forEach((node) => {
    node.addEventListener("click", () => {
      const module = currentModule();
      navigate(module.id, node.getAttribute("data-detail-id"));
    });
  });
  document.querySelectorAll("[data-retry-module]").forEach((node) => {
    node.addEventListener("click", () => loadModule(node.getAttribute("data-retry-module"), { resetContent: true, forceRefresh: true }));
  });
  document.querySelectorAll("[data-refresh-module]").forEach((node) => {
    node.addEventListener("click", () => loadModule(node.getAttribute("data-refresh-module"), { forceRefresh: true }));
  });
  document.querySelectorAll("[data-market-range]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.disabled) {
        return;
      }
      const module = currentModule();
      const detail = currentDetail(module);
      if (!detail || detail.kind !== "market") {
        return;
      }
      const rangeKey = node.getAttribute("data-market-range");
      if (!rangeKey) {
        return;
      }
      viewState.activeMarketChartRangeByDetail[detail.id] = rangeKey;
      renderModulePanel();
    });
  });
  document.querySelectorAll("[data-macro-range]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.disabled) {
        return;
      }
      const module = currentModule();
      if (module?.id !== "macro") {
        return;
      }
      const rangeKey = node.getAttribute("data-macro-range");
      const sectionKey = node.getAttribute("data-macro-section");
      if (!rangeKey || !sectionKey) {
        return;
      }
      viewState.activeMacroChartRangeBySection[sectionKey] = rangeKey;
      renderModulePanel();
    });
  });
  document.querySelectorAll("[data-add-schedule]").forEach((node) => {
    node.addEventListener("click", () => {
      const detail = currentPushDetail();
      const section = detail?.section || {};
      const moduleOptions = section.source_module_options || [];
      const root = document.getElementById("pushScheduleList");
      if (!root) {
        return;
      }
      const nextIndex = root.querySelectorAll("[data-push-schedule-row]").length;
      root.insertAdjacentHTML(
        "beforeend",
        renderPushScheduleRow(
          {
            name: `推送任务 ${nextIndex + 1}`,
            times: ["08:00"],
            timezone: "Asia/Shanghai",
            enabled: true,
            module_ids: ["market"],
          },
          nextIndex,
          moduleOptions,
        ),
      );
      const newRow = root.lastElementChild;
      newRow?.querySelectorAll("[data-remove-schedule]").forEach((button) => {
        button.addEventListener("click", () => {
          const row = button.closest("[data-push-schedule-row]");
          if (row) {
            row.remove();
          }
        });
      });
    });
  });
  document.querySelectorAll("[data-remove-schedule]").forEach((node) => {
    node.addEventListener("click", () => {
      const row = node.closest("[data-push-schedule-row]");
      if (row) {
        row.remove();
      }
    });
  });
  document.querySelectorAll("[data-push-action]").forEach((node) => {
    node.addEventListener("click", async () => {
      const action = node.getAttribute("data-push-action");
      const draft = collectPushDraft();
      updatePushSection({
        config: draft,
        flash: { status: "compatible", message: action === "send" ? "正在发送..." : "正在处理..." },
      });
      renderModulePanel();
        try {
          if (action === "save") {
            const payload = await requestPushApi("/api/push/config", draft, "PUT");
            applyModulePayload(payload);
            const savedPath = payload?.module?.details?.[0]?.section?.config_path || ".data/push_center.json";
            updatePushSection({ flash: { status: "compatible", message: `配置已保存到 ${savedPath}。` } });
            renderModulePanel();
            return;
          }
        if (action === "preview") {
          const payload = await requestPushApi("/api/push/preview", draft, "POST");
          updatePushSection({
            config: payload.config,
            preview: payload.preview,
            recent_runs: currentPushDetail()?.section?.recent_runs || [],
            flash: { status: "compatible", message: "预览已刷新。" },
          });
          renderModulePanel();
          return;
        }
        const payload = await requestPushApi("/api/push/trigger", draft, "POST");
        updatePushSection({
          config: draft,
          preview: payload.preview,
          recent_runs: payload.recent_runs || [],
          flash: {
            status: payload.ok ? "compatible" : "degraded",
            message: payload.result?.detail || (payload.ok ? "推送完成。" : "推送失败。"),
          },
        });
        renderModulePanel();
      } catch (error) {
        updatePushSection({
          config: draft,
          flash: { status: "degraded", message: error.message || "请求失败" },
        });
        renderModulePanel();
      }
    });
  });
}

function renderModulePanel() {
  const module = currentModule();
  const detail = currentDetail(module);
  disposeMarketCharts();
  document.getElementById("activeModuleEyebrow").textContent = module.label;
  document.getElementById("activeModuleDescription").textContent = module.description;
  document.getElementById("moduleStatus").innerHTML = `${statusBadge(module.loading ? "loading" : module.error ? "unavailable" : module.status)}<span class="tab-note">${escapeHtml(module.note || "")}</span><button type="button" class="module-refresh-button" data-refresh-module="${escapeHtml(module.id)}">手动刷新</button>`;

  if (module.loading && !module.loaded) {
    document.getElementById("activeModuleTitle").textContent = `${module.label} / 加载中...`;
    document.getElementById("detailTabs").innerHTML = "";
    document.getElementById("contentStage").innerHTML = renderLoadingCard(module.loadingMessage);
    bindContentActions();
    return;
  }

  if (module.error && !module.loaded) {
    document.getElementById("activeModuleTitle").textContent = `${module.label} / 加载失败`;
    document.getElementById("detailTabs").innerHTML = "";
    document.getElementById("contentStage").innerHTML = renderErrorCard(module.error, module.id);
    bindContentActions();
    return;
  }

  if (!detail) {
    document.getElementById("activeModuleTitle").textContent = `${module.label} / 暂无内容`;
    document.getElementById("detailTabs").innerHTML = "";
    document.getElementById("contentStage").innerHTML = `<article class="info-card"><p class="detail-copy">当前模块暂无可展示内容。</p></article>`;
    bindContentActions();
    return;
  }

  viewState.activeDetailByModule[module.id] = detail.id;
  document.getElementById("activeModuleTitle").textContent = module.id === "macro" ? `${module.label}总览` : detail.label;
  document.getElementById("detailTabs").innerHTML =
    module.id === "macro"
      ? ""
      : module.details.length > 1
        ? module.details
            .map(
              (item) => `<button type="button" class="detail-tab ${item.id === detail.id ? "active" : ""}" data-detail-id="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`,
            )
            .join("")
        : "";
  document.getElementById("contentStage").innerHTML = renderModuleContent(module, detail);
  bindContentActions();
  if (module.id === "macro") {
    renderMacroOverviewCharts(module);
  } else if (detail.kind === "market") {
    renderMarketTrendChart(detail.section, getActiveMarketChartRange(detail.id, detail.section));
  } else if (detail.kind === "push") {
    renderPushPreviewFrame(detail.section?.preview);
  }
}

function applyRoute(moduleId, detailId) {
  if (!viewState.modules.length) {
    return;
  }
  const module = viewState.modules.find((item) => item.id === moduleId) || viewState.modules[0];
  viewState.activeModuleId = module.id;
  // Keep module hydration on-demand so heavy modules do not block first paint.
  if (!module.loaded && !module.loading && !module.error) {
    loadModule(module.id, { resetContent: true });
  }
  renderModuleNav();
  if (detailId) {
    viewState.activeDetailByModule[module.id] = detailId;
  }
  renderModulePanel();
  document.body.classList.remove("sidebar-open");
  document.getElementById("sidebarToggle").setAttribute("aria-expanded", "false");
}

function navigate(moduleId, detailId) {
  const nextHash = `#${moduleId}${detailId ? `/${detailId}` : ""}`;
  if (window.location.hash === nextHash) {
    applyRoute(moduleId, detailId);
  } else {
    window.location.hash = nextHash;
  }
}

function replaceModule(nextModule) {
  const index = viewState.modules.findIndex((module) => module.id === nextModule.id);
  if (index === -1) {
    return;
  }
  const previous = viewState.modules[index];
  viewState.modules[index] = {
    ...previous,
    ...nextModule,
  };
}

function clearScheduledModuleReload(moduleId) {
  const timerId = viewState.refreshTimerByModule[moduleId];
  if (timerId) {
    window.clearTimeout(timerId);
    delete viewState.refreshTimerByModule[moduleId];
  }
}

function isPushWorkspaceInteracting() {
  if (viewState.activeModuleId !== "push") {
    return false;
  }
  const active = document.activeElement;
  return Boolean(active && typeof active.closest === "function" && active.closest("[data-push-workspace]"));
}

function scheduleModuleReload(moduleId, delayMs) {
  clearScheduledModuleReload(moduleId);
  viewState.refreshTimerByModule[moduleId] = window.setTimeout(() => {
    delete viewState.refreshTimerByModule[moduleId];
    if (moduleId === "push" && isPushWorkspaceInteracting()) {
      scheduleModuleReload(moduleId, delayMs);
      return;
    }
    loadModule(moduleId);
  }, Math.max(500, Number(delayMs) || 2000));
}

function setModuleLoading(moduleId, resetContent) {
  const module = viewState.modules.find((item) => item.id === moduleId);
  if (!module) {
    return;
  }
  clearScheduledModuleReload(moduleId);
  replaceModule({
    id: moduleId,
    loading: true,
    loaded: resetContent ? false : module.loaded,
    error: "",
    status: "loading",
    note: "后台加载中",
    details: resetContent ? [] : module.details,
  });
}

function setModuleError(moduleId, message) {
  clearScheduledModuleReload(moduleId);
  replaceModule({
    id: moduleId,
    loading: false,
    loaded: false,
    error: message,
    status: "unavailable",
    note: "加载失败",
    details: [],
  });
}

function applyModulePayload(payload) {
  if (!payload?.module?.id) {
    return;
  }
  const isLoadingModule = Boolean(payload.module.loading);
  if (payload.refresh_after_ms) {
    scheduleModuleReload(payload.module.id, payload.refresh_after_ms);
  } else if (payload.module.id !== "push") {
    clearScheduledModuleReload(payload.module.id);
  }
  replaceModule({
    ...payload.module,
    loading: isLoadingModule,
    loaded: !isLoadingModule,
    error: "",
  });
  if (!isLoadingModule) {
    updateGeneratedAt(payload.generated_at);
  }
  updateCoverageNote(payload.coverage_note || "");
  if (payload.news_mode || payload.upstream_service_status) {
    renderModeSwitch(payload);
  }
  renderTickerFromState();
  const route = parseHash();
  applyRoute(route.moduleId, route.detailId);
}

async function loadModule(moduleId, { resetContent = false, forceRefresh = false } = {}) {
  const requestId = (viewState.pendingRequestByModule[moduleId] || 0) + 1;
  viewState.pendingRequestByModule[moduleId] = requestId;
  setModuleLoading(moduleId, resetContent);
  renderModuleNav();
  if (viewState.activeModuleId === moduleId) {
    renderModulePanel();
  }
  if (moduleId === "news") {
    renderModeSwitch({
      news_mode: getRequestedNewsMode(),
      news_mode_options: NEWS_MODE_OPTIONS,
      upstream_service_status: { status: "loading", detail: "新闻模式状态加载中..." },
    });
  }

  try {
    let payload;
    try {
      const response = await fetch(buildModuleApiUrl(moduleId, { forceRefresh }), {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      payload = await response.json();
    } catch (moduleError) {
      const legacyPayload = await fetchLegacyDashboard({ forceRefresh });
      payload = modulePayloadFromLegacy(legacyPayload, moduleId);
      if (moduleId === "news" && !payload.upstream_service_status && legacyPayload.upstream_service_status) {
        payload.upstream_service_status = legacyPayload.upstream_service_status;
      }
    }
    if (viewState.pendingRequestByModule[moduleId] !== requestId) {
      return;
    }
    applyModulePayload(payload);
  } catch (error) {
    if (viewState.pendingRequestByModule[moduleId] !== requestId) {
      return;
    }
    setModuleError(moduleId, error.message);
    renderModuleNav();
    renderTickerFromState();
    if (viewState.activeModuleId === moduleId) {
      renderModulePanel();
    }
  }
}

function initSidebarToggle() {
  const button = document.getElementById("sidebarToggle");
  button.addEventListener("click", () => {
    const isOpen = document.body.classList.toggle("sidebar-open");
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
  document.addEventListener("click", (event) => {
    if (window.innerWidth > 980 || !document.body.classList.contains("sidebar-open")) {
      return;
    }
    const sidebar = document.getElementById("sidebar");
    if (sidebar.contains(event.target) || button.contains(event.target)) {
      return;
    }
    document.body.classList.remove("sidebar-open");
    button.setAttribute("aria-expanded", "false");
  });
}

function revealPanels() {
  document.querySelectorAll(".reveal").forEach((node, index) => {
    window.setTimeout(() => node.classList.add("visible"), 35 * index);
  });
}

function renderShell() {
  const route = parseHash();
  viewState.activeModuleId = route.moduleId;
  document.getElementById("generatedAt").textContent = "更新时间: 加载中...";
  updateCoverageNote("");
  renderModeSwitch({
    news_mode: getRequestedNewsMode(),
    news_mode_options: NEWS_MODE_OPTIONS,
    upstream_service_status: { status: "loading", detail: "新闻模式状态加载中..." },
  });
  renderTickerFromState();
  applyRoute(route.moduleId, route.detailId);
}

function loadAllModules() {
  for (const module of MODULE_CONFIGS) {
    // Regression guard: the push module builds a full preview and is intentionally
    // excluded from initial preloading. It must stay on-demand so the homepage
    // can render quickly while other modules hydrate asynchronously.
    if (module.id === "push") {
      replaceModule({
        id: "push",
        loading: false,
        loaded: false,
        error: "",
        status: "compatible",
        note: "按需加载",
        details: [],
      });
      continue;
    }
    loadModule(module.id);
  }
}

window.addEventListener("hashchange", () => {
  const route = parseHash();
  applyRoute(route.moduleId, route.detailId);
});

window.addEventListener("resize", () => {
  marketChartInstances.forEach((chart) => {
    try {
      chart.resize();
    } catch (error) {}
  });
});

applyTheme(getCurrentTheme(), { persist: false });
initThemeToggle();
initSidebarToggle();
renderShell();
revealPanels();
loadAllModules();
