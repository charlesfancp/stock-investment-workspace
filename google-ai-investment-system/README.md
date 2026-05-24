# Google AI Investment System

Alphabet / Google 股票投资方案和季度跟踪系统。第一版只支持手工 CSV 输入，不联网抓取数据。

第一轮目标：输入一行官方财报数据，输出一份有来源、有日期、有触发条件的 Google 投资判断报告。

## 快速运行

```bash
python scripts/generate_report.py
```

如果本机没有 `python` 命令，可先启用本项目虚拟环境，或使用 `python3 scripts/generate_report.py`。

默认读取：

```text
data/raw/alphabet_quarterly_manual.csv
data/raw/valuation_snapshot.csv
data/raw/market_snapshot.csv
data/raw/analyst_snapshot.csv
configs/thresholds.yaml
```

默认输出：

```text
reports/latest_report.md
decision_log/decision_log.csv
dashboard/data.json
```

报告可反复生成。决策日志按 `date + period + ticker + action + score` 去重；完全相同的判断不会重复堆积。如果同一天、同一期、同一 ticker 的 `action` 或 `score` 变化，系统会追加新记录，并在 `change_reason` 中标注“判断变化”。

## 阶段路线

1. Phase 2.5：决策日志去重。
2. Phase 3：趋势图表。
3. Phase 4：HTML 决策面板。
4. Phase 5：手工录入真实估值快照后，第一次生成有 R/R 资格的投资判断。
5. Phase 6：再考虑自动抓 SEC / IR / 价格数据。

Phase 5 之前，报告只能把经营数据强弱作为研究输入；缺少真实估值快照时，不生成 R/R、仓位或真实买入/加仓建议。

## 图表说明

Phase 3 会读取 `data/raw/alphabet_quarterly_manual.csv` 和 `data/raw/valuation_snapshot.csv`，在 `reports/charts/` 下生成趋势图，并自动插入 `reports/latest_report.md`。

当前支持：

- `cloud_revenue_growth.png`：Google Cloud 收入增速趋势。
- `cloud_operating_margin.png`：Google Cloud 经营利润率趋势。
- `search_other_growth.png`：Search & Other 收入增速趋势。
- `capex_vs_fcf.png`：CapEx / revenue 与 FCF margin 对比。
- `fcf_yield_trend.png`：FCF yield 趋势；估值数据不足时不生成。

每张图至少需要 2 个已核实、未过期、字段完整的数据点。有效数据点少于 2 个时，报告显示“历史数据不足，暂不生成趋势图”，不会补猜历史数据。

## HTML 决策面板

Phase 4 面板位于 `dashboard/`：

- `dashboard/index.html`
- `dashboard/styles.css`
- `dashboard/app.js`
- `dashboard/data.json`

数据由以下脚本生成：

```bash
python scripts/build_dashboard_data.py
```

也可以直接运行报告生成脚本，报告和面板数据会一起更新：

```bash
python scripts/generate_report.py
```

因为面板通过 `app.js` 读取 `data.json`，正确打开方式是使用项目内服务脚本：

```bash
python scripts/serve_dashboard.py
```

然后访问：

```text
http://127.0.0.1:8765/
```

如果端口被占用，可换端口：

```bash
python scripts/serve_dashboard.py --port 8766
```

面板顶部只使用已核实、可进入结论的数据。估值数据缺失时，页面会明确显示“估值数据缺失，不具备买入/加仓资格”。

面板内置三个手工录入区：

- 行情快照：写入 `data/raw/market_snapshot.csv`，用于 GOOG / GOOGL 看盘价格、PE、市值、来源和抓取时间。
- 价格 / 估值快照：写入 `data/raw/valuation_snapshot.csv`，用于当前价格、目标价、下行价、PE、FCF yield、来源和估值方法。
- 仓位快照：写入 `data/raw/position_snapshot.csv`，用于持股数、成本、当前价格、仓位占比和账户口径。

保存后服务会自动刷新 `dashboard/data.json`。这些输入仍然是人工确认数据，不会联网抓取，也不会自动下单。

面板会显示 `R/R 解锁状态`：

- 未解锁：缺少当前价格、基准目标价、风险下行价、PE、FCF yield、来源、抓取日期或估值方法时，动作只能是“继续跟踪 / 待核实”。
- 已解锁：估值快照完整且未过期时，系统显示上行空间、下行空间和 R/R，但目标价区间仍标注为“模型假设，不是已验证事实”，真实交易必须人工确认。

面板也包含 `Google I/O 2026 事件影响` 区块。该区块只使用已绑定官方来源的事实，当前作为产品、模型、Agent、基础设施和商业化跟踪项，不直接解锁买入、加仓、R/R 或仓位建议。

面板包含 `投行与共识目标价` 区块，读取 `data/raw/analyst_snapshot.csv`。该表只保存公开可核实的二手新闻或聚合目标价，用于外部参考和交叉检查；原始投行研报未取得时必须在 notes 中说明，不能直接替代自有估值方法。

### 行情快照

`data/raw/market_snapshot.csv` 用于展示看盘价格，不直接解锁 R/R 或仓位建议。字段包括：

- `date`：快照日期。
- `ticker`：证券代码。
- `share_class`：股权类别，例如 Class A / Class C。
- `current_price`：当前或最近收盘价格。
- `market_cap_usd_bn`：市值，十亿美元。
- `pe_ratio`：PE 倍数。
- `price_change_pct`：当日涨跌幅。
- `regular_close_time`：常规交易收盘时间。
- `pre_market_price`：盘前价，仅作看盘参考。
- `source_name` / `source_url`：行情来源。
- `captured_at`：本地记录时间。
- `notes`：数据限制。

## 数据纪律

- 无来源、无日期、未核实的数据不得进入结论区。
- 缺失字段显示“数据缺失”。
- 数据超过 3 个月显示“过期”。
- 只有 `verified_status=已核实` 且来源、发布日期、报告期、抓取日期、口径完整的数据参与评分。
- 2026Q1 数据必须先核实 Alphabet Q1 2026 earnings release、SEC Exhibit 99.1、Form 10-Q 等官方来源，再写入 `data/raw/alphabet_quarterly_manual.csv`。
- Cloud backlog 使用前必须标注 2026Q1 10-Q 的口径变化；不得把 backlog 环比大幅上升直接当作纯订单加速。

## 固定工作流

```text
source-integrity -> evidence-vault-rag -> variant-perception-thesis -> Python 评分系统 -> decision-dashboard-system
```

## CSV 字段

见 `data/raw/alphabet_quarterly_manual.csv`。第一行保留完整字段；样例行是待核实占位，不用于形成高置信度结论。

### 财报数据字段

- `metric`：指标名称，需与评分配置中的指标名一致。
- `value`：指标值；缺失时填“数据缺失”。
- `unit`：单位，例如 `%`、`USD bn`、`x`。
- `period`：报告期，例如 `2026Q1`。
- `source_name`：来源名称，例如 Alphabet Q1 earnings release。
- `source_url`：来源链接；缺失时不得进入高置信结论。
- `published_date`：来源发布日期。
- `accessed_date`：本地录入或核实日期。
- `methodology`：口径或计算方法。
- `verified_status`：核实状态，例如 `已核实`、`待核实`。
- `notes`：补充说明，尤其是口径变化、估算和限制。

### 估值快照字段

`data/raw/valuation_snapshot.csv` 用于手工录入当前价格和估值。第一版不联网抓行情，不自动补价格。

- `date`：估值快照日期。
- `ticker`：证券代码，例如 `GOOG` 或 `GOOGL`，需核实交易市场。
- `current_price`：当前价格。
- `target_price_base`：基准情景目标价，用于计算上行空间；必须注明人工估值方法。
- `downside_price`：风险情景下行价，用于计算下行空间；必须注明人工估值方法。
- `market_cap_usd_bn`：市值，十亿美元。
- `diluted_shares_bn`：稀释股本，十亿股。
- `pe_ratio`：PE 倍数。
- `fcf_yield_pct`：自由现金流收益率。
- `ev_to_fcf`：企业价值 / 自由现金流。
- `net_cash_usd_bn`：净现金，十亿美元。
- `source_url`：价格和估值来源链接。
- `source_date`：来源日期或交易日。
- `captured_at`：抓取或手工录入日期。
- `valuation_methodology`：目标价、下行价、倍数和 R/R 的人工估值口径。
- `notes`：口径、币种、是否盘中/收盘、数据限制。

缺少 `current_price`、`target_price_base`、`downside_price`、`pe_ratio`、`fcf_yield_pct`、`source_url`、`captured_at` 或 `valuation_methodology` 时，报告必须标注“估值数据缺失”，动作建议只能是“继续跟踪 / 待核实”。系统会自动计算上行空间、下行空间和 R/R，但这只是人工决策输入，不是自动交易指令。

### 决策日志字段

`decision_log/decision_log.csv` 由报告生成脚本追加，用于复盘每次系统判断。

- `date`：报告生成日期。
- `run_id`：日志唯一运行标识，默认由 `date + period + ticker + action + score` 组成。
- `generated_at`：报告生成脚本运行时间。
- `period`：财报报告期。
- `ticker`：证券代码；估值快照缺失时显示“数据缺失”。
- `current_price`：当前价格；缺失时显示“数据缺失”。
- `score`：综合评分。
- `action`：动作建议。
- `confidence`：置信度。
- `key_evidence`：核心证据。
- `contrary_evidence`：反方证据或未核实风险。
- `add_trigger`：加仓触发条件。
- `reduce_trigger`：减仓触发条件。
- `exit_trigger`：退出触发条件。
- `next_review_date`：下次复盘日期。
- `change_reason`：变化原因；同日同报告期同 ticker 但 action 或 score 变化时标注“判断变化”。
