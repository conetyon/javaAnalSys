# 技术设计：代码解释功能

## 上下文

本设计解决 Java 知识点匹配系统中"代码片段缺乏解释"的问题，采用关键行标注 + AI 按需解释的混合方案。

## 目标 / 非目标

### 目标

- 标注代码片段中与知识点直接相关的行
- 提供 AI 驱动的代码解释和问答能力
- 通过配额系统控制 API 成本

### 非目标

- 不提供离线预生成解释（成本高、维护复杂）
- 不支持代码执行或调试
- 不替代现有匹配算法

## 决策

### D1: 关键行标注实现方式

**决策**: 实时计算关键行，仅对返回的 top-k 结果解析

**备选方案**:
1. 预存行号到数据库 - 需要修改表结构、重新导入代码库（代价太大）
2. 实时计算（选用）- 只对 top-k 结果解析，开销可接受（通常 5-20 个片段）
3. 前端关键词高亮 - 简单但不够精确

**理由**:
- 避免修改 `code_snippets` 表结构
- 避免重新导入 20,000+ 代码片段
- top-k 通常只有 5-20 个，实时解析开销可接受（<50ms）

### D2: LLM 调用架构

**决策**: 后端统一代理 LLM API，前端通过 SSE 接收流式响应

**备选方案**:
1. 前端直接调用 LLM API - 暴露 API Key，无法做配额控制
2. 后端代理（选用）- 安全、可控、支持配额

**理由**: API Key 安全性 + 配额控制需求

### D3: 配额管理方式

**决策**: 按日配额，存储于 `user_quotas` 表，每日 0 点重置

**配额规则**:
```
管理员 (role='admin'): 无限制
普通用户 (role='user'): 50 次/天（可通过 daily_limit 字段单独调整）
未登录用户: 不允许使用 AI 解释（返回 401）
```

**备选方案**:
1. 按月配额 - 周期长，用户可能短期内耗尽
2. 按次付费 - 需要支付系统，复杂度高
3. 按日配额（选用）- 简单、公平、成本可控

**Role 降级处理**：JWT 携带 role 字段，降级时通过更新 `last_login_at` 使旧 token 失效（复用现有 single-device login 机制）。

```python
# 降级用户时强制失效旧 token
def demote_user(user_id):
    self.client.execute(
        "UPDATE users SET role = 'user', last_login_at = UTC_TIMESTAMP() WHERE id = %s",
        (user_id,)
    )
```

**时区处理策略**：
- 数据库存储：使用 UTC（与现有 auth_service.py 保持一致）
- 配额重置判断：应用层使用 zoneinfo 转换为北京时间（Asia/Shanghai）
- 避免时区混淆：`last_reset_date` 存储北京时间日期，非 UTC

```python
# quota_service.py 时区处理示例
# 使用 Python 3.9+ 内置 zoneinfo（无需额外依赖）
from datetime import datetime
from zoneinfo import ZoneInfo

def _get_beijing_date():
    """获取北京时间当前日期"""
    return datetime.now(ZoneInfo('Asia/Shanghai')).date()

def _should_reset(last_reset_date):
    """检查是否需要重置（跨北京时间 0 点）"""
    return _get_beijing_date() > last_reset_date
```

**依赖说明**：使用 Python 3.9+ 内置的 `zoneinfo` 模块，无需安装 `pytz`。

### D4: 多轮对话状态管理

**决策**: 会话状态存储于内存 LRU 缓存，30 分钟过期

**配置**:
```python
SESSION_CACHE_SIZE = 1000  # 最大会话数，防止 OOM
SESSION_TTL = 1800         # 30 分钟过期
```

**实现**：使用简单 dict + 懒清理（无外部依赖）：
```python
import time

class SessionCache:
    def __init__(self, max_size=1000, ttl=1800):
        self._cache = {}
        self._max_size = max_size
        self._ttl = ttl

    def get(self, key):
        item = self._cache.get(key)
        if item and time.time() - item['ts'] < self._ttl:
            return item['data']
        self._cache.pop(key, None)
        return None

    def set(self, key, value):
        self._cache[key] = {'data': value, 'ts': time.time()}
```

**备选方案**:
1. 数据库存储 - 持久但查询慢
2. 前端存储 - 无法跨设备
3. Redis - 需要额外依赖
4. 内存 LRU 缓存（选用）- 简单、性能好、过期自动清理

**简化决策**: MVP 阶段使用内存 LRU 缓存，不引入 Redis 依赖。多实例部署时需要会话亲和性（sticky session）或迁移到 Redis。

**⚠️ Technical Debt**: 内存缓存不支持多实例部署，后续需迁移到 Redis。

## 数据模型

### user_quotas 表

添加到 `src/db_manager/database.py` 的 `_init_tables()` 方法的 `statements` 列表中：

```python
# user_quotas 表：AI 解释配额管理
('''CREATE TABLE IF NOT EXISTS user_quotas
    (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        user_id         INT NOT NULL UNIQUE,
        daily_limit     INT NOT NULL DEFAULT 50,
        used_today      INT NOT NULL DEFAULT 0,
        last_reset_date DATE NOT NULL,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''', ()),
```

### explain_logs 表

添加到 `src/db_manager/database.py` 的 `_init_tables()` 方法的 `statements` 列表中：

```python
# explain_logs 表：AI 解释请求日志
# 注意：snippet_id 使用 ON DELETE SET NULL 保留审计日志（即使代码片段被删除）
('''CREATE TABLE IF NOT EXISTS explain_logs
    (
        id                INT PRIMARY KEY AUTO_INCREMENT,
        user_id           INT NOT NULL,
        snippet_id        INT,
        kp_id             INT NOT NULL,
        request_type      ENUM('explain', 'chat') NOT NULL,
        prompt_tokens     INT,
        completion_tokens INT,
        latency_ms        INT,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (snippet_id) REFERENCES code_snippets(id) ON DELETE SET NULL
    )''', ()),
```

索引添加到 `index_statements` 列表：

```python
# explain_logs: 用户+时间复合索引（日志查询）
('''CREATE INDEX idx_explain_logs_user_created
    ON explain_logs(user_id, created_at DESC)''', 'idx_explain_logs_user_created'),
```

### 关键行标注（实时计算，不修改数据库）

关键行通过 `HighlightService` 实时计算，基于已有的 AST 特征：

```python
# src/services/highlight_service.py
class HighlightService:
    """关键行标注服务 - 实时计算，不存储"""

    def compute_highlights(
        self,
        code: str,
        kp_ast_template: dict,
        kp_keywords: List[str]
    ) -> List[dict]:
        """
        计算代码片段的关键行

        Returns:
            [{"start_line": 3, "end_line": 6, "type": "for_statement", "label": "增强for循环"}]
        """
        # 使用已有的 tree-sitter 解析能力
        # 匹配 kp_ast_template 中的节点类型，返回行号
```

**调用时机**：在 SearchService 返回结果后，对 top-k 结果调用 `compute_highlights()`

## API 设计

### POST /api/explain

解释代码片段（SSE 流式响应）

**请求**:
```json
{
  "snippet_id": 12345,
  "kp_id": 10011,
  "user_level": "beginner"  // optional: beginner, intermediate, advanced
}
```

**响应** (SSE):
```
data: {"type": "content", "content": "这段代码演示了"}
data: {"type": "content", "content": "Java 的增强 for 循环..."}
data: {"type": "done", "tokens": {"prompt": 150, "completion": 200}}
```

### SSE 后端实现方式

使用 Flask 原生 Response + stream_with_context：

```python
# api/routes/explain.py
from flask import Response, stream_with_context

@api_bp.route('/explain', methods=['POST'])
@require_auth
@require_quota  # 配额检查装饰器
def explain_snippet_sse():
    data = request.get_json()

    def generate():
        try:
            for chunk in explain_service.stream_explain(
                user_id=g.user_id,
                snippet_id=data['snippet_id'],
                kp_id=data['kp_id'],
                user_level=data.get('user_level', 'beginner')
            ):
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'tokens': {...}})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )
```

### SSE 前端消费方式

**注意**：`EventSource` 只支持 GET 请求，POST 请求需要使用 `fetch` + `ReadableStream`：

```typescript
// frontend/src/api/explain.ts（与现有 auth.ts, match.ts 同目录）
export async function streamExplain(
  body: ExplainRequest,
  onChunk: (text: string) => void,
  onDone: (tokens: TokenUsage) => void,
  onError: (error: string) => void,
  signal?: AbortSignal  // 支持取消请求
) {
  const response = await fetch('/api/explain', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
    signal,  // 传递 AbortSignal
  });

  if (!response.ok) {
    const err = await response.json();
    onError(err.error || 'Request failed');
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      // 解析 SSE 格式: "data: {...}\n\n"
      const lines = text.split('\n\n').filter(Boolean);
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'content') onChunk(data.content);
          else if (data.type === 'done') onDone(data.tokens);
          else if (data.type === 'error') onError(data.error);
        }
      }
    }
  } finally {
    reader.releaseLock();  // 确保释放资源
  }
}

// 使用示例（支持取消）
const controller = new AbortController();
streamExplain(body, onChunk, onDone, onError, controller.signal);
// 取消请求: controller.abort();
```

### POST /api/explain/chat

多轮问答（SSE 流式响应）

**请求**:
```json
{
  "snippet_id": 12345,
  "kp_id": 10011,
  "question": "为什么不能在遍历时修改集合？",
  "session_id": "abc123"  // optional, 用于多轮对话
}
```

### GET /api/user/quota

查询当前用户配额

**响应**:
```json
{
  "daily_limit": 50,
  "used_today": 12,
  "remaining": 38,
  "reset_at": "2026-03-08T00:00:00+08:00"
}
```

### 429 错误响应

配额耗尽或请求过于频繁时返回 429 Too Many Requests：

```python
# api/middleware/error_handler.py
class TooManyRequestsException(ApiException):
    """配额耗尽或请求过于频繁"""

    def __init__(self, message: str = "请求过于频繁", error: str = None,
                 reset_at: str = None, retry_after: int = None):
        super().__init__(message, code=429, error=error)
        self.reset_at = reset_at
        self.retry_after = retry_after
```

**响应格式**：
```json
{
  "code": 429,
  "message": "配额已用完",
  "reset_at": "2026-03-08T00:00:00+08:00"
}
```

或限流时：
```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "retry_after": 60
}
```

## 服务架构

```
┌──────────────────────────────────────────────────────────────┐
│  ExplainService                                              │
├──────────────────────────────────────────────────────────────┤
│  + explain_snippet(snippet_id, kp_id, user_level)            │
│  + chat(snippet_id, kp_id, question, session_id)             │
│  - _build_explain_prompt(code, kp_name, highlights, level)   │
│  - _build_chat_prompt(code, kp_name, question, history)      │
│  - _check_quota(user_id) -> bool                             │
│  - _check_rate_limit(user_id) -> bool                        │
│  - _consume_quota(user_id)                                   │
│  - _log_request(user_id, snippet_id, kp_id, tokens, latency) │
└───────────────────────┬──────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│  LLMClient                                                   │
├──────────────────────────────────────────────────────────────┤
│  endpoint: https://china.184772.xyz                          │
│  model: gpt-5.4                                              │
│  + stream_completion(messages) -> Generator[chunk]           │
│    - 最后一个 chunk 包含 usage 字段（token 统计）              │
└──────────────────────────────────────────────────────────────┘
```

**Token 统计**：使用 LLM API 响应中的 `usage` 字段（`prompt_tokens`, `completion_tokens`），不自行计算。

## Prompt 模板

### 代码解释 Prompt（带补救能力）

```
你是一位 Java 教学助手，正在帮助学生理解代码。

【知识点】{kp_name} ({kp_name_zh})

【当前代码片段】
```java
{code}
```

【关键行标注】
{highlights}

【学生水平】{user_level}

请用简洁易懂的语言解释这段代码：
1. 概述代码的功能
2. 重点解释标注的关键行，说明它们如何体现该知识点
3. 如有必要，给出等价的替代写法或注意事项

**重要**：如果你认为这段代码不太适合演示该知识点（例如：过于复杂、包含太多无关逻辑、不够典型），请：
1. 简要说明为什么这个例子不够理想
2. 自己编写一个更简洁、更典型的示例代码
3. 基于你编写的新示例进行解释

回答要求：
- 使用中文
- 适合 {user_level} 水平的学习者
- 重点突出，避免冗长
- 生成的示例代码要简洁、可编译、能运行
- 如果代码中包含疑似敏感信息（如 API Key、密码、Token），不要在解释中暴露这些值
```

### 多轮问答 Prompt

```
你是一位 Java 教学助手，正在与学生进行问答。

【知识点】{kp_name} ({kp_name_zh})

【当前代码片段】
```java
{code}
```

【对话历史】
{history}

【学生问题】{question}

请针对学生的问题进行解答。

如果学生要求"换一个例子"、"有没有更简单的"、"这个太复杂了"等，直接编写一个更合适的示例代码并解释。

回答要求：
- 使用中文
- 直接回答问题，不要重复之前说过的内容
- 生成的代码要简洁、正确、可运行
```

## 配置文件

### config/llm.yaml

```yaml
llm:
  provider: openai_compatible
  endpoint: https://china.184772.xyz
  model: gpt-5.4
  api_key: ${LLM_API_KEY}  # 从环境变量读取
  timeout: 30
  max_tokens: 1000
  temperature: 0.7

quota:
  default_daily_limit: 50
  admin_unlimited: true
  reset_timezone: Asia/Shanghai  # 明确时区
  reset_hour: 0  # 0点重置

rate_limit:
  requests_per_minute: 10  # 防止短时间内疯狂请求
  burst: 3                 # 允许的突发请求数
```

**⚠️ 配置说明**: `endpoint` 和 `model` 为用户指定值，部署前需确认服务可用性。

### lib/utils/settings.py 配置模型

```python
# 新增 LLMConfig 类
class LLMConfig(BaseModel):
    provider: str = "openai_compatible"
    endpoint: str
    model: str
    api_key: str = ""  # 从环境变量覆盖
    timeout: int = 30
    max_tokens: int = 1000
    temperature: float = 0.7

class QuotaConfig(BaseModel):
    default_daily_limit: int = 50
    admin_unlimited: bool = True
    reset_timezone: str = "Asia/Shanghai"
    reset_hour: int = 0

class RateLimitConfig(BaseModel):
    requests_per_minute: int = 10
    burst: int = 3

# 在 _AppConfig 中添加字段
class _AppConfig(BaseModel):
    # ... 现有字段 ...
    llm: Optional[LLMConfig] = None
    quota: Optional[QuotaConfig] = None
    rate_limit: Optional[RateLimitConfig] = None
```

## 风险 / 权衡

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM API 延迟高 | 用户体验下降 | SSE 流式输出，首 token 快速显示 |
| API Key 泄露 | 成本失控 | 后端代理，Key 不暴露给前端 |
| 配额重置时间不准 | 用户困惑 | 显示明确的重置时间 |
| 会话缓存丢失 | 多轮对话中断 | 前端保留历史，重建上下文 |
| SSE 日志记录 | 内存溢出 | 更新 request_logger.py 跳过流式响应 |

## 迁移计划

1. **数据库迁移**: 新增 `user_quotas`, `explain_logs` 表
2. **配置部署**: 添加 `config/llm.yaml`，配置环境变量 `LLM_API_KEY`
3. **灰度发布**: 先对管理员开放，验证后全量发布

## 开放问题

1. ~~配额是否支持用户购买增量？~~ MVP 不实现，后续迭代考虑
2. ~~是否需要敏感词过滤？~~ 依赖 LLM 自身的安全机制
