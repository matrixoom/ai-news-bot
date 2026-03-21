const stateBadgeMap = {
  live: "正常",
  degraded: "降级",
  sample: "样例",
  unavailable: "不可用",
  unknown: "未知",
  compatible: "兼容",
};

const confidenceMap = {
  high: "高",
  medium: "中",
  low: "低",
};

const signalMap = {
  breakout: "突破",
  constructive: "偏强",
  neutral: "中性",
  pressured: "承压",
  unavailable: "不可用",
};

const trendMap = {
  up: "上行",
  down: "下行",
  flat: "持平",
  unavailable: "不可用",
};

const NEWS_MODE_LABELS = {
  hybrid: "Hybrid",
  api: "API",
  upstream: "Upstream",
};

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
  if (text.startsWith("http://") || text.startsWith("https://")) {
    return text;
  }
  return "";
}

function statusBadge(status) {
  const label = stateBadgeMap[status] || status;
  return `<span class="badge ${escapeHtml(status)}">${escapeHtml(label)}</span>`;
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
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState({}, "", nextUrl);
}

function buildApiUrl() {
  const params = new URLSearchParams();
  const newsMode = getRequestedNewsMode();
  if (newsMode !== "hybrid") {
    params.set("news_mode", newsMode);
  }
  const query = params.toString();
  return `/api/frontend/dashboard${query ? `?${query}` : ""}`;
}

function renderTicker(payload) {
  const root = document.getElementById("marketTicker");
  const market = payload.market_sections || [];
  const macro = payload.macro_sections || [];
  const lines = [];

  for (const section of market.slice(0, 5)) {
    lines.push({
      name: section.label,
      value: `${section.close_value} (${section.deviation_pct})`,
    });
  }
  for (const section of macro.slice(0, 4)) {
    lines.push({
      name: section.label,
      value: section.latest_value,
    });
  }

  if (!lines.length) {
    root.innerHTML = `<span class="ticker-empty">暂无行情数据</span>`;
    return;
  }

  root.innerHTML = `
    <div class="ticker-track">
      ${lines
        .map(
          (item) => `
            <span class="ticker-item">
              <span class="name">${escapeHtml(item.name)}</span>
              <span class="value">${escapeHtml(item.value)}</span>
            </span>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderModeSwitch(payload) {
  const root = document.getElementById("newsModeSwitch");
  const mode = payload.news_mode || getRequestedNewsMode();
  const options = payload.news_mode_options || [
    { value: "hybrid", label: "Hybrid" },
    { value: "api", label: "API" },
    { value: "upstream", label: "Upstream" },
  ];
  const upstreamStatus = payload.upstream_service_status || {
    status: "unknown",
    base_url: "",
    detail: "upstream status unavailable",
  };
  document.getElementById("newsModeTag").textContent = NEWS_MODE_LABELS[mode] || mode;

  root.innerHTML = `
    <div class="mode-switch-stack">
      <div class="mode-switch-group">
        ${options
          .map(
            (option) => `
              <button
                type="button"
                class="mode-switch-button ${option.value === mode ? "active" : ""}"
                data-news-mode="${escapeHtml(option.value)}"
              >
                ${escapeHtml(option.label)}
              </button>
            `,
          )
          .join("")}
      </div>
      <div class="mode-status mode-status-${escapeHtml(upstreamStatus.status)}">
        <span class="mode-status-label">Upstream</span>
        <span class="mode-status-text">${escapeHtml(upstreamStatus.status)}</span>
        <span class="mode-status-detail">${escapeHtml(upstreamStatus.detail)}</span>
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
      loadDashboard();
    });
  });
}

function renderHeader(payload) {
  document.getElementById("heroTitle").textContent = payload.title || "财经与政策情报终端";
  document.getElementById("heroSubtitle").textContent =
    payload.subtitle || "实时聚合宏观、市场、政策与热点新闻";
  document.getElementById("generatedAt").textContent = `更新时间: ${payload.generated_at || "-"}`;
  document.getElementById("coverageNote").textContent = payload.coverage_note || "暂无覆盖说明。";

  const highlights = document.getElementById("highlights");
  highlights.innerHTML = (payload.highlights || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");

  renderModeSwitch(payload);
}

function renderNews(sections) {
  const root = document.getElementById("newsGrid");
  if (!sections?.length) {
    root.innerHTML = `<article class="plain-card">暂无新闻数据</article>`;
    return;
  }

  root.innerHTML = sections
    .map((section) => {
      const rows = (section.items || [])
        .map((item) => {
          const url = normalizeNewsUrl(item.url);
          const title = url
            ? `<a class="headline-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">#${item.rank} ${escapeHtml(item.title)}</a>`
            : `<span class="headline-link disabled">#${item.rank} ${escapeHtml(item.title)}</span>`;
          return `
            <li>
              <p class="headline-title">${title}</p>
              <p class="headline-meta">${escapeHtml(item.source)} | ${escapeHtml(item.published_at)} | ${escapeHtml(item.tag)}</p>
            </li>
          `;
        })
        .join("");

      return `
        <article class="news-card">
          <div class="news-card-head">
            <h4>
              <span>${escapeHtml(section.title)}</span>
              ${statusBadge(section.status)}
            </h4>
            <span class="news-count">${escapeHtml(section.item_count || 0)} items</span>
          </div>
          <p class="card-meta">${escapeHtml(section.description)}</p>
          <ol class="headline-list headline-list-scroll">${rows || "<li class='placeholder'>暂无内容</li>"}</ol>
        </article>
      `;
    })
    .join("");
}

function buildLineChart(points, unit) {
  const valid = points.filter((point) => typeof point.value === "number");
  if (!valid.length) {
    return `<div class="chart-empty">暂无可绘制数据</div>`;
  }

  const width = 640;
  const height = 180;
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
  const path = valid
    .map((point, index) => `${index === 0 ? "M" : "L"} ${toX(index).toFixed(2)} ${toY(point.value).toFixed(2)}`)
    .join(" ");
  const area = `${path} L ${toX(valid.length - 1).toFixed(2)} ${toY(min).toFixed(2)} L ${toX(0).toFixed(2)} ${toY(min).toFixed(2)} Z`;
  const dots = valid
    .map((point, index) => `<circle cx="${toX(index).toFixed(2)}" cy="${toY(point.value).toFixed(2)}" r="2.2" fill="#8f3a17"></circle>`)
    .join("");
  const firstLabel = valid[0]?.period || "";
  const midLabel = valid[Math.floor((valid.length - 1) / 2)]?.period || "";
  const lastLabel = valid[valid.length - 1]?.period || "";

  const yAxis = [max, (max + min) / 2, min]
    .map((value, index) => {
      const y = top + (innerHeight * index) / 2;
      return `<text x="6" y="${(y + 3).toFixed(2)}" fill="#5f6a78" font-size="11">${escapeHtml(value.toFixed(2) + unit)}</text>`;
    })
    .join("");

  return `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <path d="${area}" fill="rgba(143, 58, 23, 0.10)"></path>
      <path d="${path}" fill="none" stroke="#8f3a17" stroke-width="2.4"></path>
      ${dots}
      ${yAxis}
      <text x="${left}" y="${height - 8}" text-anchor="start" fill="#5f6a78" font-size="11">${escapeHtml(firstLabel)}</text>
      <text x="${(left + innerWidth / 2).toFixed(2)}" y="${height - 8}" text-anchor="middle" fill="#5f6a78" font-size="11">${escapeHtml(midLabel)}</text>
      <text x="${(left + innerWidth).toFixed(2)}" y="${height - 8}" text-anchor="end" fill="#5f6a78" font-size="11">${escapeHtml(lastLabel)}</text>
    </svg>
  `;
}

function renderMacro(sections) {
  const root = document.getElementById("macroGrid");
  if (!sections?.length) {
    root.innerHTML = `<article class="plain-card">暂无宏观数据</article>`;
    return;
  }

  root.innerHTML = sections
    .map((section) => {
      const chart = buildLineChart(section.points || [], section.unit || "");
      return `
        <article class="metric-card">
          <h4>
            <span>${escapeHtml(section.label)}</span>
            ${statusBadge(section.status)}
          </h4>
          <div class="metric-row">
            <p class="metric-value">${escapeHtml(section.latest_value)}</p>
            <span class="metric-sub">趋势: ${escapeHtml(trendMap[section.trend] || section.trend)}</span>
          </div>
          <p class="card-meta">${escapeHtml(section.change_label)}</p>
          <div class="chart-wrap">${chart}</div>
          <p class="card-meta">来源: ${escapeHtml(section.source_label)} | 更新时间: ${escapeHtml(section.updated_at)}</p>
          <p class="card-meta">${escapeHtml(section.context)}</p>
        </article>
      `;
    })
    .join("");
}

function renderMarket(sections) {
  const root = document.getElementById("marketGrid");
  if (!sections?.length) {
    root.innerHTML = `<article class="plain-card">暂无市场模型数据</article>`;
    return;
  }

  root.innerHTML = sections
    .map(
      (section) => `
        <article class="plain-card">
          <h4>
            <span>${escapeHtml(section.label)}</span>
            ${statusBadge(section.status)}
          </h4>
          <p class="card-meta">收盘: ${escapeHtml(section.close_value)} | MA20: ${escapeHtml(section.ma20_value)}</p>
          <p class="card-meta">状态: ${escapeHtml(signalMap[section.signal] || section.signal)} | 偏离: ${escapeHtml(section.deviation_pct)}</p>
          <p class="card-meta">交易日: ${escapeHtml(section.trade_date)}</p>
          <p class="card-meta">${escapeHtml(section.explanation)}</p>
        </article>
      `,
    )
    .join("");
}

function renderEvents(sections) {
  const root = document.getElementById("eventsGrid");
  if (!sections?.length) {
    root.innerHTML = `<article class="plain-card">暂无事件展望数据</article>`;
    return;
  }

  root.innerHTML = sections
    .map((section) => {
      const rows = (section.items || [])
        .map(
          (item) => `
            <li>
              <p class="headline-title">${escapeHtml(item.title)}</p>
              <p class="headline-meta">${escapeHtml(item.time_window)} | 置信度: ${escapeHtml(confidenceMap[item.confidence] || item.confidence)} | ${escapeHtml(item.source)}</p>
            </li>
          `,
        )
        .join("");

      return `
        <article class="plain-card">
          <h4>
            <span>${escapeHtml(section.title)}</span>
            ${statusBadge(section.status)}
          </h4>
          <ol class="headline-list">${rows || "<li class='placeholder'>暂无事件</li>"}</ol>
        </article>
      `;
    })
    .join("");
}

function renderStatus(items) {
  const root = document.getElementById("statusList");
  if (!items?.length) {
    root.innerHTML = `<li class="status-item">暂无状态数据</li>`;
    return;
  }

  root.innerHTML = items
    .map(
      (item) => `
        <li class="status-item">
          <div class="status-title">
            <span>${escapeHtml(item.label)}</span>
            ${statusBadge(item.status)}
          </div>
          <p class="card-meta">${escapeHtml(item.detail)}</p>
        </li>
      `,
    )
    .join("");
}

function revealPanels() {
  document.querySelectorAll(".reveal").forEach((node, index) => {
    window.setTimeout(() => {
      node.classList.add("visible");
    }, 35 * index);
  });
}

async function loadDashboard() {
  try {
    const response = await fetch(buildApiUrl(), {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    renderHeader(payload);
    renderTicker(payload);
    renderNews(payload.news_sections);
    renderMacro(payload.macro_sections);
    renderMarket(payload.market_sections);
    renderEvents(payload.event_sections);
    renderStatus(payload.data_status);
    revealPanels();
  } catch (error) {
    document.getElementById("heroTitle").textContent = "页面加载失败";
    document.getElementById("heroSubtitle").textContent = `接口不可用: ${error.message}`;
    document.getElementById("coverageNote").textContent = "请检查后端服务、NewsNow 上游模式和网络依赖是否可用。";
    document.getElementById("marketTicker").innerHTML = `<span class="ticker-empty">行情条加载失败</span>`;
    document.getElementById("newsGrid").innerHTML = `<article class="plain-card">热点新闻加载失败</article>`;
    document.getElementById("macroGrid").innerHTML = `<article class="plain-card">宏观数据加载失败</article>`;
    document.getElementById("marketGrid").innerHTML = `<article class="plain-card">市场模型加载失败</article>`;
    document.getElementById("eventsGrid").innerHTML = `<article class="plain-card">事件展望加载失败</article>`;
    document.getElementById("statusList").innerHTML = `<li class="status-item">状态数据加载失败</li>`;
    renderModeSwitch({ news_mode: getRequestedNewsMode() });
    revealPanels();
  }
}

loadDashboard();
