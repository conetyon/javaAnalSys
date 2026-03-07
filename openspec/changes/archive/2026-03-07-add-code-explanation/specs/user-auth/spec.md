## ADDED Requirements

### Requirement: AI 解释配额管理

系统 SHALL 为每个用户维护 AI 解释功能的每日使用配额。

#### Scenario: 默认配额

- **WHEN** 新用户首次使用 AI 解释功能
- **THEN** 系统自动创建配额记录，`daily_limit=50`

#### Scenario: 管理员无限配额

- **WHEN** 用户角色为 `admin`
- **THEN** 配额检查跳过，不限制使用次数

#### Scenario: 配额每日重置

- **WHEN** 当前日期与 `last_reset_date` 不同
- **THEN** 系统自动将 `used_today` 重置为 0
- **AND** 更新 `last_reset_date` 为当前日期

#### Scenario: 管理员调整用户配额

- **WHEN** 管理员修改某用户的 `daily_limit` 字段
- **THEN** 该用户的每日配额上限变更为新值
- **AND** 变更立即生效

### Requirement: AI 解释请求日志

系统 SHALL 记录所有 AI 解释请求用于审计和统计。

#### Scenario: 记录解释请求

- **WHEN** 用户成功调用 `/api/explain` 或 `/api/explain/chat`
- **THEN** 系统在 `explain_logs` 表记录请求信息
- **AND** 包含 `user_id`, `snippet_id`, `kp_id`, `request_type`, `prompt_tokens`, `completion_tokens`, `latency_ms`

#### Scenario: 查询用户使用统计

- **WHEN** 需要统计某用户的 AI 解释使用情况
- **THEN** 可通过 `explain_logs` 表按 `user_id` 和 `created_at` 查询
