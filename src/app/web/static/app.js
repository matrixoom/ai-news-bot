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

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusBadge(status) {
  const label = stateBadgeMap[status] || status;
  return `<span class="badge ${escapeHtml(status)}">${escapeHtml(label)}</span>`;
}

function renderNews(sections) {
  const root = document.getElementById("newsGrid");
  if (!sections?.length) {
    root.innerHTML = `<div class="plain-card">暂无新闻数据</div>`;
    return;
  }
  root.innerHTML = sections
    .map((section) => {
      const items = section.items
        .map((item) => {
          const placeholder = item.is_placeholder ? "placeholder" : "";
          return `
            <li class="${placeholder}">
              <span class="news-title">#${item.rank} ${escapeHtml(item.title)}</span>
              <span class="news-meta">${escapeHtml(item.source)} | ${escapeHtml(item.published_at)} | ${escapeHtml(item.tag)}</span>
            </li>
          `;
        })
        .join("");
      return `
        <article class="news-card">
          <h4>${escapeHtml(section.title)} ${statusBadge(section.status)}</h4>
          <p class="muted">${escapeHtml(section.description)}</p>
          <ul class="news-list">${items}</ul>
        </article>
      `;
    })
    .join("");
}

function buildLineChart(points, unit) {
  const valid = points.filter((point) => typeof point.value === "number");
  if (!valid.length) {
    return `<div class="chart-empty">暂无可视化数据</div>`;
  }

  const width = 640;
  const height = 190;
  const left = 46;
  const right = 20;
  const top = 16;
  const bottom = 30;
  const usableWidth = width - left - right;
  const usableHeight = height - top - bottom;

  let min = Math.min(...valid.map((point) => point.value));
  let max = Math.max(...valid.map((point) => point.value));
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const pad = (max - min) * 0.12;
  min -= pad;
  max += pad;

  const toX = (index) => left + (usableWidth * index) / Math.max(points.length - 1, 1);
  const toY = (value) => top + ((max - value) / (max - min)) * usableHeight;

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${toX(index).toFixed(2)} ${toY(point.value).toFixed(2)}`)
    .join(" ");

  const dots = points
    .map((point, index) => {
      const cx = toX(index).toFixed(2);
      const cy = toY(point.value).toFixed(2);
      return `<circle cx="${cx}" cy="${cy}" r="2.2" fill="#9a3e16"></circle>`;
    })
    .join("");

  const labels = [
    points[0]?.period || "",
    points[Math.floor((points.length - 1) / 2)]?.period || "",
    points[points.length - 1]?.period || "",
  ];
  const labelX = [left, left + usableWidth / 2, left + usableWidth];
  const xLabels = labels
    .map(
      (label, index) =>
        `<text x="${labelX[index].toFixed(2)}" y="${(height - 8).toFixed(2)}" text-anchor="${index === 0 ? "start" : index === 2 ? "end" : "middle"}" fill="#5a6776" font-size="11">${escapeHtml(label)}</text>`,
    )
    .join("");

  const yLabels = [max, (max + min) / 2, min]
    .map((value, index) => {
      const y = top + (usableHeight * index) / 2;
      return `<text x="6" y="${(y + 3).toFixed(2)}" fill="#5a6776" font-size="11">${escapeHtml(value.toFixed(2) + unit)}</text>`;
    })
    .join("");

  return `
    <svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <path d="${linePath}" fill="none" stroke="#9a3e16" stroke-width="2.4"></path>
      ${dots}
      ${xLabels}
      ${yLabels}
    </svg>
  `;
}

function renderMacro(sections) {
  const root = document.getElementById("macroGrid");
  if (!sections?.length) {
    root.innerHTML = `<div class="plain-card">暂无宏观数据</div>`;
    return;
  }

  root.innerHTML = sections
    .map((section) => {
      const chart = buildLineChart(section.points || [], section.unit || "");
      return `
        <article class="metric-card">
          <h4>${escapeHtml(section.label)} ${statusBadge(section.status)}</h4>
          <div class="metric-top">
            <p class="metric-value">${escapeHtml(section.latest_value)}</p>
            <span class="muted">${escapeHtml(trendMap[section.trend] || section.trend)}</span>
          </div>
          <p class="muted">${escapeHtml(section.change_label)}</p>
          <div class="chart-wrap">${chart}</div>
          <p class="muted">来源：${escapeHtml(section.source_label)} | 更新时间：${escapeHtml(section.updated_at)}</p>
          <p class="muted">${escapeHtml(section.context)}</p>
        </article>
      `;
    })
    .join("");
}

function renderMarket(sections) {
  const root = document.getElementById("marketGrid");
  if (!sections?.length) {
    root.innerHTML = `<div class="plain-card">暂无市场模型数据</div>`;
    return;
  }
  root.innerHTML = sections
    .map(
      (section) => `
        <article class="plain-card">
          <h4>${escapeHtml(section.label)} ${statusBadge(section.status)}</h4>
          <p>收盘：${escapeHtml(section.close_value)} | MA20：${escapeHtml(section.ma20_value)}</p>
          <p>状态：${escapeHtml(signalMap[section.signal] || section.signal)} | 偏离：${escapeHtml(section.deviation_pct)}</p>
          <p class="muted">交易日：${escapeHtml(section.trade_date)} | 来源：${escapeHtml(section.source_label)}</p>
          <p class="muted">${escapeHtml(section.explanation)}</p>
        </article>
      `,
    )
    .join("");
}

function renderEvents(sections) {
  const root = document.getElementById("eventsGrid");
  if (!sections?.length) {
    root.innerHTML = `<div class="plain-card">暂无事件展望数据</div>`;
    return;
  }
  root.innerHTML = sections
    .map((section) => {
      const items = (section.items || [])
        .map(
          (item) => `
            <li>
              <strong>${escapeHtml(item.title)}</strong>
              <span class="muted">${escapeHtml(item.time_window)} | 置信度：${escapeHtml(confidenceMap[item.confidence] || item.confidence)} | ${escapeHtml(item.source)}</span>
            </li>
          `,
        )
        .join("");
      return `
        <article class="plain-card">
          <h4>${escapeHtml(section.title)} ${statusBadge(section.status)}</h4>
          <ul class="news-list">${items || "<li class='muted'>暂无事件</li>"}</ul>
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
          <div>${escapeHtml(item.label)} ${statusBadge(item.status)}</div>
          <div class="muted">${escapeHtml(item.detail)}</div>
        </li>
      `,
    )
    .join("");
}

function renderHeader(payload) {
  document.getElementById("heroTitle").textContent = payload.title || "仪表盘";
  document.getElementById("heroSubtitle").textContent = payload.subtitle || "";
  document.getElementById("generatedAt").textContent = `更新时间：${payload.generated_at || "-"}`;
  document.getElementById("coverageNote").textContent = payload.coverage_note || "无覆盖说明";
  const highlights = document.getElementById("highlights");
  highlights.innerHTML = (payload.highlights || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("");
}

async function loadDashboard() {
  try {
    const response = await fetch("/api/frontend/dashboard", {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    renderHeader(payload);
    renderNews(payload.news_sections);
    renderMacro(payload.macro_sections);
    renderMarket(payload.market_sections);
    renderEvents(payload.event_sections);
    renderStatus(payload.data_status);
  } catch (error) {
    document.getElementById("heroTitle").textContent = "加载失败";
    document.getElementById("heroSubtitle").textContent = `后端接口暂不可用：${error.message}`;
    document.getElementById("coverageNote").textContent = "请检查服务日志和数据源依赖。";
    document.getElementById("newsGrid").innerHTML = `<div class="plain-card">热点新闻加载失败</div>`;
    document.getElementById("macroGrid").innerHTML = `<div class="plain-card">宏观趋势加载失败</div>`;
    document.getElementById("marketGrid").innerHTML = `<div class="plain-card">市场模型加载失败</div>`;
    document.getElementById("eventsGrid").innerHTML = `<div class="plain-card">事件展望加载失败</div>`;
    document.getElementById("statusList").innerHTML = `<li class="status-item">状态数据加载失败</li>`;
  }
}

loadDashboard();
