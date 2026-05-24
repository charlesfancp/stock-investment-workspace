# 关键证据

## EV-2026-0001

事实：`1024.HK` 最新可用收盘价为 `44.98 HKD`，日期为 `2026-05-21`；当日跌幅 `-5.66%`，成交量 `70,062,100` 股。

来源：`data/processed/market_prices.csv`，Yahoo Finance chart API 抓取。

状态：已核实，可进入结论。价格类数据时效较短，下一交易日后需刷新。

## EV-2026-0002

事实：按 `49.34 HKD`、预算 `100,000 HKD`、每手 `100 股`计算，已记录模拟买入 `20 手 / 2,000 股`，预计占用 `98,680 HKD`，剩余 `1,320 HKD`。

来源：`data/processed/position_records.csv`。

状态：已核实，可进入复盘；不含佣金、印花税、平台费和滑点。

## EV-2026-0003

事实：基准 SOTP 目标价为 `77.63 HKD`，相对 `44.98 HKD`上行 `72.59%`。

来源：`data/processed/valuation_history.csv`，假设来自 `config/valuation_assumptions.yaml`。

状态：模型推算，可进入情景判断；估值假设仍需持续用公告、财报和可灵融资事实校验。

## EV-2026-0004

事实：最近一次成功 HKEX 标题搜索使用快手 `stockId=1000077859`，解析 `99` 条公告；`2026-05-21` HKEX 刷新超时，未完成当日公告核验。

来源：`reports/daily/latest_run_log.md` 与 `data/raw/hkex_announcements/`。

状态：已核实，可作为公告完整性检查依据。

## EV-2026-0005

事实：公开可查分析师观点区间包含摩根大通 `48 HKD`、花旗 `72 HKD`、美银 `77 HKD`、高盛 `87 HKD`、中银国际 `60 HKD`、华安证券 `86 HKD`。

来源：`data/processed/analyst_views.csv`。

状态：二手公开来源，当前仅作市场预期线索；正式引用前应补券商原文或更高可信来源。

## EV-2026-0006

事实：按 `44.98 HKD`、预算 `100,000 HKD`、每手 `100 股`计算，可买 `22 手 / 2,200 股`，预计占用 `98,956 HKD`，剩余 `1,044 HKD`。

来源：`data/processed/market_prices.csv` 与 `config/trade_settings.yaml`。

状态：已核实，可进入测算；不含佣金、印花税、平台费和滑点。
