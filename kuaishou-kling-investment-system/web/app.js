const els = {
  updatedAt: document.querySelector("#updatedAt"),
  action: document.querySelector("#action"),
  actionNote: document.querySelector("#actionNote"),
  price: document.querySelector("#price"),
  priceMeta: document.querySelector("#priceMeta"),
  baseTarget: document.querySelector("#baseTarget"),
  baseUpside: document.querySelector("#baseUpside"),
  status: document.querySelector("#status"),
  statusDetail: document.querySelector("#statusDetail"),
  valuationRows: document.querySelector("#valuationRows"),
  announcements: document.querySelector("#announcements"),
  analystViews: document.querySelector("#analystViews"),
  evidenceItems: document.querySelector("#evidenceItems"),
  triggerRules: document.querySelector("#triggerRules"),
  reviewTimeline: document.querySelector("#reviewTimeline"),
  report: document.querySelector("#report"),
  refresh: document.querySelector("#refresh"),
  runAll: document.querySelector("#runAll"),
  runDaily: document.querySelector("#runDaily"),
  runWeekly: document.querySelector("#runWeekly"),
  runBear: document.querySelector("#runBear"),
  budget: document.querySelector("#budget"),
  note: document.querySelector("#note"),
  recordBuy: document.querySelector("#recordBuy"),
  calcLots: document.querySelector("#calcLots"),
  calcShares: document.querySelector("#calcShares"),
  calcGross: document.querySelector("#calcGross"),
  calcCash: document.querySelector("#calcCash"),
  lotSource: document.querySelector("#lotSource"),
  positionRecords: document.querySelector("#positionRecords"),
  tabs: [...document.querySelectorAll("[data-report]")],
};

let state = { reports: {}, activeReport: "daily" };

function h(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function number(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return `${n > 0 ? "+" : ""}${number(n, 1)}%`;
}

function money(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "--";
  return `${n.toLocaleString("zh-CN", { maximumFractionDigits: 2 })} HKD`;
}

function setBusy(message) {
  els.status.textContent = "运行中";
  els.statusDetail.textContent = message;
  document.body.classList.add("busy");
}

function setReady(message = "可手动刷新") {
  els.status.textContent = "就绪";
  els.statusDetail.textContent = message;
  document.body.classList.remove("busy");
}

async function api(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.output || data.error || "请求失败");
  return data;
}

function renderPosition(position = {}, records = []) {
  els.budget.value = Number(position.budget_hkd || 100000).toFixed(0);
  els.calcLots.textContent = `${position.lots ?? "--"} 手`;
  els.calcShares.textContent = `${Number(position.shares || 0).toLocaleString("zh-CN")} 股`;
  els.calcGross.textContent = money(position.gross_amount_hkd);
  els.calcCash.textContent = money(position.cash_left_hkd);
  els.lotSource.textContent = `按每手 ${position.board_lot_shares || "--"} 股、最新价 ${number(position.price_hkd)} HKD 估算；不含佣金、印花税和滑点。`;
  els.positionRecords.innerHTML = records.length
    ? records
        .map(
          (row) => `
            <div class="record" data-recorded-at="${h(row.recorded_at)}">
              <div class="record-main">
                <div>
                  <strong>${h(row.lots)} 手 / ${Number(row.shares || 0).toLocaleString("zh-CN")} 股</strong>
                  <span>${formatRecordTime(row.recorded_at)} · ${h(row.action || "未评级")}</span>
                </div>
                <div>
                  <b>${money(row.gross_amount_hkd)}</b>
                  <span>价 ${number(row.price_hkd)} · 余 ${money(row.cash_left_hkd)}</span>
                </div>
              </div>
              <div class="record-edit">
                <input value="${h(row.note || "")}" placeholder="补充复盘备注" />
                <button data-action="save-note">改备注</button>
                <button data-action="delete-record" class="danger">删除</button>
              </div>
            </div>
          `,
        )
        .join("")
    : '<p class="empty">暂无买入测算记录</p>';
}

function ratingClass(rating = "") {
  if (/买入|增持|跑赢/.test(rating)) return "buy";
  if (/持有|中性/.test(rating)) return "hold";
  if (/卖出|减持|跑输/.test(rating)) return "sell";
  return "hold";
}

function formatRecordTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "";
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "--";
  return date.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

function addDays(value, days) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  date.setDate(date.getDate() + days);
  return formatDate(date);
}

function renderEvidence(rows = []) {
  els.evidenceItems.innerHTML = rows.length
    ? rows
        .map(
          (item) => `
            <div class="evidence-item">
              <div>
                <strong>${h(item.evidence_id)}</strong>
                <p>${h(item.fact)}</p>
              </div>
              <dl>
                <div><dt>日期</dt><dd>${h(item.date || "--")}</dd></div>
                <div><dt>状态</dt><dd>${h(item.verification || "--")}</dd></div>
                <div><dt>资格</dt><dd>${h(item.conclusion_eligible || "--")}</dd></div>
              </dl>
            </div>
          `,
        )
        .join("")
    : '<p class="empty">暂无证据库记录</p>';
}

function renderRules(rules = {}) {
  const price = rules.price_alerts || {};
  const decision = rules.decision_rules || {};
  const addRules = decision.add_position_if || [];
  const reduceRules = decision.reduce_position_if || [];
  els.triggerRules.innerHTML = `
    <div class="trigger-card">
      <span>买入触发</span>
      <strong>${number(price.strong_buy_below, 0)} HKD 以下</strong>
      <p>当前只对应观察仓/分批建仓假设。</p>
    </div>
    <div class="trigger-card">
      <span>止损线</span>
      <strong>${number(price.stop_loss, 0)} HKD</strong>
      <p>跌破后需重新评估主线是否失效。</p>
    </div>
    <div class="trigger-card">
      <span>加仓条件</span>
      <p>${addRules.map((item) => h(item)).join("；") || "--"}</p>
    </div>
    <div class="trigger-card">
      <span>减仓条件</span>
      <p>${reduceRules.map((item) => h(item)).join("；") || "--"}</p>
    </div>
  `;
}

function renderReview(records = []) {
  const baseRecord = records.find((row) => Number(row.price_hkd) < 50) || records[0];
  if (!baseRecord) {
    els.reviewTimeline.innerHTML = '<p class="empty">暂无可复盘的买入测算记录</p>';
    return;
  }
  const checks = [
    ["30 天", 30, "验证价格触发后是否出现公告、业绩或大行观点确认。"],
    ["60 天", 60, "检查 AI capex、可灵 ARR 和核心利润是否偏离基准假设。"],
    ["90 天", 90, "判断观察仓逻辑是否升级、维持、降级或退出。"],
  ];
  els.reviewTimeline.innerHTML = checks
    .map(
      ([label, days, task]) => `
        <article class="review-card">
          <span>${label}</span>
          <strong>${addDays(baseRecord.recorded_at, days)}</strong>
          <p>${h(task)}</p>
        </article>
      `,
    )
    .join("");
}

function renderSummary(data) {
  state.reports = data.reports || {};
  state.positionRecords = data.positionRecords || [];
  els.updatedAt.textContent = `页面更新时间：${new Date().toLocaleString("zh-CN", { hour12: false })}`;
  els.action.textContent = data.action || "--";
  els.action.dataset.action = data.action || "";
  els.actionNote.textContent = "动作来自本地规则引擎，最终决策需人工确认。";

  const price = data.price || {};
  els.price.textContent = price.close_hkd ? `${number(price.close_hkd)} HKD` : "--";
  els.priceMeta.textContent = price.date ? `${price.date} · ${price.change_pct || "--"}% · 成交量 ${price.volume || "--"}` : "暂无行情";

  els.baseTarget.textContent = data.baseTarget ? `${number(data.baseTarget)} HKD` : "--";
  els.baseUpside.textContent = data.baseUpside ? `相对当前：${pct(data.baseUpside)}` : "--";

  els.valuationRows.innerHTML = (data.valuations || [])
    .map(
      (row) => `
        <tr>
          <td>${h(row.scenario_label || row.scenario)}</td>
          <td>${number(row.target_price_hkd)} HKD</td>
          <td>${pct(row.upside_downside_pct)}</td>
          <td>${number(row.core_value_hkd_bn)} 十亿 HKD</td>
          <td>${number(row.kling_owned_value_hkd_bn)} 十亿 HKD</td>
        </tr>
      `,
    )
    .join("");

  els.announcements.innerHTML = (data.announcements || [])
    .map(
      (item) => `
        <a class="item" href="${h(item.link)}" target="_blank" rel="noreferrer">
          <span>${h(item.date)} · ${h(item.display_source || item.source)}</span>
          <strong>${h(item.display_title || item.title)}</strong>
          <em>${item.is_major_event === "True" ? "重大" : "普通"}</em>
        </a>
      `,
    )
    .join("") || '<p class="empty">暂无公告记录</p>';

  els.analystViews.innerHTML = (data.analystViews || [])
    .map(
      (view) => `
        <article class="analyst-card">
          <div class="analyst-top">
            <div>
              <strong>${h(view.institution)}</strong>
              <span>${h(view.date)} · ${h(view.source)}</span>
            </div>
            <em class="${ratingClass(view.rating)}">${h(view.rating || "--")}</em>
          </div>
          <div class="target-row">
            <span>目标价</span>
            <b>${number(view.target_price_hkd)} HKD</b>
            ${view.previous_target_hkd ? `<small>前值 ${number(view.previous_target_hkd)}</small>` : ""}
          </div>
          <p>${h(view.chinese_summary)}</p>
          <div class="point-row">${String(view.key_points || "")
            .split(";")
            .filter(Boolean)
            .map((point) => `<span>${h(point)}</span>`)
            .join("")}</div>
          <a href="${h(view.source_url)}" target="_blank" rel="noreferrer">查看来源</a>
        </article>
      `,
    )
    .join("") || '<p class="empty">暂无分析师观点</p>';

  renderEvidence(data.evidence || []);
  renderRules(data.rules || {});
  renderPosition(data.position, data.positionRecords || []);
  renderReview(data.positionRecords || []);

  renderReport();
}

function renderReport() {
  els.report.textContent = state.reports[state.activeReport] || "暂无报告";
  els.tabs.forEach((button) => button.classList.toggle("active", button.dataset.report === state.activeReport));
}

async function loadSummary() {
  const data = await api("/api/summary");
  renderSummary(data);
  setReady("数据已刷新");
}

async function run(path, label) {
  setBusy(label);
  try {
    const result = await api(path, { method: "POST" });
    await loadSummary();
    setReady(result.ok ? "运行完成" : "运行失败");
  } catch (error) {
    try {
      const data = await api("/api/summary");
      renderSummary(data);
    } catch (_summaryError) {
      // Keep the original run error visible when even summary refresh fails.
    }
    els.status.textContent = "失败";
    els.statusDetail.textContent = `已刷新可用数据；部分来源失败：${String(error.message || error).slice(0, 140)}`;
    document.body.classList.remove("busy");
  }
}

async function updateCalculation() {
  const amount = Number(els.budget.value || 0);
  const position = await api(`/api/position/calc?amount=${encodeURIComponent(amount)}`);
  renderPosition(position, state.positionRecords || []);
}

async function recordBuy() {
  setBusy("正在写入买入测算记录");
  try {
    await api("/api/position/record", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: Number(els.budget.value || 0),
        note: els.note.value,
      }),
    });
    els.note.value = "";
    await loadSummary();
    setReady("记录已保存");
  } catch (error) {
    els.status.textContent = "失败";
    els.statusDetail.textContent = String(error.message || error).slice(0, 180);
    document.body.classList.remove("busy");
  }
}

async function updateRecordNote(recordedAt, note) {
  setBusy("正在修改备注");
  await api("/api/position/note", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recorded_at: recordedAt, note }),
  });
  await loadSummary();
  setReady("备注已修改");
}

async function deleteRecord(recordedAt) {
  setBusy("正在删除误操作记录");
  await api("/api/position/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recorded_at: recordedAt }),
  });
  await loadSummary();
  setReady("记录已删除");
}

els.refresh.addEventListener("click", loadSummary);
els.runAll.addEventListener("click", () => run("/api/run/all", "正在更新全部数据"));
els.runDaily.addEventListener("click", () => run("/api/run/daily", "正在生成日报"));
els.runWeekly.addEventListener("click", () => run("/api/run/weekly", "正在生成周报"));
els.runBear.addEventListener("click", () => run("/api/run/bear", "正在生成反证"));
els.budget.addEventListener("change", updateCalculation);
els.recordBuy.addEventListener("click", recordBuy);
els.positionRecords.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const record = button.closest(".record");
  const recordedAt = record?.dataset.recordedAt;
  if (!recordedAt) return;
  if (button.dataset.action === "save-note") {
    updateRecordNote(recordedAt, record.querySelector("input")?.value || "").catch((error) => {
      els.status.textContent = "失败";
      els.statusDetail.textContent = String(error.message || error).slice(0, 180);
      document.body.classList.remove("busy");
    });
  }
  if (button.dataset.action === "delete-record") {
    deleteRecord(recordedAt).catch((error) => {
      els.status.textContent = "失败";
      els.statusDetail.textContent = String(error.message || error).slice(0, 180);
      document.body.classList.remove("busy");
    });
  }
});
els.tabs.forEach((button) => {
  button.addEventListener("click", () => {
    state.activeReport = button.dataset.report;
    renderReport();
  });
});

loadSummary().catch((error) => {
  els.status.textContent = "失败";
  els.statusDetail.textContent = error.message;
});
