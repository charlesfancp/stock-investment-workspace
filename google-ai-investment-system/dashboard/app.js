const missing = "数据缺失";

fetch(`data.json?v=${Date.now()}`, { cache: "no-store" })
  .then((response) => {
    if (!response.ok) {
      throw new Error(response.status === 404 ? "missing-data" : "fetch-failed");
    }
    return response.json();
  })
  .then(render)
  .catch((error) => {
    document.querySelector("#decision").textContent =
      error.message === "missing-data"
        ? "dashboard/data.json 缺失，请先运行 python scripts/build_dashboard_data.py。"
        : "当前页面需要通过本地静态服务打开。请运行 python scripts/serve_dashboard.py 后访问 http://127.0.0.1:8765/。";
  });

function render(data) {
  text("#updatedAt", data.updated_at);
  text("#confidence", data.confidence);
  text("#eligibility", data.trading_eligible ? "具备复核资格" : "未具备");
  text("#decision", data.decision);
  text("#action", data.action);
  renderHero(data);

  renderMarket(data.market || []);
  renderRRGate(data.rr_gate);
  renderScore(data.score);
  renderThesis(data.thesis);
  renderIOEvent(data.io_event);
  renderAnalysts(data.analysts);
  renderScenarios(data.scenarios);
  renderValuation(data.valuation, data.trading_eligibility_note);
  renderPosition(data.position);
  renderPriceSensitivity(data.price_sensitivity);
  renderValuationScenarios(data.valuation_scenarios);
  renderMissingInputs(data.missing_inputs || []);
  renderEvidence(data.evidence);
  renderRisks(data.risks, data.triggers);
  renderLogs(data.decision_log);
  renderDecisionPlans(data.decision_plans || []);
  renderReviews(data.reviews);
}

document.querySelector("#refreshDashboard").addEventListener("click", (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "刷新中";
  setSaveStatus("正在重新生成报告和面板", "neutral");
  fetch("/api/refresh", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
    .then((response) => response.json())
    .then((result) => {
      if (!result.ok) throw new Error(result.error || "刷新失败");
      setSaveStatus("已刷新，正在重新载入", "green");
      window.location.reload();
    })
    .catch((error) => {
      button.disabled = false;
      button.textContent = "刷新面板";
      setSaveStatus(`刷新失败：${error.message}`, "red");
    });
});

document.querySelector("#decisionPlanForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveForm("/api/decision-plan", event.currentTarget, false);
});

function renderHero(data) {
  text("#heroPrice", money(data.valuation?.current_price));
  text("#heroPriceMeta", `${data.valuation?.ticker || "GOOGL"} · ${data.valuation?.source_date || missing}`);
  text("#heroScore", `${data.score?.total ?? missing}`);
  text("#heroRR", data.valuation?.rr || missing);
  text("#heroBuyBelow", data.price_sensitivity?.buy_below || missing);
  text("#heroReduceAbove", data.price_sensitivity?.reduce_review_above || missing);
}

function renderMarket(items) {
  const grid = document.querySelector("#marketGrid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!items.length) {
    grid.appendChild(card("行情快照", "数据缺失", "请先录入或更新 market_snapshot.csv"));
    return;
  }
  items.forEach((item) => {
    grid.appendChild(
      card(
        `${item.ticker} · ${item.share_class}`,
        `$${item.current_price}`,
        `市值 ${item.market_cap_usd_bn}bn；PE ${item.pe_ratio}；收盘 ${item.regular_close_time}；来源 ${item.source_name}`
      )
    );
  });
}

function renderRRGate(gate) {
  const summary = document.querySelector("#rrGateSummary");
  const grid = document.querySelector("#rrGateGrid");
  grid.innerHTML = "";
  if (!gate) {
    summary.textContent = "R/R 状态数据缺失";
    return;
  }
  summary.className = gate.unlocked ? "gate-summary open" : "gate-summary locked";
  summary.innerHTML = `<strong></strong><span></span><p></p>`;
  summary.querySelector("strong").textContent = gate.title;
  summary.querySelector("span").textContent = gate.calculation || missing;
  summary.querySelector("p").textContent = `${gate.message} ${gate.methodology_note}`;
  gate.items.forEach((item) => {
    const el = card(item.label, item.value || missing, item.status);
    el.classList.add(item.status === "已录入" ? "ok" : "missing");
    grid.appendChild(el);
  });
}

document.querySelector("#valuationForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveForm("/api/valuation", event.currentTarget, true);
});

document.querySelector("#marketForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveForm("/api/market", event.currentTarget, true);
});

document.querySelector("#positionForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveForm("/api/position", event.currentTarget, true);
});

function text(selector, value) {
  document.querySelector(selector).textContent = value || missing;
}

function renderScore(score) {
  const grid = document.querySelector("#scoreGrid");
  grid.innerHTML = "";
  score.dimensions.forEach((item) => {
    grid.appendChild(card(item.label, `${item.score} / ${item.max_score}`, item.reasons.join("；")));
  });
}

function renderThesis(thesis) {
  const labels = {
    search: "Search 现金牛",
    cloud: "Cloud 第二利润引擎",
    ai_fcf: "AI CapEx / FCF",
    variant: "非共识判断",
  };
  const grid = document.querySelector("#thesisGrid");
  grid.innerHTML = "";
  Object.entries(labels).forEach(([key, label]) => grid.appendChild(card(label, "", thesis[key])));
}

function renderIOEvent(event) {
  const summary = document.querySelector("#ioSummary");
  const grid = document.querySelector("#ioGrid");
  const watchlist = document.querySelector("#ioWatchlist");
  grid.innerHTML = "";
  watchlist.innerHTML = "";
  if (!event) {
    summary.textContent = "I/O 事件数据缺失";
    return;
  }
  summary.className = "gate-summary";
  summary.innerHTML = `<strong></strong><span></span><p></p>`;
  summary.querySelector("strong").textContent = event.title;
  summary.querySelector("span").textContent = event.status;
  summary.querySelector("p").textContent = event.summary;
  (event.items || []).forEach((item) => grid.appendChild(card(item.label, item.metric, item.detail)));
  (event.watchlist || []).forEach((item) => watchlist.appendChild(card(item, "", "")));
}

function renderAnalysts(analysts) {
  const summary = document.querySelector("#analystSummary");
  const grid = document.querySelector("#analystGrid");
  grid.innerHTML = "";
  if (!analysts) {
    summary.textContent = "投行目标价数据缺失";
    return;
  }
  summary.className = "gate-summary";
  summary.innerHTML = `<strong></strong><span></span><p></p>`;
  summary.querySelector("strong").textContent = "外部目标价参考";
  summary.querySelector("span").textContent = analysts.status;
  summary.querySelector("p").textContent =
    `${analysts.summary} 参考基准目标价 ${analysts.base_target_reference || missing}；风险参考 ${analysts.risk_target_reference || missing}；乐观参考 ${analysts.bull_target_reference || missing}。`;
  (analysts.items || []).forEach((item) => {
    grid.appendChild(
      card(
        item.firm,
        `$${item.target_price}`,
        `${item.rating}；${item.action}；前值 ${item.previous_target || missing}；来源 ${item.source_name}；日期 ${item.source_date}`
      )
    );
  });
}

function renderScenarios(scenarios) {
  const grid = document.querySelector("#scenarioGrid");
  if (!grid) return;
  grid.innerHTML = "";
  scenarios.forEach((item) => {
    grid.appendChild(card(item.name, `${item.probability}%`, `目标价：${item.target_price || missing}；触发：${item.trigger}`));
  });
}

function renderValuation(valuation, note) {
  const panel = document.querySelector("#valuationPanel");
  panel.innerHTML = "";
  const fields = [
    ["当前价格", valuation.current_price],
    ["基准目标价", valuation.target_price_base],
    ["风险下行价", valuation.downside_price],
    ["上行空间", valuation.upside_pct],
    ["下行空间", valuation.downside_pct],
    ["R/R", valuation.rr],
    ["PE", valuation.pe_ratio],
    ["FCF yield", valuation.fcf_yield_pct],
    ["仓位建议", valuation.position],
    ["来源日期", valuation.source_date],
    ["抓取日期", valuation.captured_at],
    ["状态", valuation.status],
  ];
  fields.forEach(([label, value]) => panel.appendChild(card(label, value || missing, "")));
  const lock = document.createElement("p");
  lock.className = valuation.trading_eligible ? "" : "locked";
  lock.textContent = note;
  panel.appendChild(lock);
}

function renderPosition(position) {
  const panel = document.querySelector("#valuationPanel");
  const fields = [
    ["持股数", position.shares],
    ["平均成本", position.avg_cost],
    ["仓位占比", position.position_weight_pct],
    ["仓位状态", position.status],
  ];
  fields.forEach(([label, value]) => panel.appendChild(card(label, value || missing, "")));
}

function renderPriceSensitivity(sensitivity) {
  const summary = document.querySelector("#priceSensitivitySummary");
  const body = document.querySelector("#priceSensitivityRows");
  body.innerHTML = "";
  if (!sensitivity) {
    summary.textContent = "价格敏感性数据缺失";
    return;
  }
  summary.className = sensitivity.available ? "gate-summary open" : "gate-summary locked";
  summary.innerHTML = `<strong></strong><span></span><p></p>`;
  summary.querySelector("strong").textContent = sensitivity.available ? "价格区间已生成" : "价格区间未生成";
  summary.querySelector("span").textContent =
    `可买 ${sensitivity.buy_below}；持有 ${sensitivity.hold_range}；减仓复盘 ${sensitivity.reduce_review_above}`;
  summary.querySelector("p").textContent = `${sensitivity.summary} ${sensitivity.methodology}`;
  (sensitivity.rows || []).forEach((item) => {
    body.appendChild(row([item.price, item.upside_pct, item.downside_pct, item.rr, item.decision]));
  });
}

function renderValuationScenarios(matrix) {
  const summary = document.querySelector("#valuationScenarioSummary");
  const body = document.querySelector("#valuationScenarioRows");
  body.innerHTML = "";
  if (!matrix) {
    summary.textContent = "估值情景矩阵数据缺失";
    return;
  }
  summary.className = matrix.available ? "gate-summary open" : "gate-summary locked";
  summary.innerHTML = `<strong></strong><span></span><p></p>`;
  summary.querySelector("strong").textContent = matrix.available ? "情景矩阵已生成" : "情景矩阵未生成";
  summary.querySelector("span").textContent = `当前价 ${matrix.current_price || missing}`;
  summary.querySelector("p").textContent =
    `${matrix.summary}${(matrix.gaps || []).length ? ` 数据缺口：${matrix.gaps.join("；")}` : ""}`;
  (matrix.rows || []).forEach((item) => {
    body.appendChild(
      row([
        item.label,
        item.target_price,
        item.downside_price,
        item.buy_below,
        item.current_rr,
        item.current_decision,
      ])
    );
  });
}

function renderMissingInputs(items) {
  const grid = document.querySelector("#missingInputs");
  grid.innerHTML = "";
  items.forEach((item) => grid.appendChild(card(item, "", "")));
}

function renderEvidence(evidence) {
  const body = document.querySelector("#evidenceRows");
  body.innerHTML = "";
  evidence.forEach((item) => {
    body.appendChild(row([
      item.metric,
      `${item.value}${item.unit || ""}`,
      item.source_id,
      item.published_date,
      item.verified_status,
      item.stale_status,
    ]));
  });
}

function renderRisks(risks, triggers) {
  const riskGrid = document.querySelector("#riskGrid");
  riskGrid.innerHTML = "";
  risks.forEach((risk) => riskGrid.appendChild(card(risk, "", "")));

  const triggerGrid = document.querySelector("#triggerGrid");
  triggerGrid.innerHTML = "";
  triggerGrid.appendChild(card("加仓条件", "", triggers.add));
  triggerGrid.appendChild(card("减仓条件", "", triggers.reduce));
  triggerGrid.appendChild(card("退出条件", "", triggers.exit));
}

function renderLogs(logs) {
  const body = document.querySelector("#logRows");
  body.innerHTML = "";
  logs.forEach((item) => body.appendChild(row([item.date, item.period, item.action, item.score, item.change_reason || ""])));
}

function renderDecisionPlans(plans) {
  const list = document.querySelector("#decisionPlanList");
  list.innerHTML = "";
  if (!plans.length) {
    list.appendChild(recordCard({
      planned_action: "暂无人工方案",
      decision_type: "等待输入",
      date: "",
      reason: "在左侧输入加仓、减仓、持有或复盘方案后，会显示在这里。",
    }));
    return;
  }
  plans.slice().reverse().forEach((item) => list.appendChild(recordCard(item)));
}

function recordCard(item) {
  const el = document.createElement("div");
  el.className = "record-card";
  const title = `${item.planned_action || missing} · ${item.decision_type || missing}`;
  const meta = [item.date, item.ticker, item.trigger_price ? `触发价 ${item.trigger_price}` : "", item.rr_at_decision ? `R/R ${item.rr_at_decision}` : ""]
    .filter(Boolean)
    .join(" · ");
  el.innerHTML = `<strong></strong><p class="meta"></p><p class="reason"></p><p class="review"></p>`;
  el.querySelector("strong").textContent = title;
  el.querySelector(".meta").textContent = meta || "数据缺失";
  el.querySelector(".reason").textContent = item.reason || "未填写理由";
  el.querySelector(".review").textContent = `复盘：${item.review_result || "待复盘"}；${item.review_notes || item.review_date || ""}`;
  return el;
}

function renderReviews(reviews) {
  const grid = document.querySelector("#reviewGrid");
  grid.innerHTML = "";
  reviews.forEach((item) => grid.appendChild(card(item.window, "", item.focus)));
}

function card(title, metric, detail) {
  const el = document.createElement("div");
  el.className = "item";
  el.innerHTML = `<h3></h3>${metric ? `<div class="metric"></div>` : ""}<p></p>`;
  el.querySelector("h3").textContent = title;
  if (metric) el.querySelector(".metric").textContent = metric;
  el.querySelector("p").textContent = detail || "";
  return el;
}

function row(values) {
  const tr = document.createElement("tr");
  values.forEach((value) => {
    const td = document.createElement("td");
    td.textContent = value || missing;
    tr.appendChild(td);
  });
  return tr;
}

function saveForm(endpoint, form, reload = true) {
  const payload = Object.fromEntries(new FormData(form).entries());
  setSaveStatus("正在保存", "neutral");
  fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((response) => response.json())
    .then((result) => {
      if (!result.ok) throw new Error(result.error || "保存失败");
      setSaveStatus("已保存", "green");
      if (reload) {
        window.location.reload();
      } else {
        form.reset();
        window.location.reload();
      }
    })
    .catch((error) => {
      setSaveStatus(`保存失败：${error.message}`, "red");
    });
}

function setSaveStatus(message, tone) {
  const el = document.querySelector("#saveStatus");
  el.textContent = message;
  el.className = `status-pill ${tone || "neutral"}`;
}

function money(value) {
  if (!value || value === missing) return missing;
  return String(value).startsWith("$") ? value : `$${value}`;
}
