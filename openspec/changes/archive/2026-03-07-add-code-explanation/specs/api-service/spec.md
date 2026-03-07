## ADDED Requirements

### Requirement: 代码解释端点

系统 SHALL 提供 AI 驱动的代码解释端点，支持 SSE 流式响应。

#### Scenario: 解释代码片段

- **WHEN** POST 请求发送至 `/api/explain`，请求体为 `{"snippet_id": 123, "kp_id": 10011}`
- **THEN** 系统通过 SSE 流式返回 AI 生成的代码解释
- **AND** 每个 SSE 事件包含 `{"type": "content", "content": "..."}`
- **AND** 最后一个事件为 `{"type": "done", "tokens": {...}}`

#### Scenario: 多轮问答

- **WHEN** POST 请求发送至 `/api/explain/chat`，请求体包含 `question` 和可选的 `session_id`
- **THEN** 系统基于代码片段和对话历史回答问题
- **AND** 支持"换一个例子"等请求，AI 会生成更合适的示例

#### Scenario: SSE 流式错误处理

- **WHEN** LLM API 调用超时或返回错误
- **THEN** 系统发送 SSE 错误事件 `{"type": "error", "error": "LLM 服务暂时不可用，请稍后重试"}`
- **AND** 关闭 SSE 连接

#### Scenario: 客户端断开连接

- **WHEN** 客户端在流式传输过程中断开连接
- **THEN** 服务端停止向 LLM 请求后续内容
- **AND** 释放相关资源

#### Scenario: 配额不足

- **WHEN** 用户今日配额已耗尽
- **THEN** 响应状态码为 429 Too Many Requests
- **AND** 响应包含 `{"error": "配额已用完", "reset_at": "..."}`

#### Scenario: 请求限流

- **WHEN** 用户在 1 分钟内请求超过 10 次
- **THEN** 响应状态码为 429 Too Many Requests
- **AND** 响应包含 `{"error": "请求过于频繁，请稍后再试", "retry_after": 60}`

#### Scenario: 未登录用户

- **WHEN** 未携带有效 Token 的请求访问解释端点
- **THEN** 响应状态码为 401 Unauthorized
- **AND** 响应包含 `{"error": "请先登录"}`

### Requirement: 配额查询端点

系统 SHALL 提供端点供用户查询当前配额状态。

#### Scenario: 查询配额

- **WHEN** GET 请求发送至 `/api/user/quota`
- **THEN** 响应包含 `daily_limit`, `used_today`, `remaining`, `reset_at` 字段
- **AND** 响应状态码为 200 OK

### Requirement: 匹配结果包含关键行

系统 SHALL 在所有返回代码片段的端点中包含关键行标注信息。

#### Scenario: 返回关键行范围

- **WHEN** 匹配请求成功返回代码片段（包括 list/matrix/composite/composite_matrix 模式）
- **THEN** 每个片段包含 `highlight_ranges` 字段
- **AND** 格式为 `[{"start_line": 3, "end_line": 6, "type": "for_statement", "label": "增强for循环"}]`
