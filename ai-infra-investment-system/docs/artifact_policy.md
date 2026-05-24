# 数据产物归档规则

本项目区分“系统定义文件”和“运行产物”。

## 进入版本管理

这些文件应进入版本管理：

- `README.md`
- `requirements.txt`
- `.github/workflows/*.yml`
- `config/*.yaml`
- `thesis/*.yaml`
- `scripts/*.py`
- `tests/*.py`
- `docs/*.md`
- `.gitkeep`

这些文件定义系统逻辑、投资假设、数据纪律和自动化流程，应该被审查和追踪。

## 默认不进入版本管理

这些文件由运行流程生成，默认不进入版本管理：

- `data/processed/*.csv`
- `data/snapshots/*.csv`
- `reports/daily/*.md`
- `reports/weekly/*.md`
- `reports/event/*.md`

原因：

- 每次运行都会变化，容易造成噪音。
- 行情和报告应优先作为 CI artifact 或本地输出查看。
- 自动提交生成物可能让仓库历史变成数据流水账。

## 本地运行策略

本地运行 `python3 scripts/run_daily_pipeline.py` 后，可以直接查看：

- `data/processed/prices_latest.csv`
- `data/processed/benchmarks_latest.csv`
- `data/processed/fundamentals_latest.csv`
- `data/processed/valuation_latest.csv`
- `data/processed/scores_latest.csv`
- `data/processed/portfolio_state_latest.csv`
- `data/processed/rebalance_check_latest.csv`
- `data/processed/portfolio_risk_latest.csv`
- `data/processed/event_calendar_latest.csv`
- `reports/daily/latest_daily_report.md`
- `reports/weekly/latest_weekly_report.md`

这些文件可以留在本机，但不建议提交。

## CI 运行策略

GitHub Actions 只上传运行产物为 artifact：

- `data/processed/*.csv`
- `reports/daily/*.md`
- `reports/weekly/*.md`

当前工作流不提交、不推送、不交易。

## 例外规则

如果某一天的报告需要作为正式投资复盘材料，可以人工选择性提交具体日期报告。

提交前必须确认：

- 报告没有未标注来源的事实判断。
- 报告没有自动交易指令。
- 报告明确保留“仅作投研整理，不构成投资建议”。
