# 开发计划

## 第 1 周：能跑

目标是建立项目骨架、投资假设卡、数据源纪律，并生成第一版日报。

验收标准：

- 版本 B 组合配置完整。
- 10 只股票 thesis 模板完整。
- 数据源分级和数据质量规则完整。
- 日报脚本即使没有真实数据，也能明确标注“数据缺失”。

## 第 2 周：能评分

目标是实现评分模型和动作建议。

验收标准：

- 每只股票都有 0-100 分。
- 每只股票都有动作：强买入/加仓、买入/持有、持有/观察、减仓、清仓/回避。
- 如果触发 thesis 反转条件，动作必须被强制降级。

## 第 3 周：能读事件

目标是接入公司公告、SEC filing、IR、财报和新闻。

验收标准：

- 事件必须带 source、source_tier、source_date、fetched_at。
- C 类来源只能进入待核查队列。
- 重大结论需要 A 类来源或两个独立 B 类来源。

## 第 4 周：能做组合判断

目标是生成周报和再平衡建议。

验收标准：

- 对比 QQQ、SMH、SOXX。
- 输出组合是否继续版本 B、加仓、减仓、防守或升级版本 C。
- 所有交易仍需人工确认。

## 已完成工程任务

已实现 `scripts/fetch_prices.py`：

- 输入：`config/portfolio.yaml`
- 输出：`data/processed/prices_latest.csv`
- 快照：`data/snapshots/prices_YYYYMMDD.csv`
- 字段：ticker、price、market_cap、pe_ttm、pe_forward、week_52_high、week_52_low、change_percent、ma_20、ma_50、ma_200、source、fetched_at
- 缺失字段填 `null`
- 不允许编造数据

## 已完成工程任务

已实现 `scripts/score_tickers.py`：

- 输入：`data/processed/prices_latest.csv`、`config/portfolio.yaml`、`config/scoring_rules.yaml`、`thesis/*.yaml`
- 输出：`data/processed/scores_latest.csv`
- 字段：ticker、score、action、target_weight、price、main_reason、risk_flags、source_date、fetched_at
- 数据缺失时输出“数据缺失”，不允许编造评分依据
- 如果触发 reversal_triggers，动作必须强制降级

当前版本只有行情和均线数据，因此输出为初版技术面评分，`evidence_coverage` 标记为 `technicals_only`。

## 已完成工程任务

已实现 `scripts/generate_daily_report.py`：

- 输入：`data/processed/prices_latest.csv`、`data/processed/scores_latest.csv`、`config/portfolio.yaml`、`thesis/*.yaml`
- 输出：`reports/daily/YYYYMMDD_daily_report.md`
- 报告语言：中文
- 内容：组合总览、单票评分表、风险提示、触发器检查、今日是否需要动作
- 数据缺失必须明确写出，不能编造基本面或估值结论

## 已完成工程任务

已实现 `config/reversal_triggers.yaml` 和降级复核规则：

- 写入组合层面和单票层面的假设破坏清单
- 在评分和日报中读取这些触发器
- 没有 A 类来源或两个独立 B 类来源时，只能标记“待核查”，不能直接判定假设破坏
- 一旦确认触发，动作必须强制降级为减仓复核或清仓复核

当前版本尚未接入事件证据，因此所有假设破坏状态均为 `pending_evidence`。

## 已完成工程任务

已实现 `scripts/generate_weekly_report.py`：

- 输入：行情、评分、日报、组合配置、假设破坏清单
- 输出：`reports/weekly/YYYYMMDD_weekly_report.md`
- 内容：本周核心结论、组合表现占位、主线评分占位、单票更新、下周事件日历占位、调仓建议
- 在没有基准行情和事件数据时，必须明确写“数据缺失”，不能编造跑赢/跑输结论

## 已完成工程任务

已建立基准行情和组合表现基础：

- 将 QQQ、SOXX、SMH 加入基准配置
- 扩展行情抓取脚本，输出 `data/processed/benchmarks_latest.csv`
- 生成组合与基准的占位对比表
- 在没有实际持仓市值前，不计算真实组合收益

## 已完成工程任务

已建立持仓状态：

- 创建 `config/positions.yaml`
- 记录每只股票的当前仓位、成本、股数或目标资金占比
- 生成 `data/processed/portfolio_state_latest.csv`
- 在周报中展示目标权重、当前权重、偏离幅度
- 没有真实持仓输入时，继续标记“数据缺失”，不估算组合收益

## 已完成工程任务

已建立事件日历：

- 创建 `config/event_calendar.yaml`
- 记录财报、IR、SEC filing、重要产业事件和风险事件
- 生成 `data/processed/event_calendar_latest.csv`
- 在日报和周报中展示未来 14 天事件
- 事件没有来源和日期时，不能进入报告正文，只能进入待补充清单

## 已完成工程任务

已建立一键运行脚本：

- 创建 `scripts/run_daily_pipeline.py`
- 按顺序运行行情、评分、持仓状态、事件日历、日报、周报
- 任一关键步骤失败时退出并显示失败步骤
- 不执行任何交易动作

## 已完成工程任务

已建立自动化运行配置：

- 创建 GitHub Actions 工作流草案
- 工作流只生成数据和报告，不自动交易
- 默认支持手动触发，定时触发先保持注释或文档说明
- 不自动提交，除非后续明确需要机器人提交报告

## 已完成工程任务

已建立数据产物归档规则：

- 明确哪些 `data/processed/` 和 `reports/` 文件应该进入版本管理
- 明确哪些运行产物只作为 artifact 保留
- 添加文档说明本地运行和 CI 运行的产物差异
- 如有需要，拆分 `latest_*` 和日期快照的保存策略

## 已完成工程任务

已建立事件来源补全流程：

- 为 `config/event_calendar.yaml` 增加真实事件示例
- 明确财报日历的首选来源
- 支持从手工录入事件生成报告事件表
- 加测试覆盖 tier_1/tier_2 事件进入报告、tier_3 或缺源事件不进入报告

## 已完成工程任务

已建立事件预警报告：

- 生成 `reports/event/latest_event_report.md`
- 列出未来 14 天 confirmed 事件
- 列出 `needs_source` 待补充事件
- 对 tier_1 财报事件标记为“人工复核重点”
- 不根据事件本身直接生成买卖建议

## 已完成工程任务

已建立事件后复核模板：

- 创建 `docs/event_review_template.md`
- 固定财报后需要检查的指标
- 固定“是否影响原始 thesis”的结论格式
- 支持把事件复核结果人工写回 `config/event_calendar.yaml` 或后续 review log

## 已完成工程任务

已建立事件复核日志：

- 创建 `reviews/event_reviews/` 目录
- 建立复核日志命名规则
- 让事件报告链接到对应复核占位文件
- 复核完成后可以人工记录 thesis strengthened/unchanged/weakened/broken

## 已完成工程任务

已建立 thesis 变更日志：

- 创建 `reviews/thesis_change_log.md`
- 事件复核后如果 thesis 变化，人工记录变化原因
- 记录变化前后结论、证据来源、人工确认人和日期
- 不允许脚本自动改写 thesis

## 已完成工程任务

已建立 thesis 变更日志读取器：

- 增加测试，确保日志包含必要字段
- 增加测试，确保风险文档写明脚本不得自动改 thesis
- 后续如建立脚本，只允许读取日志，不允许写入 thesis

当前日报和周报会读取 `reviews/thesis_change_log.md` 并展示最近人工确认记录。脚本不写入日志，也不改写 `thesis/*.yaml`。

## 已完成工程任务

已建立持仓录入说明：

- 说明如何填写 `config/positions.yaml`
- 说明 shares、average_cost、cash_usd、portfolio_value_usd 的含义
- 给出一个不提交的本地样例
- 强调持仓录入来自人工确认交易

## 已完成工程任务

已建立组合再平衡检查：

- 基于 `portfolio_state_latest.csv` 读取目标权重和当前权重
- 设置权重偏离阈值，例如 2 个百分点
- 输出 `data/processed/rebalance_check_latest.csv`
- 周报显示“需要人工再平衡复核”的标的
- 不自动生成交易数量

## 已完成工程任务

已建立组合风险摘要：

- 读取评分、持仓状态、再平衡检查和事件日历
- 输出 `data/processed/portfolio_risk_latest.csv`
- 覆盖持仓数据缺口、技术面过热、事件密度、基本面覆盖、估值覆盖、再平衡和 thesis 反转风险
- 周报展示组合风险摘要
- 不根据风险摘要直接生成交易数量或自动交易

## 已完成工程任务

已建立 HTML 投研控制台：

- 页面位于 `web/index.html`
- 读取 `data/processed/*.csv` 作为本地投研输入
- 展示组合状态、风险摘要、单票评分、目标权重、事件日历
- 支持本地浏览器记录仓位快照、仓位变化和复盘记录
- 记录保存在浏览器本地存储，不自动改写 `config/positions.yaml`、`thesis/*.yaml` 或真实交易记录

## 下一项工程任务

建立基本面与估值证据输入：

- 已在 `config/fundamentals.yaml` 和 `config/valuation.yaml` 增加来源类型和核实状态字段
- 已在构建脚本中增加来源等级、来源类型、日期、时效和核实状态校验
- 已新增 `docs/evidence_input_guide.md`，说明字段口径、结论资格和录入顺序
- 下一步需要人工填入每只股票的最新财报与估值事实；缺失数据继续保留 `null` 或“待核查”，不得用模型推测替代事实

## 新增主题线索

已建立物理 AI 美股主题 intake：

- 文件：`docs/physical_ai_us_theme_intake.md`
- 当前定位：使用者补充材料整理，未完成独立核验
- 美股重点：NVDA、TSLA、GOOGL、AMZN，以及 GEV、VRT、ETN、DLR 等 AI 数据中心基础设施链条
- 下一步：先核查 NVDA 官方物理 AI / Omniverse / 机器人材料，以及 TSLA Optimus、FSD、Robotaxi 官方进展；核查完成前不改变组合权重
