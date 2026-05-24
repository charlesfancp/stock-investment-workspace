const DATA_PATHS = {
  scores: "/data/processed/scores_latest.csv",
  prices: "/data/processed/prices_latest.csv",
  benchmarks: "/data/processed/benchmarks_latest.csv",
  risks: "/data/processed/portfolio_risk_latest.csv",
  events: "/data/processed/event_calendar_latest.csv",
  fundamentals: "/data/processed/fundamentals_latest.csv",
  valuation: "/data/processed/valuation_latest.csv",
  physicalAiReport: "/reports/event/20260519_physical_ai_us_judgment.md",
};

const TARGETS = [
  { ticker: "NVDA", weight: 20, theme: "算力" },
  { ticker: "TSM", weight: 17, theme: "先进制造" },
  { ticker: "AVGO", weight: 11, theme: "ASIC/网络" },
  { ticker: "GOOGL", weight: 17, theme: "模型/入口" },
  { ticker: "AMZN", weight: 15, theme: "云" },
  { ticker: "MU", weight: 8, theme: "HBM" },
  { ticker: "GEV", weight: 4, theme: "电力" },
  { ticker: "VRT", weight: 4, theme: "散热" },
  { ticker: "ETN", weight: 2, theme: "电气" },
  { ticker: "DLR", weight: 2, theme: "数据中心" },
];

const PHYSICAL_AI_MAP = [
  { ticker: "NVDA", status: "核心持有", role: "物理 AI 第一表达", note: "GPU、Omniverse、GR00T、机器人和自动驾驶模型栈" },
  { ticker: "TSLA", status: "观察池", role: "具身智能整机", note: "Optimus、FSD、Robotaxi；暂不纳入 Version B" },
  { ticker: "GOOGL", status: "核心持有", role: "Waymo / 云 / 模型", note: "Robotaxi 运营规模与 Cloud AI 增长共同验证" },
  { ticker: "AMZN", status: "持有", role: "AWS / 仓储自动化", note: "AI 芯片与 GPU capacity 是主证据，机器人是内部效率期权" },
  { ticker: "GEV/VRT/ETN/DLR", status: "低权重持有", role: "电力 / 散热 / 数据中心", note: "订单和 backlog 强，但不追高" },
];

const NEXT_ACTIONS = [
  { label: "NVDA", text: "财报后核查 physical AI、Omniverse、GR00T 是否出现可量化收入或客户证据" },
  { label: "TSLA", text: "只进观察池，等待 Optimus / Robotaxi 官方量产、成本、安全和运营数据" },
  { label: "GOOGL", text: "跟踪 Waymo weekly rides、Other Bets 亏损和 Cloud AI backlog" },
  { label: "电力链", text: "核查 GEV / VRT / ETN / DLR backlog 转收入和订单质量" },
];

const SCENARIOS = [
  {
    name: "基准",
    probability: "60%",
    title: "物理 AI 早期商业化，收入先流向基础设施",
    action: "继续运行 Version B；不为主题追纯度",
  },
  {
    name: "乐观",
    probability: "25%",
    title: "Robotaxi / Optimus / Waymo 出现规模化拐点",
    action: "考虑 Version C，评估 TSLA 或提高 NVDA / GOOGL 权重",
  },
  {
    name: "风险",
    probability: "15%",
    title: "机器人延后、监管受阻或 AI capex 被质疑",
    action: "降低高估值扩张链条，保留现金和基本面最强标的",
  },
];

const WATCHLIST = [
  { ticker: "TSLA", priority: "高", reason: "Optimus、FSD、Robotaxi 是最直接物理 AI 载体", gate: "需要官方量产、成本、安全和运营数据" },
  { ticker: "SOXX", priority: "高", reason: "半导体 beta，适合观察 AI 基础设施广谱行情", gate: "只作 ETF 对照，不替代单票 thesis" },
  { ticker: "XLU", priority: "中", reason: "数据中心电力需求的防守表达", gate: "需核查公用事业估值和利率敏感性" },
  { ticker: "ITA", priority: "中", reason: "国防与航天，提供非 AI 分散线索", gate: "不是 AI 主线，不能挤占核心仓位" },
  { ticker: "GDX", priority: "中", reason: "美元走弱/金价上行情景的对冲工具", gate: "只作为宏观对冲，不作为 AI 替代" },
  { ticker: "META/MSFT/NEE", priority: "中", reason: "SCB 覆盖的 AI 应用、公用事业和云链条对照", gate: "需独立建立基本面与估值证据" },
];

const SOURCE_ITEMS = [
  { source: "NVIDIA", date: "2026-03-16", status: "已核实", fact: "Cosmos 3、Isaac GR00T N1.7、Alpamayo 等 physical AI / robotics 模型栈" },
  { source: "Tesla", date: "2026-04-22", status: "已核实", fact: "Q1 2026 Update 披露 Robotaxi、FSD、Optimus ramp 相关表述" },
  { source: "Alphabet", date: "2026-04-29", status: "已核实", fact: "Q1 2026 slides 披露 Google Cloud、Waymo robotaxi 规模线索" },
  { source: "Amazon", date: "2026-05", status: "已核实", fact: "AI chips、Trainium capacity、NVIDIA GPU deployment 等 AI infra 线索" },
  { source: "SCB Private Bank", date: "2026-05", status: "线索", fact: "月度配置 deck 支持 AI infra + 半导体 + 公用事业 + 国防 + 黄金矿股框架" },
];

const VERIFIED_EVIDENCE = [
  { ticker: "NVDA", type: "物理 AI", source: "NVIDIA 官方", date: "2026-03-16", status: "已核实", impact: "支持", fact: "Cosmos、Isaac GR00T、Omniverse、Alpamayo 形成机器人/自动驾驶 physical AI 栈" },
  { ticker: "TSLA", type: "观察池", source: "Tesla Q1 Update", date: "2026-04-22", status: "已核实", impact: "中性偏支持", fact: "Robotaxi、FSD、Optimus ramp 已披露，但仍需量产和运营数据" },
  { ticker: "GOOGL", type: "物理 AI", source: "Alphabet Q1 slides", date: "2026-04-29", status: "已核实", impact: "支持", fact: "Waymo 与 Google Cloud AI 构成物理 AI 商业化和云训练线索" },
  { ticker: "AMZN", type: "AI 基础设施", source: "Amazon Q1 release", date: "2026-05", status: "已核实", impact: "支持", fact: "AWS AI chips、Trainium capacity 与 NVIDIA GPU deployment 支撑云端 AI infra" },
  { ticker: "AVGO", type: "AI ASIC", source: "Broadcom FY26 Q1", date: "2026-03-04", status: "已核实", impact: "支持", fact: "AI revenue 由 custom AI accelerators 和 AI networking 驱动" },
  { ticker: "TSM", type: "先进制造", source: "TSMC Q1 transcript", date: "2026-04-16", status: "已核实", impact: "支持", fact: "AI megatrend 和 HPC 需求支撑先进制程收入" },
  { ticker: "GEV/VRT/ETN/DLR", type: "电力/数据中心", source: "公司财报与 IR", date: "2026-Q1", status: "已核实", impact: "支持", fact: "数据中心电力、液冷、配电、带电容量需求继续支撑二阶受益" },
  { ticker: "SOXX/XLU/ITA/GDX", type: "外部线索", source: "SCB May 2026 deck", date: "2026-05", status: "线索", impact: "观察", fact: "作为观察池和配置对照，不直接进入 Version B 权重" },
];

const SCB_ITEMS = [
  { label: "可吸收", text: "SOXX、XLU、ITA、GDX、META、MSFT、NEE 进入观察池" },
  { label: "已验证", text: "NVDA、TSM、AVGO、MU、GOOGL、AMZN、VRT 与 Version B 主线一致" },
  { label: "不照搬", text: "结构票、CLN、TRF、IRS 默认排除，除非单独拆 payoff" },
  { label: "边界", text: "SCB 是私行配置材料，不是独立深度研究" },
];

const KILL_CRITERIA = [
  { label: "AI capex", text: "大型云厂商下修 capex 或延后数据中心建设" },
  { label: "Robotaxi", text: "重大安全或监管事件导致商业化节奏受阻" },
  { label: "Optimus", text: "量产、成本或可靠性再次大幅推迟" },
  { label: "高估值链条", text: "NVDA / AVGO / VRT / GEV 订单或 backlog 低于预期" },
];

const STORAGE_KEY = "aiInfraInvestmentRecords.v1";
const state = {
  scores: [],
  prices: [],
  benchmarks: [],
  risks: [],
  events: [],
  fundamentals: [],
  valuation: [],
  physicalAiReport: "",
  records: [],
};

function parseCSV(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (char === '"' && quoted && next === '"') {
      value += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(value);
      value = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(value);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }

  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }

  const [headers, ...body] = rows;
  if (!headers) return [];
  return body.map((line) =>
    Object.fromEntries(headers.map((header, index) => [header, line[index] ?? ""]))
  );
}

function numberValue(value) {
  if (value === undefined || value === null || value === "" || value === "null") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function fmt(value, digits = 2) {
  const parsed = numberValue(value);
  return parsed === null ? "缺失" : parsed.toFixed(digits);
}

function riskClass(level) {
  if (level === "high") return "risk-high";
  if (level === "medium") return "risk-medium";
  if (level === "low") return "risk-low";
  return "neutral";
}

function riskLabel(level) {
  return { high: "高", medium: "中", low: "低" }[level] || "缺失";
}

async function loadCSV(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) return [];
  return parseCSV(await response.text());
}

async function loadText(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) return "";
  return response.text();
}

async function loadData() {
  const [scores, prices, benchmarks, risks, events, fundamentals, valuation, physicalAiReport] = await Promise.all([
    loadCSV(DATA_PATHS.scores),
    loadCSV(DATA_PATHS.prices),
    loadCSV(DATA_PATHS.benchmarks),
    loadCSV(DATA_PATHS.risks),
    loadCSV(DATA_PATHS.events),
    loadCSV(DATA_PATHS.fundamentals),
    loadCSV(DATA_PATHS.valuation),
    loadText(DATA_PATHS.physicalAiReport),
  ]);
  state.scores = scores;
  state.prices = prices;
  state.benchmarks = benchmarks;
  state.risks = risks;
  state.events = events;
  state.fundamentals = fundamentals;
  state.valuation = valuation;
  state.physicalAiReport = physicalAiReport;
  renderAll();
}

function loadRecords() {
  try {
    state.records = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    state.records = [];
  }
}

function persistRecords() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.records));
}

function priceFor(ticker) {
  return numberValue(state.prices.find((row) => row.ticker === ticker)?.price) || 0;
}

function scoreFor(ticker) {
  return state.scores.find((row) => row.ticker === ticker) || {};
}

function latestSnapshot() {
  return [...state.records].reverse().find((record) => record.type === "snapshot");
}

function setText(id, text) {
  const element = document.getElementById(id);
  if (element) element.textContent = text;
}

function riskLevel() {
  if (state.risks.some((risk) => risk.risk_level === "high")) return "高";
  if (state.risks.some((risk) => risk.risk_level === "medium")) return "中";
  return "低";
}

function primaryDecision() {
  const defensive = state.scores.some((score) => (score.action || "").includes("减仓") || (score.action || "").includes("止损"));
  if (defensive) return "持有，防守复核";
  if (riskLevel() === "高") return "持有，先补证据";
  return "持有，继续跟踪";
}

function renderDecision() {
  const decision = primaryDecision();
  setText("decisionBadge", decision);
  setText(
    "decisionSummary",
    "继续运行 Version B，不因物理 AI 主题立即换仓。物理 AI 方向成立，但当前美股最优表达仍是上游 AI 基础设施；TSLA 加入观察池，暂不纳入组合。"
  );

  const chips = [
    ["核心", "NVDA / GOOGL / AMZN"],
    ["观察", "TSLA"],
    ["低权重", "GEV / VRT / ETN / DLR"],
    ["边界", "不自动交易"],
  ];
  document.getElementById("decisionChips").innerHTML = chips
    .map(([label, value]) => `<span class="decision-chip"><b>${label}</b>${value}</span>`)
    .join("");

  document.getElementById("nextActionList").innerHTML = NEXT_ACTIONS.map(
    (item) => `
      <div class="action-item">
        <strong>${item.label}</strong>
        <span>${item.text}</span>
      </div>`
  ).join("");
}

function renderOverview() {
  const topRisk = riskLevel();
  const overheat = state.risks.find((risk) => risk.risk_area === "technical_overheat");
  const events = state.risks.find((risk) => risk.risk_area === "event_density");
  const positions = state.risks.find((risk) => risk.risk_area === "position_data");
  const timestamp = state.risks[0]?.fetched_at || state.scores[0]?.fetched_at || "未生成";

  setText("portfolioRiskLevel", topRisk);
  setText("overheatCount", overheat?.value ?? "--");
  setText("eventCount", events?.value ?? "--");
  setText("positionGap", positions?.value ?? "--");
  setText("dataTimestamp", timestamp.replace("T", " ").replace("Z", " UTC"));

  const themeStrip = document.getElementById("themeStrip");
  themeStrip.innerHTML = TARGETS.slice(0, 5)
    .map((item) => {
      const score = scoreFor(item.ticker);
      return `<div class="theme-tile"><span>${item.theme}</span><strong>${score.score || "--"}</strong><span>${item.ticker}</span></div>`;
    })
    .join("");

  const allocationBars = document.getElementById("allocationBars");
  allocationBars.innerHTML = TARGETS.map(
    (item) => `
      <div class="bar-item">
        <div class="bar-line"><strong>${item.ticker}</strong><span>${item.weight}%</span></div>
        <div class="bar-track"><div class="bar-fill" style="width:${item.weight}%"></div></div>
      </div>`
  ).join("");
}

function renderScenarios() {
  document.getElementById("scenarioGrid").innerHTML = SCENARIOS.map(
    (item) => `
      <div class="scenario-card">
        <div><strong>${item.name}</strong><span>${item.probability}</span></div>
        <p>${item.title}</p>
        <em>${item.action}</em>
      </div>`
  ).join("");
}

function renderBenchmarks() {
  const tickers = ["QQQ", "SOXX", "SMH"];
  document.getElementById("benchmarkPanel").innerHTML = tickers.map((ticker) => {
    const row = state.benchmarks.find((item) => item.ticker === ticker) || {};
    return `
      <div class="benchmark-row">
        <strong>${ticker}</strong>
        <span>价格 ${fmt(row.price)}</span>
        <span>涨跌 ${fmt(row.change_percent)}%</span>
      </div>`;
  }).join("");
}

function renderPhysicalAi() {
  const map = document.getElementById("physicalAiMap");
  map.innerHTML = PHYSICAL_AI_MAP.map(
    (item) => `
      <div class="theme-row">
        <div>
          <strong>${item.ticker}</strong>
          <span>${item.role}</span>
        </div>
        <span class="status-pill neutral">${item.status}</span>
        <p>${item.note}</p>
      </div>`
  ).join("");
}

function countEligible(rows) {
  return rows.filter((row) => row.conclusion_eligible === "true").length;
}

function renderEvidencePanel() {
  const fundamentalsReady = countEligible(state.fundamentals);
  const valuationReady = countEligible(state.valuation);
  const total = TARGETS.length;
  const scoreCoverage = state.scores.filter((score) => score.evidence_coverage === "technicals_plus_fundamentals_valuation").length;
  const verifiedCount = VERIFIED_EVIDENCE.filter((item) => item.status === "已核实").length;
  const themeSupport = VERIFIED_EVIDENCE.filter((item) => item.impact.includes("支持")).length;
  document.getElementById("evidencePanel").innerHTML = `
    <div class="evidence-metrics">
      <div><span>主题证据</span><strong>${verifiedCount}/${VERIFIED_EVIDENCE.length}</strong></div>
      <div><span>支持主线</span><strong>${themeSupport}</strong></div>
      <div><span>财务完整</span><strong>${scoreCoverage}/${total}</strong></div>
    </div>
    <div class="evidence-table">
      ${VERIFIED_EVIDENCE.map(
        (item) => `
          <div class="evidence-row">
            <strong>${item.ticker}</strong>
            <span>${item.type}</span>
            <span>${item.source} · ${item.date}</span>
            <span class="${item.status === "已核实" ? "verified" : "lead"}">${item.status}</span>
            <p>${item.fact}</p>
          </div>`
      ).join("")}
    </div>
    <div class="evidence-note">
      主题和事件证据已经纳入页面；但正式财务模型仍受限于基本面与估值缺口。当前基本面可用 ${fundamentalsReady}/${total}，估值可用 ${valuationReady}/${total}。只有 source、source_url、source_tier、source_type、source_date、verified_status 和 freshness_status 都合格的数据，才会进入财务结论资格。
    </div>`;
}

function renderWatchlist() {
  document.getElementById("watchlistGrid").innerHTML = WATCHLIST.map(
    (item) => `
      <div class="watch-card">
        <div><strong>${item.ticker}</strong><span>${item.priority}</span></div>
        <p>${item.reason}</p>
        <em>${item.gate}</em>
      </div>`
  ).join("");
}

function renderSourceList() {
  document.getElementById("sourceList").innerHTML = SOURCE_ITEMS.map(
    (item) => `
      <div class="source-item">
        <strong>${item.source}</strong>
        <span>${item.date} · ${item.status}</span>
        <p>${item.fact}</p>
      </div>`
  ).join("");
  document.getElementById("scbPanel").innerHTML = SCB_ITEMS.map(
    (item) => `
      <div class="source-item">
        <strong>${item.label}</strong>
        <p>${item.text}</p>
      </div>`
  ).join("");
  document.getElementById("killCriteria").innerHTML = KILL_CRITERIA.map(
    (item) => `
      <div class="action-item">
        <strong>${item.label}</strong>
        <span>${item.text}</span>
      </div>`
  ).join("");
}

function renderRiskTable() {
  const table = document.getElementById("riskTable");
  table.innerHTML = state.risks
    .map(
      (risk) => `
        <tr>
          <td>${risk.risk_area}</td>
          <td><span class="risk-pill ${riskClass(risk.risk_level)}">${riskLabel(risk.risk_level)}</span></td>
          <td>${risk.value}</td>
          <td>${risk.status}</td>
        </tr>`
    )
    .join("");
}

function renderScores() {
  const table = document.getElementById("scoreTable");
  table.innerHTML = state.scores
    .map(
      (score) => `
        <tr>
          <td><strong>${score.ticker}</strong></td>
          <td>${score.score}</td>
          <td>${score.action}</td>
          <td>${score.evidence_coverage}</td>
        </tr>`
    )
    .join("");
}

function renderEvents() {
  const table = document.getElementById("eventTable");
  const sorted = [...state.events].sort((a, b) => (a.event_date || "").localeCompare(b.event_date || ""));
  table.innerHTML = sorted
    .map(
      (event) => `
        <tr>
          <td>${event.event_date || "缺失"}</td>
          <td><strong>${event.ticker || "组合"}</strong></td>
          <td>${event.event_type || "缺失"}</td>
          <td>${event.title || "缺失"}</td>
          <td>${event.include_in_report === "true" ? "14天窗口" : event.status}</td>
        </tr>`
    )
    .join("");
}

function renderPositionEditor() {
  const latest = latestSnapshot();
  const positions = Object.fromEntries((latest?.positions || []).map((row) => [row.ticker, row]));
  const table = document.getElementById("positionEditor");
  table.innerHTML = TARGETS.map((target) => {
    const position = positions[target.ticker] || {};
    return `
      <tr data-ticker="${target.ticker}">
        <td><strong>${target.ticker}</strong></td>
        <td>${target.weight}%</td>
        <td>${fmt(priceFor(target.ticker))}</td>
        <td><input data-field="shares" type="number" step="0.0001" min="0" value="${position.shares ?? ""}" /></td>
        <td><input data-field="averageCost" type="number" step="0.01" min="0" value="${position.averageCost ?? ""}" /></td>
        <td data-field="currentWeight">--</td>
      </tr>`;
  }).join("");
  updateCurrentWeights();
}

function updateCurrentWeights() {
  const rows = [...document.querySelectorAll("#positionEditor tr")];
  const values = rows.map((row) => {
    const ticker = row.dataset.ticker;
    const shares = numberValue(row.querySelector('[data-field="shares"]').value) || 0;
    return { row, marketValue: shares * priceFor(ticker) };
  });
  const cash = numberValue(document.getElementById("cashInput").value) || 0;
  const total = values.reduce((sum, item) => sum + item.marketValue, cash);
  values.forEach((item) => {
    const cell = item.row.querySelector('[data-field="currentWeight"]');
    cell.textContent = total > 0 ? `${((item.marketValue / total) * 100).toFixed(1)}%` : "--";
  });
}

function renderTickerSelect() {
  const select = document.querySelector('select[name="ticker"]');
  select.innerHTML = TARGETS.map((item) => `<option value="${item.ticker}">${item.ticker}</option>`).join("");
}

function recordSummary(record) {
  if (record.type === "snapshot") return `快照 ${record.positions.length} 只`;
  if (record.type === "change") return `${record.ticker} ${record.changeType} ${record.shareDelta || 0} 股`;
  return record.title || "复盘";
}

function renderHistory() {
  const table = document.getElementById("historyTable");
  if (!state.records.length) {
    table.innerHTML = `<tr><td colspan="4" class="empty-state">暂无记录</td></tr>`;
    return;
  }
  table.innerHTML = [...state.records]
    .reverse()
    .map((record) => {
      const value = record.type === "snapshot" ? fmt(record.totalMarketValue) : "--";
      return `
        <tr>
          <td>${record.date}</td>
          <td>${record.type}</td>
          <td>${recordSummary(record)}</td>
          <td>${value}</td>
        </tr>`;
    })
    .join("");
}

function collectSnapshot() {
  const rows = [...document.querySelectorAll("#positionEditor tr")];
  const positions = rows.map((row) => {
    const ticker = row.dataset.ticker;
    const shares = numberValue(row.querySelector('[data-field="shares"]').value) || 0;
    const averageCost = numberValue(row.querySelector('[data-field="averageCost"]').value) || 0;
    const price = priceFor(ticker);
    return {
      ticker,
      targetWeight: TARGETS.find((item) => item.ticker === ticker).weight,
      shares,
      averageCost,
      price,
      marketValue: shares * price,
    };
  });
  const cash = numberValue(document.getElementById("cashInput").value) || 0;
  const totalMarketValue = positions.reduce((sum, item) => sum + item.marketValue, cash);
  return {
    id: crypto.randomUUID(),
    type: "snapshot",
    date: document.getElementById("snapshotDate").value,
    operator: document.getElementById("operatorInput").value || "manual",
    cash,
    totalMarketValue,
    positions,
    createdAt: new Date().toISOString(),
  };
}

function saveSnapshot() {
  const snapshot = collectSnapshot();
  if (!snapshot.date) return;
  state.records.push(snapshot);
  persistRecords();
  renderHistory();
}

function saveChange(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  state.records.push({
    id: crypto.randomUUID(),
    type: "change",
    date: form.get("date"),
    ticker: form.get("ticker"),
    changeType: form.get("changeType"),
    shareDelta: form.get("shareDelta"),
    price: form.get("price"),
    reason: form.get("reason"),
    notes: form.get("notes"),
    createdAt: new Date().toISOString(),
  });
  persistRecords();
  event.currentTarget.reset();
  setDefaultDates();
  renderHistory();
}

function saveReview() {
  const date = document.getElementById("reviewDate").value;
  const title = document.getElementById("reviewTitle").value;
  if (!date || !title) return;
  state.records.push({
    id: crypto.randomUUID(),
    type: "review",
    date,
    title,
    conclusion: document.getElementById("reviewConclusion").value,
    body: document.getElementById("reviewBody").value,
    createdAt: new Date().toISOString(),
  });
  persistRecords();
  renderHistory();
}

function exportRecords() {
  const blob = new Blob([JSON.stringify(state.records, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `ai-infra-records-${new Date().toISOString().slice(0, 10)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function importRecordsFromFile(event) {
  const file = event.currentTarget.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const records = JSON.parse(String(reader.result || "[]"));
      if (!Array.isArray(records)) throw new Error("records must be an array");
      state.records = records;
      persistRecords();
      renderPositionEditor();
      renderHistory();
    } catch {
      alert("记录文件无法读取。");
    } finally {
      event.currentTarget.value = "";
    }
  });
  reader.readAsText(file);
}

function clearRecords() {
  if (!confirm("确认清空本地记录？")) return;
  state.records = [];
  persistRecords();
  renderPositionEditor();
  renderHistory();
}

function setDefaultDates() {
  const today = new Date().toISOString().slice(0, 10);
  ["snapshotDate", "reviewDate"].forEach((id) => {
    const input = document.getElementById(id);
    if (input && !input.value) input.value = today;
  });
  const changeDate = document.querySelector('input[name="date"]');
  if (changeDate && !changeDate.value) changeDate.value = today;
}

function renderAll() {
  renderDecision();
  renderOverview();
  renderScenarios();
  renderBenchmarks();
  renderPhysicalAi();
  renderEvidencePanel();
  renderWatchlist();
  renderSourceList();
  renderRiskTable();
  renderScores();
  renderEvents();
  renderPositionEditor();
  renderTickerSelect();
  renderHistory();
}

function bindEvents() {
  document.getElementById("refreshData").addEventListener("click", loadData);
  document.getElementById("exportRecords").addEventListener("click", exportRecords);
  document.getElementById("importRecords").addEventListener("click", () => {
    document.getElementById("recordFileInput").click();
  });
  document.getElementById("recordFileInput").addEventListener("change", importRecordsFromFile);
  document.getElementById("saveSnapshot").addEventListener("click", saveSnapshot);
  document.getElementById("clearRecords").addEventListener("click", clearRecords);
  document.getElementById("saveReview").addEventListener("click", saveReview);
  document.getElementById("changeForm").addEventListener("submit", saveChange);
  document.getElementById("positionEditor").addEventListener("input", updateCurrentWeights);
  document.getElementById("cashInput").addEventListener("input", updateCurrentWeights);
}

document.addEventListener("DOMContentLoaded", () => {
  loadRecords();
  setDefaultDates();
  bindEvents();
  loadData();
});
