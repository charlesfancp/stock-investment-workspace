# NVDA 事件复核 - 2026-05-20

## 基本信息

- ticker: NVDA
- 事件类型: earnings
- 事件日期: 2026-05-20
- 复核日期: 2026-05-20
- 来源: NVIDIA Newsroom; NVIDIA CFO Commentary
- source_tier: tier_1
- source_url: https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2027
- 复核人: Codex draft, human confirmation required

## 事件摘要

- NVIDIA FY2027Q1 revenue 为 816.15 亿美元，同比增长 85%，环比增长 20%。
- Data Center revenue 为 752.46 亿美元，同比增长 92%，环比增长 21%；按旧口径，Data Center compute revenue 为 604 亿美元，同比增长 77%，networking revenue 为 148 亿美元，同比增长 199%。
- GAAP / non-GAAP gross margin 分别为 74.9% / 75.0%；non-GAAP EPS 为 1.87 美元。
- FY2027Q2 revenue outlook 为 910 亿美元 +/-2%，且未假设任何来自中国的 Data Center compute revenue；GAAP / non-GAAP gross margin outlook 分别为 74.9% / 75.0% +/-50 bps。
- 公司宣布新增 800 亿美元回购授权，并将季度股息从每股 0.01 美元提高到 0.25 美元。
- CFO commentary 披露 Blackwell 300 产品 ramp、InfiniBand / Spectrum-X / NVLink 需求、总供应相关承诺 1190 亿美元、multi-year cloud service commitments 300 亿美元；财报新闻稿新增 Edge Computing 平台，覆盖 agentic 和 physical AI 设备。

## 必查指标

- data_center_revenue_growth
- gross_margin
- networking_revenue_growth
- hyperscaler_capex_commentary
- backlog_or_supply_commentary
- Blackwell/Rubin progress
- China/H20 export-control impact
- FY2027Q2 revenue and gross-margin outlook
- physical AI / robotics / Omniverse incremental evidence

## Thesis 影响判断

- 当前状态: thesis_strengthened
- 判断依据:
  - Data Center 收入同比 92%，显著高于 `data_center_growth_below_30_percent` 触发器阈值。
  - 毛利率维持 75% 左右，未出现连续两个季度结构性下滑。
  - Networking 同比 199%，强化 NVDA 从单芯片到系统级 AI factory 平台的逻辑。
  - FY2027Q2 收入指引 910 亿美元，高于会议纪要中 900 亿美元以上的乐观锚，且未纳入中国 Data Center compute 收入。
  - physical AI / robotics / automotive / Omniverse 线索进入 Edge Computing 平台叙事，但仍缺少单独收入拆分，不能单独提高估值假设。

## 触发器检查

- 触发器名称: gross_margin_down_two_quarters; data_center_growth_below_30_percent; blackwell_or_rubin_delay; nvda_data_center_guidance_miss
- 证据来源: NVIDIA FY2027Q1 earnings release; Q1FY27 CFO Commentary
- 是否满足确认规则: 是，tier_1 官方来源
- 需要第二来源: 不需要；但 Rubin 具体延期/出货节奏未在本次官方材料中确认，相关会议纪要说法仍需第二来源
- 当前状态: no_trigger_confirmed

| 触发器 | 检查结果 | 状态 |
| --- | --- | --- |
| `gross_margin_down_two_quarters` | GAAP / non-GAAP gross margin 74.9% / 75.0%，环比仅下降 0.1 pct | 未触发 |
| `data_center_growth_below_30_percent` | Data Center revenue 同比 92% | 未触发 |
| `blackwell_or_rubin_delay` | CFO commentary 只确认 Blackwell 300 ramp；未确认 Rubin 延期 | 未触发，Rubin 仍待跟踪 |
| `nvda_data_center_guidance_miss` | Q2 revenue outlook 910 亿美元 +/-2%，且不含中国 Data Center compute revenue | 未触发 |

## 动作建议

- no_action_review_only
- 说明: 本次事件强化 Version B 的 NVDA 算力核心逻辑，但不自动改 thesis、不自动改持仓、不生成交易指令。

## 数据缺口

- 10-Q 尚未在本次复盘中接入；需补充风险因素、客户集中度、库存、采购承诺和地区收入披露。
- 电话会 Q&A 尚未纳入；需关注客户 capex、Blackwell/Rubin 供给、China/H20、竞争 ASIC 和毛利率可持续性。
- physical AI / robotics / Omniverse 仍只有平台和产品线证据，缺少可量化收入或客户采购拆分。
- 会议纪要中关于 Rubin 延期约 1 个月、TSM CoWoS 产能上修等说法仍未由 NVIDIA 官方确认。

## 最终结论

```text
事件结论：NVIDIA FY2027Q1 财报强化 Version B 的上游 AI 基础设施主线。
对原始 thesis 的影响：thesis_strengthened；Data Center、networking、Q2 指引和股东回报均支持 NVDA 继续作为算力核心地段。
是否触发假设破坏：未触发；毛利率、Data Center 增速、Q2 指引均未触发反转条件。
建议动作：no_action_review_only。
需要补充的数据：10-Q、电话会 Q&A、Rubin 具体出货节奏、China/H20 后续政策影响、physical AI 可量化收入。
人工确认状态：required。
```

## Thesis 变更记录

如本次事件改变 NVDA thesis，人工记录到：

`reviews/thesis_change_log.md`
