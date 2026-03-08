# API Service Capability

## Purpose
Flask-based REST API providing endpoints for knowledge point queries and code snippet matching. Includes CORS support, request validation with Pydantic schemas, and structured error handling.
## Requirements
### Requirement: Knowledge Point Tree Endpoint
The system SHALL provide an endpoint to retrieve the hierarchical tree structure of all knowledge points.

#### Scenario: Get complete knowledge point tree
- **WHEN** GET request is sent to `/api/knowledge/tree`
- **THEN** response contains hierarchical tree structure (L1→L2→L3)
- **AND** each node includes id, name, name_zh (Chinese name), level, and children
- **AND** response status is 200 OK

#### Scenario: Handle tree query error
- **WHEN** GET request to `/api/knowledge/tree` fails due to database error
- **THEN** response status is 500 Internal Server Error
- **AND** response contains error message

### Requirement: Knowledge Point List Endpoint
The system SHALL provide an endpoint to retrieve a flat list of all knowledge points.

#### Scenario: Get all knowledge points
- **WHEN** GET request is sent to `/api/knowledge/list`
- **THEN** response contains flat list of all knowledge points
- **AND** each entry includes kp_id, name, description, level, parent_id
- **AND** response status is 200 OK

### Requirement: Single Knowledge Point Endpoint
The system SHALL provide an endpoint to retrieve details of a specific knowledge point by ID.

#### Scenario: Get existing knowledge point
- **WHEN** GET request is sent to `/api/knowledge/10011`
- **THEN** response contains complete knowledge point details including AST template and keywords
- **AND** response status is 200 OK

#### Scenario: Get non-existent knowledge point
- **WHEN** GET request is sent to `/api/knowledge/99999` (invalid ID)
- **THEN** response status is 404 Not Found
- **AND** response contains error message

### Requirement: Knowledge Point Children Endpoint
The system SHALL provide an endpoint to retrieve all child knowledge points of a given parent.

#### Scenario: Get children of existing parent
- **WHEN** GET request is sent to `/api/knowledge/100/children`
- **THEN** response contains list of child knowledge points
- **AND** response status is 200 OK

#### Scenario: Get children of leaf node
- **WHEN** GET request is sent to children endpoint for a leaf node (L3)
- **THEN** response contains empty list
- **AND** response status is 200 OK

### Requirement: Single Knowledge Point Matching
The system SHALL provide an endpoint to match code snippets to a single knowledge point with configurable parameters.

#### Scenario: Match with default parameters
- **WHEN** POST request to `/api/match` with body `{"kp_id": 10011}`
- **THEN** system uses default weights (0.5, 0.4, 0.1) and thresholds (0.4, 0.4)
- **AND** returns top-5 matching snippets by default
- **AND** response status is 200 OK

#### Scenario: Match with custom difficulty
- **WHEN** POST request to `/api/match` with body `{"kp_id": 10011, "target_difficulty": 0.8}`
- **THEN** system uses specified target difficulty for matching
- **AND** returns matching snippets with difficulty-adjusted scores
- **AND** response status is 200 OK

**Note**: Custom weight parameters (`w_ast`, `w_keyword`, `w_difficulty`) are supported at the service layer for evaluation experiments but not exposed in the public API. The API uses production-optimized default weights from `config/matching.yaml`.

#### Scenario: Match with custom thresholds
- **WHEN** POST request to `/api/match` with body `{"kp_id": 10011, "ast_min_ratio": 0.3, "keyword_min_score": 0.3}`
- **THEN** system uses specified thresholds for filtering
- **AND** may return more results than with default thresholds
- **AND** response status is 200 OK

#### Scenario: Match with custom top_k
- **WHEN** POST request to `/api/match` with body `{"kp_id": 10011, "top_k": 20}`
- **THEN** system returns up to 20 matching snippets
- **AND** response status is 200 OK

#### Scenario: Match with invalid knowledge point ID
- **WHEN** POST request to `/api/match` with body `{"kp_id": 99999}`
- **THEN** response status is 404 Not Found
- **AND** response contains error message "Knowledge point not found"

### Requirement: Batch Knowledge Point Matching
The system SHALL provide an endpoint to match multiple knowledge points independently in a single request.

#### Scenario: Match multiple knowledge points
- **WHEN** POST request to `/api/match/batch` with body `{"kp_ids": [10011, 10012, 10034]}`
- **THEN** system performs independent matching for each knowledge point
- **AND** response contains separate result sets for each kp_id
- **AND** response status is 200 OK

#### Scenario: Batch match with shared parameters
- **WHEN** POST request to `/api/match/batch` with `{"kp_ids": [10011, 10012], "top_k": 5, "ast_min_ratio": 0.5}`
- **THEN** all knowledge points use the same parameters (top_k=5, ast_min_ratio=0.5)
- **AND** response status is 200 OK

### Requirement: Composite Knowledge Point Matching
The system SHALL provide an endpoint to find code snippets demonstrating multiple knowledge points simultaneously.

#### Scenario: Composite match with average aggregation
- **WHEN** POST request to `/api/match/composite` with body `{"kp_ids": [10011, 10012], "score_aggregation": "average"}`
- **THEN** system calculates average score across both knowledge points for each snippet
- **AND** returns snippets with highest composite scores
- **AND** response status is 200 OK

#### Scenario: Composite match with min aggregation
- **WHEN** POST request to `/api/match/composite` with body `{"kp_ids": [10011, 10012], "score_aggregation": "min"}`
- **THEN** system uses minimum score across both knowledge points as composite score
- **AND** returns only snippets that satisfy all knowledge points well
- **AND** response status is 200 OK

#### Scenario: Composite match with sum aggregation
- **WHEN** POST request to `/api/match/composite` with body `{"kp_ids": [10011, 10012], "score_aggregation": "sum"}`
- **THEN** system uses sum of scores across both knowledge points as composite score
- **AND** snippets with broader KP coverage are ranked higher
- **AND** response status is 200 OK

### Requirement: Health Check Endpoint
The system SHALL provide a health check endpoint to verify API service availability.

#### Scenario: Check healthy service
- **WHEN** GET request is sent to `/api/match/health`
- **THEN** response status is 200 OK
- **AND** response contains `{"status": "healthy", "message": "Search service is operational"}`

### Requirement: Request Validation
The system SHALL validate all incoming requests using Pydantic schemas and return meaningful error messages for invalid inputs.

#### Scenario: Reject missing required field
- **WHEN** POST request to `/api/match` with empty body
- **THEN** response status is 422 Unprocessable Entity
- **AND** response contains validation error details

#### Scenario: Reject invalid data types
- **WHEN** POST request to `/api/match` with body `{"kp_id": "invalid_string"}`
- **THEN** response status is 422 Unprocessable Entity
- **AND** response contains type validation error

#### Scenario: Reject out-of-range values
- **WHEN** POST request to `/api/match` with body `{"kp_id": 10011, "ast_min_ratio": 1.5}`
- **THEN** response status is 422 Unprocessable Entity
- **AND** response contains range validation error (thresholds must be 0.0-1.0)

### Requirement: CORS Support
The system SHALL support Cross-Origin Resource Sharing (CORS) to allow browser-based clients from different origins.

#### Scenario: Handle preflight request
- **WHEN** OPTIONS request is sent to any API endpoint
- **THEN** response includes appropriate CORS headers
- **AND** response status is 200 OK

#### Scenario: Include CORS headers in responses
- **WHEN** any API request is processed
- **THEN** response includes `Access-Control-Allow-Origin` header
- **AND** response includes `Access-Control-Allow-Methods` header

### Requirement: Error Response Format
The system SHALL return structured error responses with consistent format for all error conditions.

#### Scenario: Return validation error
- **WHEN** request validation fails
- **THEN** response contains `{"success": false, "error": "description", "details": {...}}`

#### Scenario: Return not found error
- **WHEN** requested resource does not exist
- **THEN** response contains `{"success": false, "error": "Resource not found"}`
- **AND** response status is 404

#### Scenario: Return server error
- **WHEN** unexpected server error occurs
- **THEN** response contains `{"success": false, "error": "Internal server error"}`
- **AND** response status is 500
- **AND** detailed error is logged but not exposed to client

### Requirement: 单知识点矩阵匹配

系统 SHALL 提供端点，将单个知识点的匹配结果按难度级别分组，以矩阵形式返回。

#### Scenario: 默认三级难度分组

- **WHEN** POST 请求发送至 `/api/match/matrix`，请求体为 `{"kp_id": 10011, "per_level": 5}`
- **THEN** 系统返回按 easy/medium/hard 三级分组的代码片段矩阵
- **AND** 每个级别最多包含 5 个片段
- **AND** 响应状态码为 200 OK

#### Scenario: 自定义每级别数量

- **WHEN** POST 请求发送至 `/api/match/matrix`，请求体为 `{"kp_id": 10011, "per_level": 10}`
- **THEN** 系统返回每个难度级别最多 10 个片段的矩阵
- **AND** 响应包含 `shape` 字段表示矩阵维度 `[3, 10]`

#### Scenario: 某难度级别无结果

- **WHEN** 匹配结果中没有符合 "hard" 难度的片段
- **THEN** 响应矩阵中 "hard" 键对应空数组 `[]`
- **AND** 响应状态码仍为 200 OK

#### Scenario: 无效知识点 ID

- **WHEN** POST 请求发送至 `/api/match/matrix`，请求体为 `{"kp_id": 99999}`
- **THEN** 响应状态码为 404 Not Found
- **AND** 响应包含错误消息 "知识点不存在"

### Requirement: 综合知识点矩阵匹配

系统 SHALL 提供端点，将涉及多个知识点的代码片段按难度级别分组，以矩阵形式返回。

#### Scenario: 综合匹配默认参数

- **WHEN** POST 请求发送至 `/api/match/composite/matrix`，请求体为 `{"kp_ids": [10011, 10012], "per_level": 5}`
- **THEN** 系统返回同时涉及两个知识点的代码片段，按难度分组
- **AND** 每个片段包含各知识点的详细得分 `kp_details`
- **AND** 响应状态码为 200 OK

#### Scenario: 综合匹配指定聚合策略

- **WHEN** POST 请求发送至 `/api/match/composite/matrix`，请求体为 `{"kp_ids": [10011, 10012], "score_aggregation": "min"}`
- **THEN** 系统使用最小值聚合策略计算综合得分
- **AND** 只有同时满足所有知识点的片段才会获得高分

#### Scenario: 综合匹配空知识点列表

- **WHEN** POST 请求发送至 `/api/match/composite/matrix`，请求体为 `{"kp_ids": []}`
- **THEN** 响应状态码为 400 Bad Request
- **AND** 响应包含错误消息 "知识点列表不能为空"

### Requirement: 矩阵响应格式

系统 SHALL 使用标准化的矩阵响应格式，包含形状、级别标签和分组数据。

#### Scenario: 标准矩阵响应结构

- **WHEN** 矩阵匹配请求成功处理
- **THEN** 响应包含以下字段：
  - `code`: 状态码 (200)
  - `message`: 响应消息 ("success")
  - `kp_id` 或 `kp_ids`: 查询的知识点
  - `shape`: 矩阵维度 `[m, n]`
  - `levels`: 难度级别名称列表 `["easy", "medium", "hard"]`
  - `per_level`: 每级别片段数
  - `matrix`: 按难度分组的片段字典
  - `total`: 结果总数

### Requirement: AI 代码解释（v1.6.0+）

系统 SHALL 提供 AI 驱动的代码解释功能，支持 SSE 流式响应。

#### Scenario: 基础代码解释

- **WHEN** POST 请求发送至 `/api/explain`，请求体为 `{"snippet_id": 12345, "kp_id": 10011}`
- **THEN** 返回 SSE 流式响应
- **AND** 每个 chunk 格式为 `data: {"type": "content", "content": "..."}`
- **AND** 最后返回 `data: {"type": "done", "tokens": {...}}`

#### Scenario: 多知识点解释（v1.6.1+）

- **WHEN** POST 请求发送至 `/api/explain`，请求体为 `{"snippet_id": 12345, "kp_ids": [10011, 10012]}`
- **THEN** 系统合并多个知识点的关键词和高亮信息
- **AND** Prompt 中组合显示知识点名称（如 "For loop + ArrayList"）
- **AND** 返回针对多知识点的综合解释

#### Scenario: 指定用户级别

- **WHEN** 请求包含 `user_level: "beginner"`
- **THEN** AI 使用适合初学者的语言风格解释代码
- **AND** 支持的级别：beginner, intermediate, advanced

#### Scenario: 配额检查失败

- **WHEN** 用户当日配额已用尽
- **THEN** 响应状态码为 429 Too Many Requests
- **AND** 响应包含 `{"error": "Daily quota exceeded"}`

### Requirement: AI 多轮问答（v1.6.0+）

系统 SHALL 支持针对代码的多轮对话问答。

#### Scenario: 追问代码问题

- **WHEN** POST 请求发送至 `/api/explain/chat`，请求体为 `{"snippet_id": 12345, "kp_id": 10011, "question": "为什么用 ArrayList？"}`
- **THEN** 返回 SSE 流式响应
- **AND** 基于代码上下文回答问题

#### Scenario: 多知识点追问（v1.6.1+）

- **WHEN** POST 请求发送至 `/api/explain/chat`，请求体包含 `kp_ids: [10011, 10012]`
- **THEN** 系统使用多知识点的合并上下文回答问题

#### Scenario: 会话上下文

- **WHEN** 请求包含 `session_id`
- **THEN** 系统保持对话上下文连续性
- **AND** 后续问题可以引用之前的回答

### Requirement: 配额查询（v1.6.0+）

系统 SHALL 提供端点查询用户的 AI 解释配额状态。

#### Scenario: 查询配额

- **WHEN** GET 请求发送至 `/api/user/quota`
- **THEN** 响应包含 `daily_limit`, `used_today`, `remaining`, `reset_at`
- **AND** 响应状态码为 200 OK

#### Scenario: 管理员无限配额

- **WHEN** 管理员用户查询配额
- **THEN** `daily_limit` 显示为 -1（表示无限制）

## Implementation Details

### Flask Application
- App factory: api/__init__.py:1 (`create_app()`)
- Configuration: Flask development server (single-threaded)
- CORS enabled via flask-cors
- Host: 0.0.0.0 (default)
- Port: 5000 (default, configurable)

### API Routes
- Knowledge point routes: api/routes/knowledge_routes.py:1
- Matching routes: api/routes/match_routes.py:1
- Route registration: api/routes/__init__.py:1

### Request/Response Schemas
- Match request schema: api/schemas/match.py:1
- Match response schema: api/schemas/match.py:50
- Knowledge point schema: api/schemas/knowledge.py:1

### Service Layer Integration
- Search service: src/services/search_service.py:1
- Knowledge service: src/services/knowledge_service.py:1
- Service singleton pattern: Shared instance via `get_search_service()`, `get_knowledge_service()`

### Logging
- Logger: `api_logger` from lib/globals
- Log location: api/logs/
- Log format: Timestamp, level, message, request context

### Entry Point
- Server launcher: run_api.py:1
- Command-line arguments: --port, --host, --debug

## API Endpoints Summary

### Knowledge Point Endpoints (READ-ONLY)
- `GET /api/knowledge/tree` - Hierarchical tree structure
- `GET /api/knowledge/list` - Flat list of all KPs
- `GET /api/knowledge/{id}` - Single KP details
- `GET /api/knowledge/{id}/children` - Child KPs

### Matching Endpoints
- `POST /api/match` - Single KP matching with parameters
- `POST /api/match/batch` - Multiple independent KP matching
- `POST /api/match/composite` - Composite KP matching (multi-KP)
- `POST /api/match/matrix` - Single KP matrix matching (by difficulty)
- `POST /api/match/composite/matrix` - Composite KP matrix matching
- `GET /api/match/health` - Service health check

### AI Explanation Endpoints (v1.6.0+, require authentication)
- `POST /api/explain` - Code explanation (SSE streaming)
- `POST /api/explain/chat` - Multi-turn Q&A (SSE streaming)
- `GET /api/user/quota` - Query AI explanation quota

## Default Configuration

### Matching Parameters (v1.3.3+)
- `w_ast`: 0.5 (AST structure weight, not exposed in API)
- `w_keyword`: 0.4 (keyword semantic weight, not exposed in API)
- `w_difficulty`: 0.1 (difficulty alignment weight, not exposed in API)
- `ast_min_ratio`: 0.4 (minimum AST coverage)
- `keyword_min_score`: 0.4 (minimum keyword score)
- `top_k`: 5 (maximum results)

### Composite Matching
- `score_aggregation`: "average" (default aggregation strategy)
- Alternatives: "min" (strict), "sum" (coverage)

## Dependencies
- Flask: Web framework
- flask-cors: CORS support
- Pydantic: Request/response validation
- SearchService: Business logic for matching
- KnowledgeService: Business logic for knowledge points
- ExplainService: AI explanation with LLM (v1.6.0+)
- HighlightService: AST-based code line highlighting (v1.6.0+)
- QuotaService: Daily quota management (v1.6.0+)
- RateLimiterService: Request rate limiting (v1.6.0+)
- LLMClient: OpenAI-compatible API wrapper (v1.6.0+)

## AI Explanation Architecture (v1.6.0+)

### LLM Integration

The system uses `lib/client/llm.py` to interact with LLM APIs:

```python
# Configuration: config/llm.yaml
primary:
  endpoint: https://api.openai.com/v1/chat/completions
  model: gpt-4o
  api_key: ${LLM_API_KEY}  # From environment variable

fallback:
  endpoint: https://backup-api.example.com
  model: gpt-4o-mini
  api_key: ${LLM_FALLBACK_API_KEY}
```

**Features**:
- SSE (Server-Sent Events) streaming response
- Primary/Fallback dual-endpoint support
- Automatic failover on primary failure
- Token usage tracking (prompt + completion)

### Highlight Mechanism

`HighlightService` computes code line highlights based on:
1. **AST Node Matching**: KP template nodes → code locations
2. **Keyword Matching**: KP keywords → code lines containing them
3. **Merge Adjacent**: Consecutive highlighted lines merged

**Output Format**:
```json
[
  {"start_line": 3, "end_line": 5, "type": "for_statement", "label": "for loop"},
  {"start_line": 7, "end_line": 7, "type": "keyword_match", "label": "Keyword: ArrayList"}
]
```

### Quota Management

`QuotaService` manages daily AI explanation quotas:
- Regular users: 50 requests/day
- Admin users: Unlimited
- Reset time: 00:00 Beijing time (Asia/Shanghai)
- Quota consumed only on successful LLM response (v1.6.1+)

### Rate Limiting

`RateLimiterService` implements sliding window rate limiting:
- Default: 10 requests/minute/user
- Returns 429 Too Many Requests when exceeded
