# 快手-可灵投资研究跟踪系统

本仓库用于跟踪快手科技 `1024.HK` 与可灵 AI 分拆、融资、估值和业务进展，输出可复核的投资研究材料。

系统定位是半自动投研辅助工具：它负责维护事实、假设、估值、触发条件和报告；最终投资决策仍由人工完成。

## 核心目标

- 跟踪港交所公告、快手投资者关系材料、可灵 AI 相关信息、市场价格和重要行业变化。
- 将公告、新闻、财报和人工录入信息沉淀为结构化数据。
- 用统一假设表计算快手核心业务、可灵 AI 和 SOTP 每股价值。
- 每日生成一张可决策简报，明确输出买入、加仓、持有、减仓或卖出。
- 每次投资主线变化都写入日志，避免事后重写逻辑。

## 快速开始

```bash
cd kuaishou-kling-investment-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python models/valuation_engine.py
python scripts/generate_daily_brief.py
```

一键跑每日更新：

```bash
python3 scripts/run_daily_update.py
```

打开本地操作台：

```bash
python3 scripts/dashboard_server.py
```

然后访问 `http://127.0.0.1:8765/`。

操作台支持买入测算与复盘记录：默认按 `config/trade_settings.yaml` 中的 `default_budget_hkd` 和 `board_lot_shares` 计算整手买入数量，记录会写入 `data/processed/position_records.csv`。

生成周度 memo 和反证报告：

```bash
python3 scripts/generate_weekly_memo.py
python3 scripts/generate_bear_case_review.py
```

第一版可以先手动维护：

- `config/valuation_assumptions.yaml`：估值假设。
- `config/alert_rules.yaml`：价格区间和事件触发规则。
- `data/processed/market_prices.csv`：人工或脚本更新的股价数据。
- `data/processed/announcements.csv`：公告和新闻结构化记录。

## 每日流程

1. 运行 `python3 scripts/run_daily_update.py`。
2. 查看 `reports/daily/YYYY-MM-DD-daily-brief.md`。
3. 查看 `reports/daily/valuation_snapshot.md`。
4. 人工确认未核实信息，不把传闻直接写入估值假设。

## 每周流程

1. 运行 `python3 scripts/generate_weekly_memo.py`。
2. 运行 `python3 scripts/generate_bear_case_review.py`。
3. 查看 `reports/weekly/latest_weekly_memo.md` 和 `reports/weekly/latest_bear_case_review.md`。
4. 如投资主线变化，更新 `decision_log/thesis_change_log.md`。

## 数据纪律

- 所有数据必须标注来源、日期和抓取时间。
- 未经核实的传闻不得进入估值模型。
- 超过 3 个月的数据必须标注为过期。
- 券商观点、媒体报道和社区讨论要分层处理，不与官方公告等同。

## 风险提示

本仓库只提供研究、数据整理和估值计算辅助，不构成投资建议。
