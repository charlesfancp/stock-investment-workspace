# AI 基础设施投资系统规则

本项目用于跟踪 AI 基础设施“版本 B”股票组合，生成投研判断、风险提示、再平衡建议和人工复核材料。系统是投研辅助系统，不是自动交易系统。

## 项目范围

版本 B 组合包括 NVDA、TSM、AVGO、GOOGL、AMZN、MU、GEV、VRT、ETN、DLR。研究重点是算力、先进制造、ASIC/AI 网络、云、HBM、电力、散热、数据中心地产等 AI 基础设施链条。

## 数据纪律

- 正式判断必须保留来源、发布日期或报告期、抓取时间、数据口径和核实状态。
- A 类来源优先：公司公告、财报、SEC 文件、IR、交易所文件、官方指引。
- B 类来源可辅助判断：权威数据库、行业报告、主流财经媒体、券商研究。
- C 类来源只可作为线索：社区讨论、社交媒体、未经确认传闻。
- 假设破坏必须由 A 类来源或两个独立 B 类来源确认；确认前只能标记为待核查。
- 缺失字段必须保留 `null` 或“待核查”，不得编造。

## 投研输出

日报、周报、事件报告和组合报告必须输出：

- 当前判断：买入、加仓、持有、减仓、清仓、继续跟踪之一；
- 基准、乐观、风险情景及概率；
- 当前仓位、目标仓位、最大仓位上限；
- 加仓价、减仓价、止损或退出条件；
- 组合相关性、单一主题暴露、现金比例；
- 对原投资逻辑的影响；
- 下次复盘事项。

所有动作都是人工决策输入，不得计算真实下单数量，不得自动交易。

## 文件与人工输入

- `config/positions.yaml` 只能由人工填写或在使用者明确要求下修改。
- `thesis/` 中的单票投资假设卡不得被脚本自动改写。
- Thesis 变更只能人工记录到 `reviews/thesis_change_log.md`。
- 生成的 `data/processed/`、`reports/`、`reviews/` 文件必须保留数据日期和生成时间。

## HTML 控制台

本项目 HTML 控制台应采用决策面板，而不是展示页：

- 顶部显示组合结论、今日动作、更新时间和主要风险；
- 中部显示单票评分、权重偏离、估值风险、事件日历和假设破坏信号；
- 底部显示决策日志、复盘记录和待人工确认事项；
- 数据与判断分离，便于持续更新和复盘。

## 常用命令

生成全部投研数据和报告：

```bash
python3 scripts/run_daily_pipeline.py
```

生成中文日报：

```bash
python3 scripts/generate_daily_report.py
```

生成中文周报：

```bash
python3 scripts/generate_weekly_report.py
```

生成组合风险摘要：

```bash
python3 scripts/build_portfolio_risk.py
```

运行测试：

```bash
python3 -m unittest discover -s tests
```

启动本地投研控制台：

```bash
python3 -m http.server 8765
```

打开：

```text
http://localhost:8765/web/index.html
```
