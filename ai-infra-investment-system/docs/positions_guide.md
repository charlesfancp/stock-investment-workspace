# 持仓录入说明

`config/positions.yaml` 用于人工录入真实持仓。

系统不会自动推断持仓，不会自动下单，也不会把目标权重当作真实仓位。

## 字段说明

- `portfolio_value_usd`：组合总资产。可以先留空。
- `cash_usd`：现金余额。可以先留空。
- `as_of`：持仓数据日期，格式为 `YYYY-MM-DD`。
- `shares`：确认成交后的实际股数。
- `average_cost`：确认成交后的平均成本，单位为美元。

## 填写规则

- 只有人工确认交易后，才能填写 `shares` 和 `average_cost`。
- 如果没有真实持仓，保持 `null`。
- 不要为了让报告好看而估算股数。
- `positions.yaml` 是人工输入文件，不由脚本自动改写。

## 本地填写流程

1. 复制样例文件：

```bash
cp docs/examples/positions.example.yaml config/positions.local.yaml
```

2. 在本地填写真实持仓。

3. 如需让系统读取本地文件，先手动把内容复制到 `config/positions.yaml`，再运行：

```bash
python3 scripts/build_portfolio_state.py
python3 scripts/generate_weekly_report.py
```

## 输出解释

`data/processed/portfolio_state_latest.csv` 会输出：

- `target_weight`：目标权重，来自 `config/portfolio.yaml`。
- `market_value`：`shares * price`。
- `current_weight`：单票市值 / 已录入持仓总市值。
- `weight_drift`：当前权重 - 目标权重。
- `position_status`：
  - `missing_position_input`：未录入真实持仓。
  - `missing_price`：缺少行情价格。
  - `ready`：可以计算当前权重和偏离。

## 风控边界

- 当前权重偏离不等于交易指令。
- 再平衡建议必须结合 thesis、估值、事件和人工确认。
- 系统不得自动修改持仓文件。
