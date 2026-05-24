# NVDA 事件复核 - 2026-05-20

本文件用于 2026-05-20 NVIDIA 1st Quarter FY27 Financial Results 事件后的人工复核。

事件来源：

- [NVIDIA FY2027Q1 earnings release](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2027)
- [NVIDIA Q1FY27 CFO Commentary](https://s201.q4cdn.com/141608511/files/doc_financials/2027/Q127/Q1FY27-CFO-Commentary.pdf)

## 已核实事件信息

- 来源等级：tier_1
- 来源类型：original
- 发布日期：2026-05-20
- 核实日期：2026-05-20
- 事件时间：2026-05-20 14:00 PT / 17:00 ET
- 覆盖期间：FY2027Q1，截至 2026-04-26
- 核实状态：verified for earnings release and CFO commentary

## 复核重点

- Data Center revenue growth：752.46 亿美元，同比增长 92%，环比增长 21%。
- Gross margin：GAAP / non-GAAP 为 74.9% / 75.0%。
- Networking revenue growth：按旧口径，Data Center networking revenue 为 148 亿美元，同比增长 199%，环比增长 35%。
- Hyperscaler / AI cloud commentary：新口径中 Hyperscale 为 378.69 亿美元，ACIE 为 373.77 亿美元，Data Center 收入约各占一半。
- Backlog or supply commentary：CFO commentary 披露 total supply-related commitments 为 1190 亿美元；multi-year cloud service commitments 为 300 亿美元。
- Blackwell/Rubin progress：CFO commentary 披露 Blackwell 300 ramp；本次材料未确认 Rubin 延期或具体出货延迟。
- China/H20 export-control impact：Q1 未向中国发货 Data Center Hopper；Q2 outlook 未假设任何来自中国的 Data Center compute revenue。
- FY2027Q2 revenue and gross-margin outlook：收入 910 亿美元 +/-2%；GAAP / non-GAAP gross margin 74.9% / 75.0% +/-50 bps。
- Physical AI / robotics / Omniverse incremental evidence：NVIDIA 新增 Edge Computing 平台叙事，覆盖 agentic and physical AI devices；同时披露 Alpamayo 1.5、Omniverse NuRec、Cosmos、Isaac GR00T N、IGX Thor 和 DRIVE Hyperion 等线索，但仍未单独披露收入。

## 触发器映射

- `gross_margin_down_two_quarters`：毛利率是否连续两个季度下降。
- `data_center_growth_below_30_percent`：Data Center 收入增速是否跌破 30%。
- `blackwell_or_rubin_delay`：Blackwell 或 Rubin 是否出现重大延期。
- `nvda_data_center_guidance_miss`：数据中心收入或相关指引是否明显低于预期。

## 复核状态

- 当前状态：thesis_strengthened
- 历史状态：pending_event 已在 NVIDIA FY2027Q1 财报发布后关闭。
- 事件后复核已按 `docs/event_review_template.md` 完成。
- 复核结论不自动触发交易，必须人工确认。

## 人工复核结论

```text
事件结论：NVIDIA FY2027Q1 财报强化 Version B 的上游 AI 基础设施主线。
对原始 thesis 的影响：thesis_strengthened。
是否触发假设破坏：未触发。
建议动作：no_action_review_only。
需要补充的数据：10-Q、电话会 Q&A、Rubin 具体出货节奏、China/H20 后续政策影响、physical AI 可量化收入。
人工确认状态：required。
```
