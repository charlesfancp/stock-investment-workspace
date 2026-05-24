# Thesis 变更日志

本日志用于记录投资假设的人工确认变更。

脚本不得自动改写 thesis。任何 thesis 变更必须由人工复核后记录在本文件，再手动更新 `thesis/*.yaml`。

## 记录格式

| 日期 | ticker | 事件/来源 | 原 thesis 状态 | 新 thesis 状态 | 变化原因 | 证据等级 | 确认人 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 状态选项

- thesis_strengthened
- thesis_unchanged
- thesis_weakened
- thesis_broken_pending_confirmation
- thesis_broken_confirmed

## 后续动作选项

- no_action_review_only
- maintain_watch
- upgrade_review
- reduce_review
- sell_review

## 使用规则

- 必须填写事件或来源。
- 必须填写证据等级：tier_1、two_independent_tier_2、tier_2_only、tier_3_watch_only。
- `thesis_broken_confirmed` 只能由 tier_1 或两个独立 tier_2 来源支持。
- 日志记录不等于交易指令。
- 交易动作必须另行人工确认。

## 待填记录

| 日期 | ticker | 事件/来源 | 原 thesis 状态 | 新 thesis 状态 | 变化原因 | 证据等级 | 确认人 | 后续动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
