# 每日更新 Prompt

请更新 `/Users/fan/Documents/New project/li-auto-investment-system` 的 LI vs XPEV 双标的决策系统。

要求：
- 先用 `source-integrity` 核实当天新增价格、公告、交付、新闻来源和日期。
- 新事实写入 `evidence/source_index.csv`、`evidence/li_evidence.md`、`evidence/xpev_evidence.md`。
- 更新 `dashboard/data.json` 和 `decision_log/daily_decision_log.md`。
- 最后必须输出：继续跟踪、买LI、买XPEV、双持观察、加仓谁、减仓谁、两者回避之一。
- 所有动作都是研究建议，不是交易指令。
