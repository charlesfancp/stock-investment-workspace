# LI vs XPEV 中国AI汽车 / 具身智能双标的投资判断系统

本项目从单票理想汽车研究升级为 LI vs XPEV 双标的相对投资决策系统。

核心目标不是资料整理，而是每次更新后输出明确研究动作：继续跟踪、买入 LI、买入 XPEV、LI / XPEV 双持观察、加仓谁、减仓谁或两者都回避。

当前 Phase 1 结论：

- LI：继续跟踪，不在2026Q1财报前主动加仓。
- XPEV：纳入重点观察池，不在2026Q1财报前主动加仓。
- 双标的：双持观察，Q1财报前合计观察仓不超过0%-5%。
- 第一复核点：2026-05-28，LI 与 XPEV 均发布2026Q1财报和电话会。

## 推荐启动提示词

在本项目目录中新开 Codex 对话后，可以直接说：

```text
请基于理想汽车，按 source-integrity、evidence-vault-rag、company-project-primer、decision-dashboard-system 四个技能，建立第一版投资方案设计。先核实来源和日期，再生成证据库、一页纸和 HTML 决策面板。不要把无来源或无日期的数据放进结论区。
```

## 第一轮目标

1. 核实 LI / XPEV 当前证券代码、最新价格、财报、交付数据和重要公告。
2. 建立 `evidence/` 下双标的证据库。
3. 建立 `research/01_li_company_primer.md` 和 `research/02_xpev_company_primer.md`。
4. 建立 `research/03_li_vs_xpev_comparison.md`。
5. 建立评分模型、阈值和催化剂日历。
6. 更新 HTML 决策面板，首页显示 LI vs XPEV 对比。
7. 记录 2026-05-28 财报复核清单。

## 目录结构

- `config/`：项目配置和假设。
- `data/raw/`：原始资料。
- `data/processed/`：清洗后数据。
- `data/snapshots/`：日期快照。
- `evidence/`：证据库、引用映射和时效检查。
- `research/`：投资命题和决策框架。
- `reports/`：日报、周报、事件报告。
- `dashboard/`、`web/`：HTML 决策面板。
- `decision_log/`：主线变化和复盘。
- `models/valuation/`：估值模型。
- `models/scoring/`：评分模型。
- `scripts/`：后续自动化脚本。
- `tests/`：测试。
