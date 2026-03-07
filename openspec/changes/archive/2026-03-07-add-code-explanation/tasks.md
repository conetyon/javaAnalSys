# 实施任务清单

## 0. 前置任务

- [x] 0.1 修改 `src/services/auth_service.py`
  - `_generate_tokens(user_id, user_role='user')` 添加 role 参数
  - `login()` 传递 `user['role']` 给 `_generate_tokens()`
  - `refresh_token()` 查询最新 role 后传递给 `_generate_tokens()`
  - JWT payload 添加 `'role': user_role`
- [x] 0.2 修改 `api/middleware/auth.py` 的 `require_auth` 装饰器
  - 从 JWT payload 解析 `role` 字段（无需查库）
  - 设置 `g.user_role = payload.get('role', 'user')`

## 1. 基础设施

- [x] 1.1 创建 `config/llm.yaml` 配置文件
- [x] 1.2 在 `.env` 添加 `LLM_API_KEY` 环境变量
- [x] 1.3 更新 `lib/globals/__init__.py` 加载 LLM 配置
- [x] 1.4 修改 `lib/utils/settings.py` 的 `_AppConfig` 类
  - 添加 `LLMConfig` 类定义（endpoint, model, timeout, max_tokens, temperature）
  - 添加 `llm: Optional[LLMConfig] = None` 字段

## 2. 数据库

- [x] 2.1 在 `src/db_manager/database.py` 添加 `user_quotas` 表定义
- [x] 2.2 在 `src/db_manager/database.py` 添加 `explain_logs` 表定义
- [x] 2.3 添加索引 `idx_explain_logs_user_created`
- [x] 2.4 运行 `python scripts/setup_database.py --init-schema` 验证

## 3. 后端服务层

- [x] 3.1 创建 `lib/client/llm.py` - LLM API 客户端
  - OpenAI 兼容接口
  - 流式响应支持（yield chunks）
  - 错误处理和重试
- [x] 3.2 创建 `src/services/highlight_service.py` - 关键行标注服务
  - `compute_highlights(code, kp_ast_template, kp_keywords)` 方法
  - 使用已有的 tree-sitter 解析能力
- [x] 3.3 创建 `src/services/quota_service.py` - 配额管理服务（前置于 ExplainService）
  - `check_quota(user_id, user_role)` 方法
  - `consume_quota(user_id)` 方法
  - `get_quota_info(user_id)` 方法
  - 每日重置逻辑（Asia/Shanghai 时区）
  - **时区策略**：DB 存 UTC，应用层用 `zoneinfo` 转北京时间判断重置（Python 3.9+ 内置，无需额外依赖）
- [x] 3.4 创建 `src/services/rate_limiter.py` - 请求限流服务
  - 内存滑动窗口限流（10 次/分钟）
  - `check_rate_limit(user_id)` 方法
- [x] 3.5 创建 `src/services/explain_service.py` - AI 解释服务（依赖 3.1, 3.3, 3.4）
  - `stream_explain(user_id, snippet_id, kp_id, user_level)` 生成器方法
  - `stream_chat(user_id, snippet_id, kp_id, question, session_id)` 生成器方法
  - 请求日志记录

## 4. 后端 API 层

- [x] 4.1 创建 `api/schemas/explain.py` - 请求/响应模型
  - `ExplainRequest`, `ChatRequest`
  - `QuotaResponse`
- [x] 4.2 创建 `api/middleware/quota.py` - 配额检查装饰器
  - `@require_quota` 装饰器，检查配额和限流
  - 返回 429 错误时包含 `reset_at` 或 `retry_after`
- [x] 4.3 创建 `api/routes/explain.py` - 解释相关路由
  - 创建独立 Blueprint：`explain_bp = Blueprint('explain', __name__, url_prefix='/api/explain')`
  - `POST /api/explain` (SSE，使用 Response + stream_with_context)
  - `POST /api/explain/chat` (SSE)
  - 在 `api/routes/__init__.py` 的 `register_routes()` 中注册
  - **SSE 修复**：添加 CORS preflight 处理（`@explain_bp.before_request`）
  - **SSE 修复**：修复响应编码（`response.encoding = 'utf-8'`，content-type charset）
  - **SSE 修复**：修复 `iter_content` 流式处理
- [x] 4.4 扩展 `api/routes/user.py` - 配额查询路由
  - `GET /api/user/quota`
- [x] 4.5 在 `api/middleware/error_handler.py` 添加 `TooManyRequestsException`
  - 支持 `reset_at` 和 `retry_after` 字段
  - 注册 429 错误处理器
- [x] 4.6 更新 `api/middleware/request_logger.py` 跳过 SSE 响应日志
  - 检测 `Content-Type: text/event-stream`
  - 避免记录流式响应体（可能导致内存问题）

## 5. 匹配结果扩展

- [x] 5.1 修改 `src/services/search_service.py` 的结果组装逻辑
  - 在 `results.append({...})` 处调用 `HighlightService.compute_highlights()`
  - 需修改的方法：`search()`, `matrix_search()`, `composite_search()`, `composite_matrix_search()`
  - 参考位置：`search_service.py:269-303` 的结果组装处
- [x] 5.2 更新 `api/schemas/match.py`
  - `MatchResultItem` 添加 `highlight_ranges` 字段

## 6. 前端组件

- [x] 6.0 更新 `frontend/src/types/match.ts` 添加类型定义
  - 添加 `HighlightRange` 接口：`{ start_line, end_line, type, label }`
  - 在 `MatchResultItem` 中添加 `highlight_ranges?: HighlightRange[]`
  - 在 `MatrixResultItem` 中添加 `highlight_ranges?: HighlightRange[]`
- [x] 6.1 修改 `frontend/src/components/CodeBlock.tsx`
  - 添加 `highlightLines` prop
  - 使用 `lineProps` 实现行高亮样式
- [x] 6.2 创建 `frontend/src/components/CodeExplainer.tsx`
  - AI 解释面板
  - 使用 fetch + ReadableStream 接收 SSE
  - 多轮问答 UI
  - 断线重连（显示重试按钮）
  - **SSE 修复**：React StrictMode 兼容性
  - **SSE 修复**：请求直连后端（绕过 Vite 代理）
- [x] 6.3 创建 `frontend/src/components/QuotaIndicator.tsx`
  - 显示剩余配额
  - 配额耗尽提示
- [x] 6.4 创建 `frontend/src/api/explain.ts`（与现有 auth.ts, match.ts 同目录）
  - **前置**: 创建 `frontend/src/utils/sse.ts` 通用 SSE 处理工具
    - 封装 fetch + ReadableStream 逻辑
    - SSE 事件解析（`data: {...}\n\n` 格式）
    - AbortController 取消支持
    - 断线检测和重连提示
  - `streamExplain()` 使用 SSE 工具
  - `streamChat()` 使用 SSE 工具
  - `getQuota()` 请求
- [x] 6.5 在 `frontend/src/api/client.ts` 添加 429 错误处理
  - 解析 `reset_at` 或 `retry_after` 字段
  - 返回友好的配额耗尽提示

## 7. 前端集成

- [x] 7.1 修改 `frontend/src/components/MatchResultCard.tsx`
  - 从 `item.highlight_ranges` 提取行号数组传递给 `CodeBlock`
  - 实现：`highlightLines = ranges.flatMap(r => Array.from({length: r.end_line - r.start_line + 1}, (_, i) => r.start_line + i))`
  - 集成 `CodeExplainer` 组件
  - 添加"AI 解释"按钮
- [x] 7.2 在 Header 或侧边栏集成 `QuotaIndicator`

## 8. 测试

- [ ] 8.0 创建测试基础设施
  - 添加 `tests/__init__.py`
  - 添加 `tests/conftest.py`（共享 fixtures：mock DB、mock LLM）
  - 添加 `pytest.ini` 配置
- [ ] 8.1 后端单元测试
  - `tests/test_highlight_service.py`
  - `tests/test_explain_service.py`
  - `tests/test_quota_service.py`
- [ ] 8.2 API 集成测试
  - 测试 SSE 流式响应
  - 测试配额限制
  - 测试限流
- [x] 8.3 前端手动测试
  - 行高亮显示正确
  - AI 解释流式输出
  - 配额提示正确
  - 断线重试正常

## 9. 文档

- [x] 9.1 更新 `CLAUDE.md` 添加新功能说明
- [x] 9.2 更新 `README.md` 添加环境变量说明
- [x] 9.3 添加 AI 生成内容免责声明（前端 UI）
  - 在 CodeExplainer 组件底部显示提示文字
  - "AI 生成内容仅供参考，请自行验证代码正确性"
- [ ] 9.4 配置 `explain_logs` 数据保留策略
  - 建议保留 90 天
  - 可在 `scripts/` 添加清理脚本或在数据库层面配置
- [x] 9.5 记录 role 降级强制失效机制
  - 降级用户时更新 `last_login_at` 使旧 token 失效
  - 利用现有 single-device login 检查机制

---

## SSE 流式响应修复记录 (2026-03-07)

### 问题现象

1. 前端 `fetch` 请求 SSE 端点时遇到 CORS 错误（preflight OPTIONS 请求被拒绝）
2. 流式响应内容乱码（编码问题）
3. React StrictMode 下组件挂载两次导致重复请求

### 解决方案

**后端修复**：

1. 在 `api/routes/explain.py` 添加 CORS preflight 处理：
   ```python
   @explain_bp.before_request
   def handle_preflight():
       if request.method == 'OPTIONS':
           response = make_response()
           response.headers['Access-Control-Allow-Origin'] = '*'
           response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
           response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
           return response
   ```

2. 修复 SSE 响应编码：
   ```python
   response.encoding = 'utf-8'
   response.headers['Content-Type'] = 'text/event-stream; charset=utf-8'
   ```

3. 修复 `iter_content` 流式处理

**前端修复**：

1. SSE 请求绕过 Vite 代理，直连后端：
   ```typescript
   const API_BASE_URL = 'http://localhost:5000';
   fetch(`${API_BASE_URL}/api/explain`, { ... })
   ```

2. React StrictMode 兼容性处理（使用 `useRef` 防止重复请求）

### 验证结果

- [x] CORS preflight 请求正常通过
- [x] 流式响应内容正确解码
- [x] React StrictMode 下无重复请求
- [x] 断线重试功能正常
