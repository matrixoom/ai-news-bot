const stateBadgeMap = {
  live: "正常",
  degraded: "降级",
  sample: "样例",
  unavailable: "不可用",
  unknown: "未知",
  compatible: "兼容",
  loading: "加载中",
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
const NEWS_MODE_LABELS = { hybrid: "Hybrid", api: "API", upstream: "Upstream" };
const NEWS_MODE_OPTIONS = [
  { value: "hybrid", label: "Hybrid" },
  { value: "api", label: "API" },
  { value: "upstream", label: "Upstream" },
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
  pendingRequestByModule: {},
  refreshTimerByModule: {},
  generatedAt: "",
  coverageNote: "",
};

let legacyDashboardPromise = null;

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

function loadingSpinner(label = "加载中", inline = false) {
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

  if (moduleId === "macro") {
    const sections = payload.macro_sections || [];
    return {
      generated_at: payload.generated_at,
      module: {
        id: "macro",
        label: "宏观指标",
        note: `${sections.length} 个指标`,
        description: "宏观数据",
        status: groupStatus(sections),
        details: sections.map((section) => ({
          id: section.key,
          label: section.label,
          kind: "macro",
          note: section.latest_value,
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
        <span class="mode-status-text">${upstreamStatus.status === "loading" ? loadingSpinner("加载中", true) : escapeHtml(upstreamStatus.status)}</span>
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
  const macroModule = viewState.modules.find((module) => module.id === "macro");

  if (marketModule?.loaded && !marketModule.error) {
    for (const detail of marketModule.details.slice(0, 4)) {
      lines.push({
        name: detail.label,
        value: `${detail.section.close_value} / ${signalMap[detail.section.signal] || detail.section.signal}`,
      });
    }
  }

  if (macroModule?.loaded && !macroModule.error) {
    for (const detail of macroModule.details.slice(0, 2)) {
      lines.push({
        name: detail.label,
        value: detail.section.latest_value,
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

function renderMacroCard(section) {
  return `<article class="metric-card"><div class="card-head"><h4>${escapeHtml(section.label)}</h4>${statusBadge(section.status)}</div><div class="metric-row"><p class="metric-value">${escapeHtml(section.latest_value)}</p><span class="metric-sub">趋势: ${escapeHtml(trendMap[section.trend] || section.trend)}</span></div><p class="card-meta">${escapeHtml(section.change_label)}</p><div class="chart-wrap">${buildLineChart(section.points || [])}</div><p class="card-meta">来源: ${escapeHtml(section.source_label)} | 更新时间: ${escapeHtml(section.updated_at)}</p><p class="card-meta">${escapeHtml(section.context)}</p></article>`;
}

function renderTable(headers, rows, options = {}) {
  const classes = ["terminal-table"];
  if (options.compact) {
    classes.push("compact");
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
      ? `<a class="headline-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a>`
      : `<span class="headline-link disabled">${escapeHtml(item.title)}</span>`;
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
      { html: titleCell, className: "cell-grow" },
      { html: summaryCell, className: "cell-summary" },
    ];
  });
  return renderTable(
    [
      { label: "Rank", className: "cell-mono cell-rank" },
      { label: "Title", className: "cell-grow" },
      { label: "Summary", className: "cell-summary" },
    ],
    rows,
    {
      emptyText: "暂无新闻内容",
      columnsTemplate: "56px minmax(360px, 1.8fr) minmax(320px, 1.2fr)",
    },
  );
}

function renderEventsTable(items) {
  const rows = [];
  for (const section of items || []) {
    for (const item of section.items || []) {
      rows.push([
        { text: section.title, className: "cell-tight cell-cyan" },
        { text: item.title, className: "cell-grow" },
        { text: item.time_window, className: "cell-mono" },
        { text: confidenceMap[item.confidence] || item.confidence, className: "cell-tight" },
        { text: item.source, className: "cell-muted" },
      ]);
    }
  }
  return renderTable(
    [
      { label: "Window" },
      { label: "Event", className: "cell-grow" },
      { label: "Time", className: "cell-mono" },
      { label: "Confidence" },
      { label: "Source" },
    ],
    rows,
    { emptyText: "暂无事件展望数据" },
  );
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

function renderLoadingCard(message) {
  return `<article class="info-card loading-card"><div class="card-head"><h4>数据加载中</h4>${statusBadge("loading")}</div><div class="loading-card-copy">${loadingSpinner(message || "模块数据正在加载...", false)}</div></article>`;
}

function renderErrorCard(message, moduleId) {
  return `<article class="info-card"><div class="card-head"><h4>加载失败</h4>${statusBadge("unavailable")}</div><p class="detail-copy">${escapeHtml(message || "模块数据暂时不可用。")}</p><button type="button" class="retry-button" data-retry-module="${escapeHtml(moduleId)}">重新加载</button></article>`;
}

function renderModuleContent(module, detail) {
  if (detail.kind === "news") {
    return `<div class="content-stack"><article class="info-card"><div class="card-head"><h4>${escapeHtml(detail.section.title)}</h4>${statusBadge(detail.section.status)}</div><p class="detail-copy">${escapeHtml(detail.section.description)}</p></article><div class="table-scroll">${renderNewsTable(detail.section)}</div></div>`;
  }
  if (detail.kind === "macro") {
    return `<div class="content-stack">${renderMacroCard(detail.section)}${renderTable(
      [
        { label: "Field" },
        { label: "Value", className: "cell-grow" },
      ],
      [
        [{ text: "变化标签", className: "cell-tight cell-cyan" }, { text: detail.section.change_label, className: "cell-grow" }],
        [{ text: "来源", className: "cell-tight cell-cyan" }, { text: detail.section.source_label, className: "cell-grow" }],
        [{ text: "更新时间", className: "cell-tight cell-cyan" }, { text: detail.section.updated_at, className: "cell-grow cell-mono" }],
        [{ text: "频率", className: "cell-tight cell-cyan" }, { text: detail.section.frequency || "unknown", className: "cell-grow" }],
      ],
    )}</div>`;
  }
  if (detail.kind === "market") {
    return `<div class="content-stack">${renderTable(
      [
        { label: "Field" },
        { label: "Value", className: "cell-grow" },
      ],
      [
        [{ text: "收盘价", className: "cell-tight cell-cyan" }, { text: detail.section.close_value, className: "cell-grow cell-mono cell-accent" }],
        [{ text: "MA20", className: "cell-tight cell-cyan" }, { text: detail.section.ma20_value, className: "cell-grow cell-mono" }],
        [{ text: "模型信号", className: "cell-tight cell-cyan" }, { text: signalMap[detail.section.signal] || detail.section.signal, className: "cell-grow" }],
        [{ text: "偏离", className: "cell-tight cell-cyan" }, { text: detail.section.deviation_pct, className: "cell-grow cell-mono" }],
        [{ text: "交易日", className: "cell-tight cell-cyan" }, { text: detail.section.trade_date, className: "cell-grow cell-mono" }],
        [{ text: "说明", className: "cell-tight cell-cyan" }, { text: detail.section.explanation, className: "cell-grow cell-muted" }],
      ],
    )}${renderMarketSummaryTable(module, detail)}</div>`;
  }
  if (detail.kind === "events") {
    return `<div class="content-stack"><article class="info-card"><div class="card-head"><h4>${escapeHtml(detail.section.title)}</h4>${statusBadge(detail.section.status)}</div><p class="detail-copy">当前窗口收录 ${(detail.section.items || []).length} 条事件。</p></article>${renderEventsTable([detail.section])}</div>`;
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
}

function renderModulePanel() {
  const module = currentModule();
  const detail = currentDetail(module);
  document.getElementById("activeModuleEyebrow").textContent = module.label;
  document.getElementById("activeModuleDescription").textContent = module.description;
  document.getElementById("moduleStatus").innerHTML = `${statusBadge(module.loading ? "loading" : module.error ? "unavailable" : module.status)}<span class="tab-note">${escapeHtml(module.note || "")}</span><button type="button" class="module-refresh-button" data-refresh-module="${escapeHtml(module.id)}">手动刷新</button>`;

  if (module.loading && !module.loaded) {
    document.getElementById("activeModuleTitle").textContent = `${module.label} / 加载中`;
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
  document.getElementById("activeModuleTitle").textContent = detail.label;
  document.getElementById("detailTabs").innerHTML =
    module.details.length > 1
      ? module.details
          .map(
            (item) => `<button type="button" class="detail-tab ${item.id === detail.id ? "active" : ""}" data-detail-id="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`,
          )
          .join("")
      : "";
  document.getElementById("contentStage").innerHTML = renderModuleContent(module, detail);
  bindContentActions();
}

function applyRoute(moduleId, detailId) {
  if (!viewState.modules.length) {
    return;
  }
  const module = viewState.modules.find((item) => item.id === moduleId) || viewState.modules[0];
  viewState.activeModuleId = module.id;
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

function scheduleModuleReload(moduleId, delayMs) {
  clearScheduledModuleReload(moduleId);
  viewState.refreshTimerByModule[moduleId] = window.setTimeout(() => {
    delete viewState.refreshTimerByModule[moduleId];
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
  if (isLoadingModule && payload.refresh_after_ms) {
    scheduleModuleReload(payload.module.id, payload.refresh_after_ms);
  } else {
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
  document.getElementById("generatedAt").textContent = "更新时间: 加载中";
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
    loadModule(module.id);
  }
}

window.addEventListener("hashchange", () => {
  const route = parseHash();
  applyRoute(route.moduleId, route.detailId);
});

applyTheme(getCurrentTheme(), { persist: false });
initThemeToggle();
initSidebarToggle();
renderShell();
revealPanels();
loadAllModules();
