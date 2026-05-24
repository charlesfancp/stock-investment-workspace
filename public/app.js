const DEFAULT_CODE = "02510";
const AUTO_REFRESH_MS = 10 * 60 * 1000;

const els = {
  form: document.querySelector("#stockForm"),
  codeInput: document.querySelector("#stockCode"),
  stockOptions: document.querySelector("#stockOptions"),
  stockAlias: document.querySelector("#stockAlias"),
  companyName: document.querySelector("#companyName"),
  stockMeta: document.querySelector("#stockMeta"),
  lastUpdated: document.querySelector("#lastUpdated"),
  price: document.querySelector("#price"),
  currency: document.querySelector("#currency"),
  priceMove: document.querySelector("#priceMove"),
  dayRange: document.querySelector("#dayRange"),
  volume: document.querySelector("#volume"),
  turnover: document.querySelector("#turnover"),
  marketTime: document.querySelector("#marketTime"),
  signals: document.querySelector("#signals"),
  signalBadge: document.querySelector("#signalBadge"),
  anomalySummary: document.querySelector("#anomalySummary"),
  anomalyBadge: document.querySelector("#anomalyBadge"),
  anomalyPoints: document.querySelector("#anomalyPoints"),
  intradayChart: document.querySelector("#intradayChart"),
  intradayCaption: document.querySelector("#intradayCaption"),
  chart: document.querySelector("#priceChart"),
  chartCaption: document.querySelector("#chartCaption"),
  announcements: document.querySelector("#announcements"),
  announcementCount: document.querySelector("#announcementCount"),
  news: document.querySelector("#news"),
  research: document.querySelector("#research"),
  forumLinks: document.querySelector("#forumLinks"),
  researchSearchLink: document.querySelector("#researchSearchLink"),
  disclosureLink: document.querySelector("#disclosureLink"),
  newsSearchLink: document.querySelector("#newsSearchLink"),
  rangeButtons: [...document.querySelectorAll("[data-range]")],
};

let state = {
  code: DEFAULT_CODE,
  query: DEFAULT_CODE,
  stock: null,
  quote: null,
  announcements: null,
  news: null,
  research: null,
  range: 365,
};
let refreshInFlight = false;
let lastRefreshStartedAt = 0;

function h(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatNumber(value, digits = 2) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatCompact(value) {
  if (!Number.isFinite(value)) return "--";
  return new Intl.NumberFormat("zh-CN", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatMoney(value, currency = "HKD") {
  if (!Number.isFinite(value)) return "--";
  return `${formatCompact(value)} ${currency}`;
}

function formatPercent(value) {
  if (!Number.isFinite(value)) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, 2)}%`;
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Hong_Kong",
  }).format(date);
}

function formatNewsDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function shortText(value = "", max = 64) {
  const text = String(value)
    .replace(/\s+/g, " ")
    .replace(/\s+-\s+(AASTOCKS\.com|Investing\.com.*|FX168|信報網站|智通財經|智通财经).*$/i, "")
    .trim();
  return text.length > max ? `${text.slice(0, max - 3)}...` : text;
}

function cleanHeadline(value = "", max = 64) {
  return shortText(
    String(value)
      .replace(/德翔海運/g, "德翔海运")
      .replace(/目標價/g, "目标价")
      .replace(/現價/g, "现价")
      .replace(/港幣/g, "港币"),
    max,
  );
}

function findByText(items = [], pattern) {
  return items.find((item) =>
    pattern.test(`${item.title || ""} ${item.category || ""} ${item.source || ""}`),
  );
}

function normalizeCode(value) {
  return String(value || DEFAULT_CODE).replace(/\D/g, "").padStart(5, "0");
}

async function loadJson(path, code) {
  const response = await fetch(`${path}?code=${encodeURIComponent(code)}`, {
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "读取失败");
  }
  return data;
}

function setStatus(message) {
  els.lastUpdated.textContent = message;
}

function setMoveClass(element, value) {
  element.classList.remove("up", "down", "neutral", "watch");
  if (!Number.isFinite(value) || value === 0) {
    element.classList.add("neutral");
  } else {
    element.classList.add(value > 0 ? "up" : "down");
  }
}

function updateQuote(quote) {
  els.price.textContent = formatNumber(quote.price, 2);
  els.currency.textContent = quote.currency || "HKD";
  const move =
    Number.isFinite(quote.change) && Number.isFinite(quote.changePercent)
      ? `${quote.change > 0 ? "+" : ""}${formatNumber(quote.change, 2)} (${formatPercent(
          quote.changePercent,
        )})`
      : "变化未提供";
  els.priceMove.textContent = move;
  setMoveClass(els.priceMove, quote.change);
  els.dayRange.textContent = `${formatNumber(quote.dayLow, 2)} - ${formatNumber(
    quote.dayHigh,
    2,
  )}`;
  els.volume.textContent = formatCompact(quote.volume);
  els.turnover.textContent = formatMoney(quote.turnover, quote.currency || "HKD");
  els.marketTime.textContent = formatDateTime(quote.marketTime);
  updateStockHeader();
}

function updateStockHeader() {
  const stock = state.stock;
  const quote = state.quote;
  const displayName = stock?.displayName || (quote?.code === DEFAULT_CODE ? "德翔海运" : "");
  const shortName = stock?.shortName || "";
  const exchange = quote?.exchange || "HKEX";
  const source = quote?.source || "Yahoo Finance";
  const nameParts = [quote?.code || state.code, displayName, shortName].filter(Boolean);
  els.stockMeta.textContent = `${nameParts.join(" · ")} · ${exchange} · ${source}`;
  els.stockAlias.textContent = displayName
    ? `简称：${displayName}${shortName && shortName !== displayName ? ` / ${shortName}` : ""}`
    : "可输入代码或英文简称搜索";
}

function latestRows(days) {
  const history = state.quote?.history || [];
  return history.slice(Math.max(0, history.length - days));
}

function average(values) {
  const valid = values.filter(Number.isFinite);
  if (!valid.length) return null;
  return valid.reduce((sum, value) => sum + value, 0) / valid.length;
}

function latestTradingRows(days, offset = 0) {
  const history = state.quote?.history || [];
  const end = Math.max(0, history.length - offset);
  return history.slice(Math.max(0, end - days), end);
}

function setupCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(320, Math.floor(rect.width * ratio));
  canvas.height = Math.max(160, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  return { ctx, width: rect.width, height: rect.height };
}

function clearChart(ctx, width, height) {
  const background = ctx.createLinearGradient(0, 0, 0, height);
  background.addColorStop(0, "#ffffff");
  background.addColorStop(1, "#fafbf8");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, width, height);
}

function paddedRange(values, paddingRatio = 0.08) {
  const valid = values.filter(Number.isFinite);
  if (!valid.length) return { min: 0, max: 1, spread: 1 };
  const rawMin = Math.min(...valid);
  const rawMax = Math.max(...valid);
  const rawSpread = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.02, 0.01);
  const padding = rawSpread * paddingRatio;
  const min = rawMin - padding;
  const max = rawMax + padding;
  return { min, max, spread: max - min || 1 };
}

function drawHorizontalGrid(ctx, { left, right, top, bottom, min, max, steps = 3 }) {
  const height = bottom - top;
  ctx.save();
  ctx.strokeStyle = "#e6ece7";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#6a776f";
  ctx.font = "11px Inter, Arial";
  for (let i = 0; i <= steps; i += 1) {
    const y = top + (height / steps) * i;
    const value = max - ((max - min) / steps) * i;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(right, y);
    ctx.stroke();
    ctx.fillText(formatNumber(value, 2), right + 8, y + 4);
  }
  ctx.restore();
}

function drawLine(ctx, points, color, width = 2) {
  if (points.length < 2) return;
  ctx.save();
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
      return;
    }
    ctx.lineTo(point.x, point.y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.stroke();
  ctx.restore();
}

function drawArea(ctx, points, bottom, color) {
  if (points.length < 2) return;
  const gradient = ctx.createLinearGradient(0, points[0].y, 0, bottom);
  gradient.addColorStop(0, color);
  gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
  ctx.save();
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
      return;
    }
    ctx.lineTo(point.x, point.y);
  });
  ctx.lineTo(points.at(-1).x, bottom);
  ctx.lineTo(points[0].x, bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();
  ctx.restore();
}

function drawEndMarker(ctx, point, label, color, width) {
  ctx.save();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(point.x, point.y, 3.2, 0, Math.PI * 2);
  ctx.fill();

  ctx.font = "12px Inter, Arial";
  const textWidth = ctx.measureText(label).width;
  const x = Math.min(Math.max(point.x + 8, 8), width - textWidth - 12);
  const y = Math.max(18, point.y - 10);
  ctx.fillStyle = "#17201c";
  ctx.fillText(label, x, y);
  ctx.restore();
}

function renderIntradayChart() {
  const { ctx, width, height } = setupCanvas(els.intradayChart);
  const rows = (state.quote?.intraday || []).filter((row) => Number.isFinite(row.close));
  clearChart(ctx, width, height);
  if (rows.length < 2) {
    ctx.fillStyle = "#65756e";
    ctx.font = "13px Arial";
    ctx.fillText("暂无当日分钟走势", 16, 32);
    els.intradayCaption.textContent = "行情源暂未提供当日分钟走势";
    return;
  }

  const padding = { top: 14, right: 48, bottom: 22, left: 10 };
  const left = padding.left;
  const right = width - padding.right;
  const top = padding.top;
  const bottom = height - padding.bottom;
  const plotWidth = right - left;
  const plotHeight = bottom - top;
  const closes = rows.map((row) => row.close);
  const { min, max, spread } = paddedRange(closes, 0.06);
  const xFor = (index) => left + (index / (rows.length - 1)) * plotWidth;
  const yFor = (value) => top + (1 - (value - min) / spread) * plotHeight;
  const previousClose = state.quote?.previousClose;
  const points = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.close), value: row.close }));

  drawHorizontalGrid(ctx, { left, right, top, bottom, min, max, steps: 3 });

  if (Number.isFinite(previousClose)) {
    const y = yFor(previousClose);
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "#aebbb4";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(right, y);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  const lastClose = rows.at(-1).close;
  const basis = Number.isFinite(previousClose) ? previousClose : rows[0].close;
  const rising = lastClose >= basis;
  const lineColor = rising ? "#006b5b" : "#b23b34";
  drawArea(ctx, points, bottom, rising ? "rgba(0, 107, 91, 0.16)" : "rgba(178, 59, 52, 0.14)");
  drawLine(ctx, points, lineColor, 2.2);
  drawEndMarker(ctx, points.at(-1), formatNumber(lastClose, 2), lineColor, width);

  const start = formatDateTime(rows[0].time);
  const end = formatDateTime(rows.at(-1).time);
  els.intradayCaption.textContent = `${start} - ${end} · 成交额 ${formatMoney(
    state.quote?.turnover,
    state.quote?.currency || "HKD",
  )}`;
}

function renderChart() {
  const { ctx, width, height } = setupCanvas(els.chart);

  const rows = latestRows(state.range).filter((row) => Number.isFinite(row.close));
  clearChart(ctx, width, height);
  if (rows.length < 2) {
    ctx.fillStyle = "#65756e";
    ctx.font = "14px Arial";
    ctx.fillText("暂无足够历史价格绘制趋势图", 24, 40);
    return;
  }

  const padding = { top: 18, right: 58, bottom: 30, left: 46 };
  const left = padding.left;
  const right = width - padding.right;
  const volumeHeight = Math.min(72, Math.max(44, height * 0.18));
  const volumeGap = 14;
  const volumeBase = height - padding.bottom;
  const priceBottom = volumeBase - volumeHeight - volumeGap;
  const top = padding.top;
  const plotWidth = right - left;
  const plotHeight = priceBottom - top;
  const closes = rows.map((row) => row.close);
  const volumes = rows.map((row) => row.volume).filter(Number.isFinite);
  const { min, max, spread } = paddedRange(closes, 0.08);
  const maxVolume = Math.max(...volumes, 1);
  const yFor = (value) => top + (1 - (value - min) / spread) * plotHeight;
  const xFor = (index) => left + (index / (rows.length - 1)) * plotWidth;
  const points = rows.map((row, index) => ({ x: xFor(index), y: yFor(row.close), value: row.close }));

  drawHorizontalGrid(ctx, { left, right, top, bottom: priceBottom, min, max, steps: 3 });

  const barSlot = plotWidth / rows.length;
  const barWidth = Math.max(1, Math.min(8, barSlot * 0.72));
  rows.forEach((row, index) => {
    if (!Number.isFinite(row.volume)) return;
    const x = xFor(index) - barWidth / 2;
    const barHeight = Math.max(1, (row.volume / maxVolume) * volumeHeight);
    const previousClose = index > 0 ? rows[index - 1].close : row.open;
    const upBar = Number.isFinite(previousClose) ? row.close >= previousClose : true;
    ctx.fillStyle = upBar ? "rgba(0, 107, 91, 0.2)" : "rgba(178, 59, 52, 0.18)";
    ctx.fillRect(x, volumeBase - barHeight, barWidth, barHeight);
  });
  ctx.strokeStyle = "#e6ece7";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(left, volumeBase);
  ctx.lineTo(right, volumeBase);
  ctx.stroke();
  ctx.fillStyle = "#65756e";
  ctx.font = "11px Inter, Arial";
  ctx.fillText("成交量", left, volumeBase - volumeHeight - 6);
  ctx.fillText(formatCompact(maxVolume), right + 8, volumeBase - volumeHeight + 4);

  const rising = rows.at(-1).close >= rows[0].close;
  const lineColor = rising ? "#006b5b" : "#b23b34";
  drawArea(ctx, points, priceBottom, rising ? "rgba(0, 107, 91, 0.16)" : "rgba(178, 59, 52, 0.13)");
  drawLine(ctx, points, lineColor, 2.1);

  const first = rows[0];
  const last = rows.at(-1);
  ctx.fillStyle = "#65756e";
  ctx.font = "11px Inter, Arial";
  ctx.fillText(first.date, left, height - 10);
  const lastLabel = last.date;
  ctx.fillText(lastLabel, right - ctx.measureText(lastLabel).width, height - 10);
  drawEndMarker(ctx, points.at(-1), `${formatNumber(last.close, 2)} ${state.quote?.currency || "HKD"}`, lineColor, width);

  const latestVolume = Number.isFinite(state.quote?.volume) ? state.quote.volume : last.volume;
  const rangeName = state.range === 365 ? "1年" : state.range === 180 ? "6月" : "60日";
  els.chartCaption.textContent = `${rangeName} · ${rows[0].date} 至 ${last.date} · 最新量 ${formatCompact(
    latestVolume,
  )}`;
}

function renderList(container, items, emptyText, mapper) {
  if (!items?.length) {
    container.innerHTML = `<div class="empty">${emptyText}</div>`;
    return;
  }
  container.innerHTML = items.map(mapper).join("");
}

function renderAnnouncements(data) {
  els.announcementCount.textContent = `HKEX 最新5条中文公告，共 ${data.total || data.items.length} 条`;
  els.disclosureLink.href = data.disclosureUrl;
  els.companyName.textContent = data.stock?.displayName || data.stock?.shortName || "单股面板";
  renderList(
    els.announcements,
    data.items.slice(0, 5),
    "暂时没有读到 HKEX 公告。",
    (item) => `
      <article class="news-item">
        <a href="${h(item.url)}" target="_blank" rel="noreferrer">${h(item.title)}</a>
        <div class="category">${h(item.category)}</div>
        <div class="item-meta">
          <span>${h(item.releaseTime)}</span>
          <span>${h(item.fileSize || "")}</span>
        </div>
      </article>
    `,
  );
}

function renderNews(data) {
  els.newsSearchLink.href = data.searchUrl;
  renderList(
    els.news,
    data.items.slice(0, 5),
    "暂时没有读到相关新闻。",
    (item) => `
      <article class="news-item">
        <a href="${h(item.url)}" target="_blank" rel="noreferrer">${h(item.title)}</a>
        <div class="item-meta">
          <span>${h(formatNewsDate(item.publishedAt))}</span>
          <span>${h(item.source)}</span>
        </div>
      </article>
    `,
  );
}

function forumUrl(data, source, fallback) {
  return data?.forumLinks?.find((item) => item.source === source)?.url || fallback;
}

function buildCommunityGroups(data) {
  const code = state.code || DEFAULT_CODE;
  const numeric = Number(code);
  const quote = state.quote || {};
  const announcements = state.announcements?.items || [];
  const news = state.news?.items || [];
  const research = data?.items || [];
  const closes = quote.history?.map((row) => row.close).filter(Number.isFinite) || [];
  const lastClose = closes.at(-1);
  const ma20 = average(closes.slice(-20));
  const ma60 = average(closes.slice(-60));
  const rows20 = latestRows(20);
  const high20 = Math.max(...rows20.map((row) => row.high).filter(Number.isFinite));
  const low20 = Math.min(...rows20.map((row) => row.low).filter(Number.isFinite));
  const pct20 = ma20 ? ((lastClose - ma20) / ma20) * 100 : null;
  const pct60 = ma60 ? ((lastClose - ma60) / ma60) * 100 : null;
  const pctFromHigh = quote.fiftyTwoWeekHigh
    ? ((quote.price - quote.fiftyTwoWeekHigh) / quote.fiftyTwoWeekHigh) * 100
    : null;
  const researchLead =
    findByText(research, /摩通|大行|目标价|目標價|评级|評級|券商|分析師|分析员/i) ||
    research[0];
  const revenueNews = findByText(news, /收入|營運|运营|業績|业绩|updates|首三月|三月/i);
  const transaction =
    findByText(
      announcements,
      /關連交易|关连交易|connected transaction|須予披露|须予披露|discloseable|租賃|租赁|船舶|vessel|container/i,
    ) || announcements[0];

  const moveText = Number.isFinite(quote.changePercent)
    ? `今日${quote.changePercent >= 0 ? "涨" : "跌"}${formatNumber(
        Math.abs(quote.changePercent),
        2,
      )}%`
    : "短线涨跌待确认";
  const turnoverText = Number.isFinite(quote.turnover)
    ? `成交额${formatMoney(quote.turnover, quote.currency || "HKD")}`
    : "成交额待确认";
  const researchText = researchLead
    ? cleanHeadline(researchLead.title, 34)
    : "近3个月暂无明确大行目标价";
  const revenueText = revenueNews
    ? cleanHeadline(revenueNews.title, 34)
    : "收入、运价和装载率仍是基本面焦点";
  const transactionText = transaction
    ? cleanHeadline(transaction.title, 34)
    : "继续盯关联交易和船队变化";
  const range20 =
    Number.isFinite(low20) && Number.isFinite(high20)
      ? `${formatNumber(low20, 2)}-${formatNumber(high20, 2)}`
      : "--";
  const ma20Text = Number.isFinite(pct20)
    ? `${lastClose >= ma20 ? "站上" : "低于"}20日线${formatPercent(pct20)}`
    : "20日线待确认";
  const ma60Text = Number.isFinite(pct60)
    ? `${lastClose >= ma60 ? "站上" : "低于"}60日线${formatPercent(pct60)}`
    : "";
  const drawdownText = Number.isFinite(pctFromHigh)
    ? `距52周高点${formatPercent(pctFromHigh)}`
    : "52周位置待确认";

  return [
    {
      source: "雪球",
      url: forumUrl(data, "雪球", `https://xueqiu.com/S/HK${code}`),
      points: [
        `买入理由：${researchText}。`,
        `分歧点：${revenueText}。`,
        `估值点：${drawdownText}，看分红和运价周期。`,
      ],
    },
    {
      source: "富途牛牛",
      url: forumUrl(data, "富途牛牛", `https://www.futunn.com/stock/${code}-HK`),
      points: [
        `情绪：${moveText}，${turnoverText}。`,
        `公告：${transactionText}。`,
        `等待点：${ma20Text}${ma60Text ? `，${ma60Text}` : ""}。`,
      ],
    },
    {
      source: "TradingView",
      url: forumUrl(data, "TradingView", `https://www.tradingview.com/symbols/HKEX-${numeric}/ideas/`),
      points: [
        `趋势：${ma20Text}${ma60Text ? `，${ma60Text}` : ""}。`,
        `区间：20日${range20}，跌破低位偏防守。`,
        `位置：${drawdownText}，反弹要有量能或基本面配合。`,
      ],
    },
  ];
}

function renderResearch(data) {
  els.researchSearchLink.href = data.searchUrl;
  renderList(
    els.research,
    data.items.slice(0, 1),
    "近3个月暂未读到明确的券商研报、评级或目标价新闻。",
    (item) => `
      <article class="doc-item">
        <a href="${h(item.url)}" target="_blank" rel="noreferrer">${h(item.title)}</a>
        <div class="item-meta">
          <span>${h(formatNewsDate(item.publishedAt))}</span>
          <span>${h(item.source)}</span>
        </div>
      </article>
    `,
  );
  const groups = buildCommunityGroups(data);
  els.forumLinks.innerHTML = `
    <p class="forum-title">社区高关注观点（前三个平台，各3条）</p>
    <div class="community-grid">
    ${groups
      .map(
        (group) => `
          <section class="community-group">
            <a class="community-source" href="${h(group.url)}" target="_blank" rel="noreferrer">${h(
              group.source,
            )}</a>
            <ol>
              ${group.points.map((point) => `<li class="community-point">${h(point)}</li>`).join("")}
            </ol>
          </section>
        `,
      )
      .join("")}
    </div>
  `;
}

function latestNewsTime(items = []) {
  const timestamps = items
    .map((item) => new Date(item.publishedAt || item.releaseTime).getTime())
    .filter(Number.isFinite);
  return timestamps.length ? Math.max(...timestamps) : null;
}

function hasFreshItem(items = [], hours = 36) {
  const latest = latestNewsTime(items);
  return latest ? Date.now() - latest <= hours * 60 * 60 * 1000 : false;
}

function buildAnomaly() {
  const quote = state.quote;
  const history = quote?.history || [];
  const last = history.at(-1);
  const previous = history.at(-2);
  if (!quote || !last || !previous) {
    return {
      badge: "待判断",
      tone: "neutral",
      summary: "历史数据不足，先看最新公告和成交量。",
      points: [
        ["价格变化", "暂无足够交易日"],
        ["成交量", "暂无均量对比"],
        ["消息面", "等待新闻与公告"],
        ["结论", "先不判断异动性质"],
      ],
    };
  }

  const closes = history.map((row) => row.close).filter(Number.isFinite);
  const previousVolumes = latestTradingRows(20, 1).map((row) => row.volume).filter(Number.isFinite);
  const ma20 = average(closes.slice(-20));
  const ma60 = average(closes.slice(-60));
  const volume20 = average(previousVolumes);
  const changePct = Number.isFinite(quote.changePercent)
    ? quote.changePercent
    : ((last.close - previous.close) / previous.close) * 100;
  const volumeRatio = Number.isFinite(volume20) && volume20 > 0 ? last.volume / volume20 : null;
  const above20 = Number.isFinite(ma20) ? ((last.close - ma20) / ma20) * 100 : null;
  const above60 = Number.isFinite(ma60) ? ((last.close - ma60) / ma60) * 100 : null;
  const freshAnnouncement = hasFreshItem(state.announcements?.items || [], 36);
  const freshNews = hasFreshItem(state.news?.items || [], 36);
  const bigMove = Math.abs(changePct) >= 3;
  const volumeExpanded = Number.isFinite(volumeRatio) && volumeRatio >= 1.8;
  const technicalBreak =
    (Number.isFinite(above20) && above20 >= 0) || (Number.isFinite(above60) && above60 >= 0);

  let badge = "正常波动";
  let tone = "neutral";
  let summary = "涨跌幅和成交量没有明显偏离，按常规跟踪。";
  let driver = "常规波动";

  if (bigMove && (freshAnnouncement || freshNews)) {
    badge = "消息驱动";
    tone = "watch";
    driver = "消息触发";
    summary = "涨跌幅较大且有近期消息，先核对公告或新闻是否改变基本面假设。";
  } else if (bigMove && volumeExpanded && technicalBreak) {
    badge = "量价突破";
    tone = changePct >= 0 ? "up" : "down";
    driver = "资金推动";
    summary = "消息面未必新增，但成交量放大并触发均线位置，主要看资金能否延续。";
  } else if (bigMove && volumeExpanded) {
    badge = "放量异动";
    tone = "watch";
    driver = "资金推动";
    summary = "涨跌幅较大且成交量放大，更像资金行为，需看次日能否站稳。";
  } else if (bigMove) {
    badge = "价格异动";
    tone = "watch";
    driver = "价格重估";
    summary = "价格变化较大但量能不算突出，谨慎看作短线重估。";
  }

  const direction = changePct >= 0 ? "上涨" : "下跌";
  const volumeText = Number.isFinite(volumeRatio)
    ? `${formatNumber(volumeRatio, 1)}倍20日均量`
    : "均量不足";
  const maText = [
    Number.isFinite(above20) ? `${above20 >= 0 ? "高于" : "低于"}20日线${formatPercent(above20)}` : "",
    Number.isFinite(above60) ? `${above60 >= 0 ? "高于" : "低于"}60日线${formatPercent(above60)}` : "",
  ]
    .filter(Boolean)
    .join("；");
  const newsText =
    freshAnnouncement || freshNews ? "有近36小时公告/新闻，需复核内容" : "未见近36小时重大新增消息";
  const actionText =
    badge === "量价突破"
      ? "不急追，重点看能否放量站稳关键价位"
      : badge === "消息驱动"
        ? "先读公告原文，再判断是否改变收入、成本或订单假设"
        : bigMove
          ? "看次日成交量和回落幅度，防止单日拉升"
          : "继续按常规观察";

  return {
    badge,
    tone,
    summary,
    points: [
      ["价格变化", `${direction}${formatPercent(changePct)}，日内区间 ${formatNumber(last.low, 2)}-${formatNumber(last.high, 2)}`],
      ["成交量", `${formatCompact(last.volume)}，${volumeText}`],
      ["消息面", newsText],
      ["判断", `${driver}；${maText || actionText}`],
    ],
  };
}

function renderAnomaly() {
  const anomaly = buildAnomaly();
  els.anomalySummary.textContent = anomaly.summary;
  els.anomalyBadge.classList.remove("up", "down", "neutral", "watch");
  els.anomalyBadge.classList.add(anomaly.tone);
  els.anomalyBadge.textContent = anomaly.badge;
  els.anomalyPoints.innerHTML = anomaly.points
    .map(
      ([label, value]) => `
        <div>
          <span>${h(label)}</span>
          <strong>${h(value)}</strong>
        </div>
      `,
    )
    .join("");
}

function buildSignals() {
  const signals = [];
  const quote = state.quote;
  const announcements = state.announcements?.items || [];
  const news = state.news?.items || [];
  const research = state.research?.items || [];
  const latestAnnouncement = announcements[0];
  const transaction =
    findByText(
      announcements,
      /關連交易|关连交易|connected transaction|須予披露|须予披露|discloseable|租賃|租赁|船舶|vessel|container/i,
    ) || latestAnnouncement;
  const revenueNews = findByText(news, /收入|營運|运营|業績|业绩|updates|首三月|三月/i);
  const famousView =
    findByText(research, /摩通|大行|目标价|目標價|评级|評級|券商|分析師|分析员/i) ||
    findByText(news, /AASTOCKS|Investing|FX168|信報|智通|經濟通|經濟日報|财經新聞|财经新闻/i);
  const closes = quote?.history?.map((row) => row.close).filter(Number.isFinite) || [];
  const lastClose = closes.at(-1);
  const ma20 = average(closes.slice(-20));
  const ma60 = average(closes.slice(-60));
  const pctFromHigh = quote?.fiftyTwoWeekHigh
    ? ((quote.price - quote.fiftyTwoWeekHigh) / quote.fiftyTwoWeekHigh) * 100
      : null;

  if (Number.isFinite(quote?.changePercent)) {
    const direction = quote.changePercent >= 0 ? "涨" : "跌";
    const turnoverText = Number.isFinite(quote.turnover)
      ? `，成交额${formatMoney(quote.turnover, quote.currency || "HKD")}`
      : "";
    signals.push(
      `市场反应：今日${direction}${formatNumber(
        Math.abs(quote.changePercent),
        2,
      )}%${turnoverText}；先对照公告和行业新闻。`,
    );
  }

  if (famousView) {
    signals.push(`知名观点：${cleanHeadline(famousView.title, 58)}。`);
  }

  if (transaction) {
    signals.push(
      `公告假设：${cleanHeadline(
        transaction.title,
        46,
      )}；核对收入、成本、船队和关联交易。`,
    );
  }

  if (revenueNews) {
    signals.push(`经营数据：${cleanHeadline(revenueNews.title, 54)}。`);
  }

  const waitingPoints = [];
  if (Number.isFinite(lastClose) && Number.isFinite(ma20)) {
    waitingPoints.push(
      `${lastClose >= ma20 ? "站上" : "低于"}20日均线${formatPercent(
        ((lastClose - ma20) / ma20) * 100,
      )}`,
    );
  }
  if (Number.isFinite(lastClose) && Number.isFinite(ma60)) {
    waitingPoints.push(`${lastClose >= ma60 ? "站上" : "低于"}60日均线`);
  }
  if (Number.isFinite(pctFromHigh)) {
    waitingPoints.push(`距52周高点${formatPercent(pctFromHigh)}`);
  }
  if (waitingPoints.length) {
    signals.push(
      `等待点：${waitingPoints.join("；")}；比较是否有更低风险买点或替代标的。`,
    );
  }

  if (!signals.length && latestAnnouncement) {
    signals.push(`最新公告：${latestAnnouncement.releaseTime}，${cleanHeadline(latestAnnouncement.title, 58)}。`);
  }

  if (!signals.length) {
    signals.push("数据不足，建议先查看 HKEX 公告和最新年报。");
  }
  return signals.slice(0, 5);
}

function renderSignals() {
  const signals = buildSignals();
  els.signals.innerHTML = signals.map((text) => `<li>${h(text)}</li>`).join("");
  const severe = signals.some((text) => /低于|核对|等待点|下跌|跌/.test(text));
  const positive = signals.some((text) => /站上|偏强|上涨|涨/.test(text));
  els.signalBadge.classList.remove("up", "down", "neutral", "watch");
  els.signalBadge.classList.add(severe ? "watch" : positive ? "up" : "neutral");
  els.signalBadge.textContent = severe ? "需复核" : positive ? "偏积极" : "中性";
}

function showSectionError(container, error) {
  container.innerHTML = `<div class="error">${error.message}</div>`;
}

async function refresh(code) {
  if (refreshInFlight) return;
  refreshInFlight = true;
  lastRefreshStartedAt = Date.now();
  try {
  const query = String(code || DEFAULT_CODE).trim() || DEFAULT_CODE;
  state.query = query;
  state.quote = null;
  state.announcements = null;
  state.news = null;
  state.research = null;
  els.codeInput.value = query;
  localStorage.setItem("stock-dashboard-query", query);
  setStatus("正在刷新");
  els.signals.innerHTML = "<li>正在读取价格、公告和新闻。</li>";
  els.signalBadge.textContent = "加载中";
  els.anomalySummary.textContent = "正在读取量价和消息面数据";
  els.anomalyBadge.textContent = "加载中";
  els.anomalyPoints.innerHTML = "<div>正在读取成交量、均线和最新消息。</div>";

  const [quoteResult, announcementResult, newsResult, researchResult] = await Promise.allSettled([
    loadJson("/api/quote", query),
    loadJson("/api/announcements", query),
    loadJson("/api/news", query),
    loadJson("/api/research", query),
  ]);

  if (quoteResult.status === "fulfilled") {
    state.quote = quoteResult.value;
    state.code = state.quote.code;
    localStorage.setItem("stock-dashboard-code", state.code);
    updateQuote(state.quote);
    renderIntradayChart();
    renderChart();
  } else {
    els.chartCaption.textContent = quoteResult.reason.message;
    els.price.textContent = "--";
  }

  if (announcementResult.status === "fulfilled") {
    state.announcements = announcementResult.value;
    state.stock = state.announcements.stock;
    renderAnnouncements(state.announcements);
    updateStockHeader();
  } else {
    showSectionError(els.announcements, announcementResult.reason);
  }

  if (newsResult.status === "fulfilled") {
    state.news = newsResult.value;
    renderNews(state.news);
  } else {
    showSectionError(els.news, newsResult.reason);
  }

  if (researchResult.status === "fulfilled") {
    state.research = researchResult.value;
    renderResearch(state.research);
  } else {
    showSectionError(els.research, researchResult.reason);
    els.forumLinks.innerHTML = "";
  }

  renderSignals();
  renderAnomaly();
  setStatus(`已刷新 ${new Date().toLocaleString("zh-CN", { hour12: false })}`);
  } finally {
    refreshInFlight = false;
  }
}

els.form.addEventListener("submit", (event) => {
  event.preventDefault();
  refresh(els.codeInput.value);
});

let searchTimer = null;
els.codeInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    const q = els.codeInput.value.trim();
    if (!q) {
      els.stockOptions.innerHTML = "";
      return;
    }
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(q)}`, { cache: "no-store" });
      const data = await response.json();
      els.stockOptions.innerHTML = (data.items || [])
        .map((item) => {
          const label = [item.displayName, item.shortName, ...(item.aliases || [])]
            .filter(Boolean)
            .join(" / ");
          return `<option value="${h(item.code)}" label="${h(label)}"></option>`;
        })
        .join("");
    } catch {
      els.stockOptions.innerHTML = "";
    }
  }, 180);
});

els.rangeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    els.rangeButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.range = Number(button.dataset.range);
    renderChart();
  });
});

window.addEventListener("resize", () => {
  if (state.quote) {
    renderIntradayChart();
    renderChart();
  }
});

refresh(localStorage.getItem("stock-dashboard-query") || localStorage.getItem("stock-dashboard-code") || DEFAULT_CODE);

setInterval(() => {
  refresh(state.query || state.code || DEFAULT_CODE);
}, AUTO_REFRESH_MS);

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && Date.now() - lastRefreshStartedAt > AUTO_REFRESH_MS) {
    refresh(state.query || state.code || DEFAULT_CODE);
  }
});
