# AI 基础设施投资判断系统

本项目用于跟踪 AI 基础设施“版本 B”股票组合，并自动生成投研判断报告。

系统定位是自动投研判断系统，不是自动交易系统。机器负责收集数据、评分、触发预警、生成买入/持有/减仓/清仓建议；最终交易必须由人工确认。

## 版本 B 组合

| 股票 | 目标权重 | 角色 |
| --- | ---: | --- |
| NVDA | 20% | 算力核心地段 |
| TSM | 17% | 先进制造地段 |
| AVGO | 11% | ASIC/AI 网络地段 |
| GOOGL | 17% | 数据/模型/入口地段 |
| AMZN | 15% | 云地产 |
| MU | 8% | HBM 瓶颈建材 |
| GEV | 4% | 电力基础设施地段 |
| VRT | 4% | AI 机房电力与散热 |
| ETN | 2% | 电力与液冷稳健补充 |
| DLR | 2% | 带电容量与数据中心地产 |

## 当前阶段

当前已建立项目骨架、投资假设模板和数据源纪律，并提供第一版行情抓取脚本。脚本只生成投研输入数据，不生成交易指令。

## 后续开发计划

1. 接入行情与估值数据，生成 `data/processed/prices_latest.csv`。
2. 实现评分模型，输出每只股票 0-100 分和动作建议。
3. 生成中文日报，检查加仓、减仓、止损、假设破坏触发器。
4. 接入财报、SEC filing、公司 IR、新闻和产业事件。
5. 生成周报，比较 QQQ、SMH、SOXX，并输出再平衡建议。
6. 建立 GitHub Actions 或本地定时任务，自动生成报告但不自动下单。

## 数据纪律

- A 类高可信数据可进入正式判断。
- B 类辅助数据可验证趋势，但重大动作需要二次确认。
- C 类低可信数据只能作为线索，不能直接改变评分或动作建议。
- 每条正式判断必须保留来源、日期和抓取时间。
- 搜索结果不是事实，缺失字段必须填 `null`，不能编造。
- 假设破坏必须由 A 类来源或两个独立 B 类来源确认；确认前只能标记为待核查。

## 本地运行

一键生成全部投研数据和报告：

```bash
python3 scripts/run_daily_pipeline.py
```

生成最新行情表和当日快照：

```bash
python3 scripts/fetch_prices.py
```

生成第一版评分表：

```bash
python3 scripts/score_tickers.py
```

生成基本面数据表：

```bash
python3 scripts/build_fundamentals.py
```

生成估值数据表：

```bash
python3 scripts/build_valuation.py
```

生成中文日报：

```bash
python3 scripts/generate_daily_report.py
```

生成中文周报：

```bash
python3 scripts/generate_weekly_report.py
```

生成持仓状态表：

```bash
python3 scripts/build_portfolio_state.py
```

生成再平衡人工复核表：

```bash
python3 scripts/check_rebalance.py
```

生成组合风险摘要：

```bash
python3 scripts/build_portfolio_risk.py
```

生成事件日历：

```bash
python3 scripts/build_event_calendar.py
```

生成事件预警报告：

```bash
python3 scripts/generate_event_report.py
```

运行测试：

```bash
python3 -m unittest discover -s tests
```

启动本地投研控制台：

```bash
python3 -m http.server 8765
```

打开最终决策面板：

```text
http://localhost:8765/web/index.html
```

不要直接用 `file://` 打开 `web/index.html`，否则浏览器无法读取 `data/processed/*.csv`，页面会缺数据。

## 自动化运行

已提供 GitHub Actions 草案：`.github/workflows/research-pipeline.yml`。

- 仅支持手动触发。
- 只运行测试和投研报告生成。
- 只上传报告和数据为 artifact。
- 不提交文件，不推送，不执行交易。

## 数据产物归档

生成的行情、评分、日报和周报默认不进入版本管理，只保留在本地或 CI artifact。

详细规则见 `docs/artifact_policy.md`。

## 证据录入

基本面和估值输入说明见 `docs/evidence_input_guide.md`。

- `config/fundamentals.yaml` 和 `config/valuation.yaml` 只接受人工确认后的数据。
- 数据必须保留来源、链接、来源等级、来源类型、日期和核实状态。
- 未核实、过期或低可信来源不会被标记为可进入结论。

## 主题线索

物理 AI 美股主题 intake 见 `docs/physical_ai_us_theme_intake.md`。

- 该文件只整理线索和核查清单，不直接改变组合权重或交易动作。
- 美股重点包括 NVDA、TSLA、GOOGL、AMZN，以及现有电力、散热和数据中心链条。
- 未经官方来源或交叉验证的订单、量产和客户关系不得进入正式结论。

## 事件复核

事件后人工复核使用 `docs/event_review_template.md`。

当前已建立 NVDA 2026-05-20 财报事件复核占位：`docs/nvda_event_review_2026-05-20.md`。

事件复核日志位于 `reviews/event_reviews/`，索引文件为 `reviews/event_reviews/index.md`。

Thesis 变更只能人工记录到 `reviews/thesis_change_log.md`，脚本不得自动改写 `thesis/*.yaml`。

日报和周报会读取 thesis 变更日志并展示最近人工确认记录；没有记录时显示暂无变化。

## 持仓录入

持仓录入说明见 `docs/positions_guide.md`。

真实持仓只能人工填写到 `config/positions.yaml`，系统不会自动推断或自动修改持仓。

## 目录结构

- `config/`：组合、评分和数据源规则。
- `thesis/`：单票投资假设卡。
- `data/raw/`：原始数据。
- `data/processed/`：清洗后的结构化数据。
- `data/snapshots/`：带日期的数据快照。
- `scripts/`：抓取、评分和报告生成脚本。
- `reports/daily/`：日报。
- `reports/weekly/`：周报。
- `reports/event/`：事件预警。
- `tests/`：测试。
- `docs/`：方法论和风控说明。

## 当前可生成文件

- `data/processed/prices_latest.csv`：版本 B 股票行情。
- `data/processed/benchmarks_latest.csv`：QQQ、SOXX、SMH 基准行情。
- `data/processed/fundamentals_latest.csv`：人工确认基本面输入的结构化表；缺失字段保留 `null`。
- `data/processed/valuation_latest.csv`：人工确认估值输入的结构化表；缺失字段保留 `null`。
- `data/processed/portfolio_state_latest.csv`：真实持仓输入和目标权重偏离；未填写持仓时标记为数据缺失。
- `data/processed/rebalance_check_latest.csv`：权重偏离人工复核信号；不计算交易数量，不自动下单。
- `data/processed/portfolio_risk_latest.csv`：组合风险摘要；汇总持仓、过热、事件密度、证据覆盖和再平衡状态。
- `data/processed/event_calendar_latest.csv`：未来事件日历；缺少来源或日期的事件不会进入正式报告。
- `data/processed/scores_latest.csv`：初版技术面评分。
- `reports/daily/latest_daily_report.md`：中文日报。
- `reports/weekly/latest_weekly_report.md`：中文周报。
- `reports/event/latest_event_report.md`：事件预警报告。
