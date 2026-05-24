# 基本面与估值证据录入说明

本项目的 `config/fundamentals.yaml` 和 `config/valuation.yaml` 只接受人工确认后的数据。脚本可以读取、校验并生成 CSV，但不得自动改写配置，也不得把未核实信息升级为结论。

## 结论资格

一条基本面或估值数据必须同时满足以下条件，才会在 `data/processed/*_latest.csv` 中标记为 `ready` 和 `conclusion_eligible=true`：

| 字段 | 要求 |
| --- | --- |
| `source` | 明确来源名称，不能只写搜索结果或截图 |
| `source_url` | 原始链接或可追溯链接 |
| `source_tier` | 只能是 `tier_1` 或 `tier_2`；`tier_3` 不得进入结论 |
| `source_type` | `original`、`secondary`、`estimate`、`model` 之一 |
| `source_date` | `YYYY-MM-DD` 格式 |
| `verified_status` | 必须是 `verified` |
| `freshness_status` | 必须是 `current` |

估算、模型输出和二手来源可以保留在配置中，但必须在 `source_type` 标明，且重大动作不能只依赖单一二手来源。

## 基本面字段

`config/fundamentals.yaml` 的最低可用字段：

| 字段 | 口径 |
| --- | --- |
| `period` | 报告期，例如 `FY2026Q1` |
| `revenue_growth_yoy` | 同比收入增速，百分比数字 |
| `gross_margin` | 毛利率，百分比数字 |
| `operating_margin` | 经营利润率，百分比数字 |
| `free_cash_flow` | 自由现金流，注明币种和单位到 `notes` |
| `capex` | 资本开支，注明币种和单位到 `notes` |
| `guidance` | 公司指引摘要，不得改写为已实现事实 |

优先来源：公司 earnings release、10-Q/10-K、20-F、投资者演示、官方电话会文字稿。

## 估值字段

`config/valuation.yaml` 的最低可用字段：

| 字段 | 口径 |
| --- | --- |
| `market_cap` | 市值，注明币种和日期 |
| `pe_forward` | Forward PE，注明数据源和预测口径 |
| `fcf_yield` | 自由现金流收益率，注明使用历史、未来一年还是模型值 |
| `valuation_percentile` | 历史分位或同业分位，必须说明样本窗口 |
| `valuation_commentary` | 简短估值判断，只能基于已核实字段 |

估值数据时效更短，当前规则要求 `source_date` 距生成时间不超过 30 天；超过后会标记为 `freshness:stale`。

## 不得进入结论的信息

- 无来源、无日期、无链接的数据。
- `verified_status` 不是 `verified` 的数据。
- `source_tier=tier_3` 的社区、社交媒体、传闻和截图。
- 只来自模型推算但没有明确标注 `source_type=model` 的数据。
- 超过时效阈值且未标注历史基准用途的数据。

## 推荐录入顺序

1. 先录入 NVDA、TSM、AVGO、GOOGL、AMZN 五个核心权重标的。
2. 每只股票先补最新财报期的基本面，再补估值。
3. 对 MU、GEV、VRT、ETN、DLR 重点补订单、backlog、CapEx、数据中心/电力链条相关指标。
4. 每次录入后运行 `python3 scripts/run_daily_pipeline.py`，检查 `fundamentals_status`、`valuation_status` 和 `data_gaps`。
