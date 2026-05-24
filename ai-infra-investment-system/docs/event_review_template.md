# 事件后复核模板

本模板用于财报、IR、SEC filing、产业事件或风险事件之后的人工复核。

系统可以提示事件和整理事实，但最终结论必须由人工确认。事件复核结果不自动触发交易。

## 基本信息

- ticker:
- 事件类型:
- 事件日期:
- 复核日期:
- 来源:
- source_tier:
- source_url:
- 复核人:

## 事件摘要

用 3-5 条事实描述事件，不写主观判断。

- 
- 
- 

## 必查指标

### NVDA

- data_center_revenue_growth
- gross_margin
- networking_revenue_growth
- hyperscaler_capex_commentary
- backlog_or_supply_commentary
- Blackwell/Rubin progress

### TSM

- advanced_node_revenue_mix
- CoWoS capacity and utilization
- AI customer demand
- gross_margin
- capex_guidance

### AVGO

- AI revenue growth
- custom ASIC pipeline
- networking revenue growth
- hyperscaler customer commentary
- free_cash_flow

### GOOGL

- Google Cloud growth
- search revenue growth
- AI product adoption
- capex efficiency
- antitrust risk update

### AMZN

- AWS revenue growth
- AWS operating margin
- capex growth
- free_cash_flow
- Trainium/Inferentia adoption

### MU

- HBM revenue
- HBM pricing
- gross_margin
- inventory_days
- supply commentary

### GEV

- data_center_orders
- gas_turbine_backlog
- electrification revenue growth
- segment margin
- free_cash_flow

### VRT

- liquid_cooling_orders
- data_center_backlog
- organic revenue growth
- adjusted operating margin
- hyperscaler commentary

### ETN

- electrical_orders
- data_center_exposure
- margin
- backlog
- Boyd or liquid cooling integration progress

### DLR

- leasing_backlog
- renewal_spreads
- development_pipeline
- financing_cost
- occupancy

## Thesis 影响判断

选择一个结论：

- thesis_strengthened
- thesis_unchanged
- thesis_weakened
- thesis_broken_pending_confirmation
- thesis_broken_confirmed

判断依据：

- 
- 
- 

## 触发器检查

是否触发 `config/reversal_triggers.yaml`：

- 触发器名称:
- 证据来源:
- 是否满足确认规则:
- 需要第二来源:
- 当前状态:

## 动作建议

只能选择人工复核动作，不能写交易指令。

- no_action_review_only
- maintain_watch
- upgrade_review
- reduce_review
- sell_review

理由：

- 
- 
- 

## 数据缺口

- 
- 
- 

## 最终结论

用固定格式写：

```text
事件结论：
对原始 thesis 的影响：
是否触发假设破坏：
建议动作：
需要补充的数据：
人工确认状态：
```
