# 技术设计文档

## 设计原则

1. **前端技术栈统一**：使用 React 18 + Ant Design 5 + Vite
2. **与现有后端风格一致**：路由、Schema、服务层遵循现有代码规范
3. **敏捷迭代**：迭代 1 可独立运行，不依赖认证
4. **幂等优先**：写操作尽可能设计为幂等，避免重复提交问题

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | React 18 + TypeScript | 主流前端框架 |
| UI 组件 | Ant Design 5 | 企业级 UI 组件库 |
| 代码高亮 | react-syntax-highlighter | Java 语法高亮 |
| 构建工具 | Vite | 快速开发服务器 |
| HTTP 客户端 | Axios | 需统一拦截处理 ApiException |
| 认证 | JWT (PyJWT + bcrypt) | 新增 |
| 状态管理 | React Context | 新增 |

## JWT 认证设计（迭代 2）

```
用户 → POST /api/auth/login → 后端验证 → 返回 tokens
                                    ↓
前端存储 localStorage ← access_token (15min)
                      ← refresh_token (7d)
                                    ↓
后续请求 → Authorization: Bearer <token> → @require_auth 验证
```

**Token 配置**：
- `access_token`：15 分钟，API 请求认证
- `refresh_token`：7 天，刷新 access_token（不轮换，简化实现）

**单设备登录策略**：
- 每次登录生成新 Token，旧 Token 自然失效（无需服务端存储）
- 同一账号只能在一个设备登录，新登录会使旧设备的请求返回 401
- 实现方式：Token 中嵌入 `iat`（签发时间），数据库存储用户最后登录时间，验证时比对

## 统一错误处理与响应规范

前端 `api/client.ts` 必须拦截响应，适配后端的 `ApiException` 格式。
注意：部分接口（如 `/api/match`）会在顶层返回 `kp_id`, `total` 等元数据，前端需做泛型适配：

```typescript
// 基础响应结构
interface BaseResponse {
  code: number;
  message: string;
  error?: string; // 适配 ApiException
}

// 通用数据响应
interface ApiResponse<T = any> extends BaseResponse {
  data?: T;
}

// 匹配接口响应（带元数据）
interface MatchResponse<T> extends BaseResponse {
  kp_id: number;
  total: number;
  data: T[];
}
```

### 前端错误处理策略

后端 `ApiException` 的 `error` 字段处理规则：

| 状态码 | `error` 字段处理 | 说明 |
|--------|-----------------|------|
| 400 | 展示给用户 | 参数校验错误，用户可修正（如"用户名已存在"）|
| 401 | 记录控制台 + 跳转登录 | 认证错误，不展示技术细节 |
| 404 | 展示给用户 | 资源不存在，用户可理解（如"知识点不存在"）|
| 422 | 展示给用户 | Pydantic 校验失败（如字段类型错误、超出范围）|
| 500 | **仅记录控制台** | 服务器错误，展示通用提示"服务暂时不可用" |

```typescript
// api/client.ts 错误拦截示例
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<BaseResponse>) => {
    const status = error.response?.status;
    const errorDetail = error.response?.data?.error;

    // 记录所有错误到控制台（便于调试）
    console.error(`[API Error] ${status}: ${errorDetail}`);

    // 500 错误不透传给用户
    if (status === 500) {
      message.error('服务暂时不可用，请稍后重试');
    }
    // 400/404/422 错误透传
    else if (status === 400 || status === 404 || status === 422) {
      message.error(error.response?.data?.message || '请求失败');
    }
    // 401 交由刷新逻辑处理

    return Promise.reject(error);
  }
);
```

## 数据库表设计

> **注意**：本项目 MySQL 版本要求 8.0+（支持 JSON 类型）。
> 所有表结构变更应直接在 `src/db_manager/database.py` 的 `_init_tables` 方法中实现。
> **严禁创建独立的 SQL 脚本文件**，以保持 `DatabaseInitializer` 的单一事实来源。

### users 表（迭代 2）

```python
# 添加到 statements 列表
('''CREATE TABLE IF NOT EXISTS users
    (
        id            INT PRIMARY KEY AUTO_INCREMENT,
        username      VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(128) NOT NULL,
        email         VARCHAR(100) UNIQUE,
        role          ENUM('user', 'admin') DEFAULT 'user',
        last_login_at TIMESTAMP NULL,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )''', ()),
```

### match_history 表（迭代 3）

```python
# 添加到 statements 列表
('''CREATE TABLE IF NOT EXISTS match_history
    (
        id         INT PRIMARY KEY AUTO_INCREMENT,
        user_id    INT NOT NULL,
        kp_ids     JSON NOT NULL,
        kp_names   JSON NOT NULL,
        params     JSON NOT NULL,
        mode       VARCHAR(20) DEFAULT 'list',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )''', ()),
```

> **冗余存储说明**：`match_history.kp_names` 在写入时快照知识点名称，即使后续 KP 名称变更，历史记录仍保留当时的名称。这是期望行为，确保历史记录的可追溯性。

### favorites 表（迭代 3）

```python
# 添加到 statements 列表
('''CREATE TABLE IF NOT EXISTS favorites
    (
        id         INT PRIMARY KEY AUTO_INCREMENT,
        user_id    INT NOT NULL,
        snippet_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (snippet_id) REFERENCES code_snippets(id) ON DELETE CASCADE,
        UNIQUE KEY uk_user_snippet (user_id, snippet_id)
    )''', ()),
```

### 索引定义（单独语句）

```python
# 添加到 index_statements 列表（与现有风格一致）
index_statements = [
    # ... 现有索引 ...

    # match_history: 用户+时间复合索引（降序，用于历史记录分页）
    ('''CREATE INDEX idx_match_history_user_created
        ON match_history(user_id, created_at DESC)''', 'idx_match_history_user_created'),

    # favorites: 用户+时间复合索引（降序，用于收藏列表分页）
    ('''CREATE INDEX idx_favorites_user_created
        ON favorites(user_id, created_at DESC)''', 'idx_favorites_user_created'),
]
```

> **说明**：
> - `favorites.user_id` 外键索引用于 `get_favorite_ids()` 查询
> - `favorites.snippet_id` 无需单独索引，外键自动创建
> - 唯一约束 `uk_user_snippet` 已隐式创建复合索引（用于添加/取消收藏）
> - `idx_favorites_user_created` 用于收藏列表分页的 ORDER BY 排序

**幂等性说明**：
- **DDL**：所有表使用 `CREATE TABLE IF NOT EXISTS`，可重复执行
- **索引**：使用单独语句 + 异常捕获（错误码 1061），跳过已存在索引
- **收藏 (POST)**：捕获唯一约束异常（错误码 1062），已存在视为成功
- **取消 (DELETE)**：`DELETE` 天然幂等，记录不存在也返回成功
- **管理员创建**：使用 `INSERT IGNORE`，已存在则跳过
- **历史记录**：非幂等（设计如此），每次请求写入新记录

## 后端实现准则

新增代码必须与现有风格一致：

| 项目 | 准则 | 参考文件 |
|------|------|----------|
| 路由组织 | Flask Blueprint | `api/routes/__init__.py` |
| 请求校验 | Pydantic BaseModel | `api/schemas/match.py` |
| 服务实例 | 懒加载单例 | `api/routes/knowledge.py` |
| 日志记录 | `lib.globals.api_logger` | `api/routes/match.py` |
| 表定义 | `CREATE TABLE IF NOT EXISTS` | `src/db_manager/database.py` |
| 异常处理 | `BadRequestException` / `NotFoundException` | `api/middleware/error_handler.py` |

### 异常处理示例

```python
from api.middleware.error_handler import BadRequestException, NotFoundException

# 参数校验失败
raise BadRequestException(message="用户名已存在", error="Username already exists")

# 资源不存在
raise NotFoundException(message="用户不存在", error="User not found")
```

### 新增 UnauthorizedException（迭代 2 必须）

现有 `api/middleware/error_handler.py` 缺少 401 异常类，需新增：

```python
# api/middleware/error_handler.py 新增异常类
class UnauthorizedException(ApiException):
    """未授权访问异常"""
    def __init__(self, message: str = "未授权访问", error: str = None):
        super().__init__(message, code=401, error=error)
```

**同时需要添加原生 401 处理器**（用于捕获 Flask `abort(401)` 等非 ApiException 的 401 错误）：

```python
# api/middleware/error_handler.py 的 register_error_handlers() 中添加
@app.errorhandler(401)
def handle_unauthorized(e):
    """处理原生 401 错误（如 abort(401)）"""
    log.warning(f"[{request.method}] {request.path} - Unauthorized: {str(e)}")
    return jsonify({
        "code": 401,
        "message": "未授权访问",
        "error": str(e.description) if hasattr(e, 'description') else str(e)
    }), 401
```

> **说明**：`UnauthorizedException` 会被 `@app.errorhandler(ApiException)` 处理，而原生 401 错误需要单独处理器。

使用场景：
- Token 无效或过期
- Authorization Header 缺失
- 用户名或密码错误
- Token 签发时间早于用户最后登录时间（单设备校验）

### Auth 路由注册方式

采用独立 Blueprint 挂载到 `/api/auth`：

```python
# api/routes/auth.py
from flask import Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    ...

@auth_bp.route('/login', methods=['POST'])
def login():
    ...

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    ...
```

```python
# api/routes/__init__.py 修改
from .auth import auth_bp

def register_routes(app):
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)  # 新增
    app.register_blueprint(system_bp)
```

### User 路由注册方式（迭代 3）

```python
# api/routes/user.py
from flask import Blueprint
user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/history', methods=['GET'])
@require_auth
def get_history():
    ...

@user_bp.route('/favorites', methods=['GET', 'POST'])
@require_auth
def favorites():
    ...

@user_bp.route('/favorites/ids', methods=['GET'])
@require_auth
def get_favorite_ids():
    """获取当前用户所有收藏的 snippet_id 列表（轻量接口）"""
    user_id = g.user_id
    ids = user_service.get_favorite_ids(user_id)
    return jsonify({"code": 200, "message": "success", "data": ids})

@user_bp.route('/favorites/<int:snippet_id>', methods=['DELETE'])
@require_auth
def remove_favorite(snippet_id):
    ...
```

### 日志格式

```python
log.info("[POST] /api/auth/login - 用户登录成功")
log.warning("[POST] /api/auth/login - 用户名不存在")
# 注意：密码不应出现在日志中
```

### 认证装饰器实现（迭代 2）

提供两种装饰器，支持不同场景：

| 装饰器 | 用途 | 未登录行为 |
|--------|------|-----------|
| `@require_auth` | 用户专属接口（历史、收藏） | 返回 401 |
| `@optional_auth` | 匹配接口（选项 B 策略） | 继续执行，`g.user_id=None` |

```python
# api/middleware/auth.py
import os
from functools import wraps
from flask import request, g
import jwt
from api.middleware.error_handler import UnauthorizedException

# JWT 配置直接从环境变量读取（简化方案，无需扩展 Cfg）
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = 'HS256'

# 懒加载 AuthService 单例，避免循环导入
_auth_service = None

def _get_auth_service():
    global _auth_service
    if _auth_service is None:
        from src.services.auth_service import AuthService
        _auth_service = AuthService()
    return _auth_service

def _validate_token(token: str) -> int | None:
    """验证 Token 并返回 user_id，无效返回 None"""
    try:
        # 安全规范：必须显式指定 algorithms 参数
        # 防止 JWT Header 操纵攻击（Algorithm Confusion）
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        iat = payload.get('iat')

        # 单设备校验
        last_login = _get_auth_service().get_last_login_time(user_id)
        if last_login and iat < last_login.timestamp():
            return None

        return user_id
    except jwt.PyJWTError:
        return None

def require_auth(f):
    """强制认证装饰器 - 用于用户专属接口"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise UnauthorizedException(error="Missing or invalid Authorization header")

        token = auth_header.split(' ')[1]
        user_id = _validate_token(token)
        if user_id is None:
            raise UnauthorizedException(error="Invalid or expired token")

        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated

def optional_auth(f):
    """可选认证装饰器 - 用于匹配接口（登录用户记录历史，匿名用户正常使用）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user_id = None  # 默认匿名
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            g.user_id = _validate_token(token)  # 验证失败则保持 None
        return f(*args, **kwargs)
    return decorated
```

## Pydantic Schema 定义

### api/schemas/auth.py（迭代 2）

```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator, EmailStr
import re

class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名（3-50字符，仅字母/数字/下划线）"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="密码（8-128字符）"
    )
    # TODO: 生产环境建议增加密码复杂度校验
    # @field_validator('password')
    # def validate_password(cls, v):
    #     if not any(c.isupper() for c in v): raise ValueError('需包含大写字母')
    #     if not any(c.islower() for c in v): raise ValueError('需包含小写字母')
    #     if not any(c.isdigit() for c in v): raise ValueError('需包含数字')
    #     return v
    email: Optional[EmailStr] = Field(
        None,
        description="邮箱（可选）"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class RefreshRequest(BaseModel):
    """Token 刷新请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str = Field(description="访问令牌")
    refresh_token: str = Field(description="刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(default=900, description="过期时间（秒）")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    email: Optional[str] = None
    role: str = "user"
```

### api/schemas/user.py（迭代 3）

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class AddFavoriteRequest(BaseModel):
    """添加收藏请求"""
    snippet_id: int = Field(..., description="代码片段 ID")


class FavoriteItem(BaseModel):
    """收藏项"""
    id: int
    snippet_id: int
    content: str = Field(default="", description="代码内容")
    file_path: Optional[str] = None
    created_at: str


class FavoritesResponse(BaseModel):
    """收藏列表响应"""
    code: int = 200
    message: str = "success"
    data: List[FavoriteItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class HistoryItem(BaseModel):
    """历史记录项"""
    id: int
    kp_ids: List[int]
    kp_names: List[str] = Field(default_factory=list)
    mode: str = "list"
    params: dict = Field(default_factory=dict)
    created_at: str


class HistoryResponse(BaseModel):
    """历史记录响应"""
    code: int = 200
    message: str = "success"
    data: List[HistoryItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
```

## 幂等性实现

### 收藏操作（幂等）

```python
# src/services/user_service.py
from mysql.connector import IntegrityError
from api.middleware.error_handler import BadRequestException

class UserService:
    def __init__(self, db_name: str = None):
        from lib.client.db import MySQLClient
        import config
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)

    def add_favorite(self, user_id: int, snippet_id: int) -> bool:
        """
        添加收藏（幂等操作）
        - 成功添加返回 True
        - 已存在（唯一约束冲突）也返回 True
        - snippet_id 不存在抛出 BadRequestException
        """
        try:
            self.client.execute(
                "INSERT INTO favorites (user_id, snippet_id) VALUES (%s, %s)",
                (user_id, snippet_id)
            )
            return True
        except IntegrityError as e:
            # 错误码 1062 = Duplicate entry（唯一约束冲突）
            if e.errno == 1062:
                return True  # 幂等：已存在视为成功
            # 错误码 1452 = Foreign key constraint fails（snippet_id 不存在）
            if e.errno == 1452:
                raise BadRequestException(message="代码片段不存在", error="Snippet not found")
            raise

    def remove_favorite(self, user_id: int, snippet_id: int) -> bool:
        """
        取消收藏（幂等操作）
        - 不管记录是否存在，都返回成功
        """
        self.client.execute(
            "DELETE FROM favorites WHERE user_id = %s AND snippet_id = %s",
            (user_id, snippet_id)
        )
        return True  # DELETE 天然幂等

    def get_favorite_ids(self, user_id: int) -> list:
        """
        获取用户所有收藏的 snippet_id 列表（轻量接口，用于前端收藏按钮状态初始化）
        """
        rows = self.client.fetch_all(
            "SELECT snippet_id FROM favorites WHERE user_id = %s",
            (user_id,)
        )
        return [r['snippet_id'] for r in rows]

    def get_favorites(self, user_id: int, page: int = 1, page_size: int = 20) -> tuple:
        """
        查询收藏列表（JOIN 代码片段内容）
        返回 (items, total)
        """
        # 获取总数
        total = self.client.fetch_one(
            "SELECT COUNT(*) as cnt FROM favorites WHERE user_id = %s",
            (user_id,)
        )['cnt']

        # JOIN 获取收藏内容
        items = self.client.fetch_all(
            """SELECT f.id, f.snippet_id, f.created_at, s.content, s.file_path
               FROM favorites f
               JOIN code_snippets s ON f.snippet_id = s.id
               WHERE f.user_id = %s
               ORDER BY f.created_at DESC
               LIMIT %s OFFSET %s""",
            (user_id, page_size, (page - 1) * page_size)
        )
        return items, total

    def get_history(self, user_id: int, page: int = 1, page_size: int = 20) -> tuple:
        """
        查询匹配历史（kp_names 已冗余存储，无需 JOIN）
        返回 (items, total)
        """
        total = self.client.fetch_one(
            "SELECT COUNT(*) as cnt FROM match_history WHERE user_id = %s",
            (user_id,)
        )['cnt']

        items = self.client.fetch_all(
            """SELECT id, kp_ids, kp_names, params, mode, created_at
               FROM match_history
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            (user_id, page_size, (page - 1) * page_size)
        )
        return items, total
```

### 历史记录（非幂等）

历史记录作为用户行为日志，**在路由层写入**（保持 SearchService 单一职责）：

```python
# src/services/user_service.py 新增方法
class UserService:
    def record_history(self, user_id: int, kp_ids: List[int], kp_names: List[str], mode: str, params: dict):
        """写入匹配历史（每次调用都插入新记录）"""
        import json
        self.client.execute(
            "INSERT INTO match_history (user_id, kp_ids, kp_names, params, mode) VALUES (%s, %s, %s, %s, %s)",
            (user_id, json.dumps(kp_ids), json.dumps(kp_names), json.dumps(params), mode)
        )
```

```python
# src/services/knowledge_service.py 新增方法
class KnowledgeService:
    def get_kp_names(self, kp_ids: List[int]) -> List[str]:
        """
        批量获取知识点名称
        :param kp_ids: 知识点 ID 列表
        :return: 名称列表（与输入顺序一致，不存在的返回空字符串）
        """
        if not kp_ids:
            return []
        placeholders = ','.join(['%s'] * len(kp_ids))
        sql = f"SELECT id, name FROM knowledge_points WHERE id IN ({placeholders})"
        with MySQLClient(db=self.db_name) as client:
            rows = client.fetch_all(sql, tuple(kp_ids))
        name_map = {row['id']: row['name'] for row in rows}
        return [name_map.get(kp_id, '') for kp_id in kp_ids]
```

```python
# api/routes/match.py 修改（在路由层处理历史写入）
from flask import g

@api_bp.route('/match', methods=['POST'])
@optional_auth  # 可选认证：匿名可用，登录则记录历史
def match():
    # ... 参数解析 ...
    results = search_service.search(kp_id, ...)

    # 路由层负责历史写入（仅登录用户且有结果）
    if g.user_id is not None and results and len(results) > 0:
        kp_names = knowledge_service.get_kp_names([kp_id])
        user_service.record_history(g.user_id, [kp_id], kp_names, 'list', params)

    return jsonify({"code": 200, "data": results, ...})
```

**认证策略（选项 B）**：
- 匹配 API 使用 `@optional_auth`，匿名用户可正常使用
- 登录用户自动记录匹配历史
- 历史/收藏 API 使用 `@require_auth`，强制登录

**设计理由**：
- SearchService 保持单一职责（只负责匹配逻辑）
- 历史记录是用户行为，属于 UserService 职责
- 路由层可访问 `g.user_id`，无需传递到 Service 层
- 便于测试：SearchService 测试无需 mock 用户相关逻辑

**历史写入条件**：
- `g.user_id is not None`（已登录）
- `results` 非空且 `len(results) > 0`
- 空结果或匿名访问不记录

### 级联删除说明

```sql
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
```

**预期行为**：删除用户时，自动删除其历史记录和收藏。这是合理的设计：
- 用户数据归属于用户，用户删除后数据无意义
- 避免孤儿记录占用存储
- 符合 GDPR 数据删除要求

## 前端 Token 自动刷新流程

前端 `api/client.ts` 实现 axios 拦截器，处理 Token 过期：

```typescript
// frontend/src/api/client.ts
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { Modal } from 'antd';

const client = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

// **注意**：baseURL: '/api' 意味着调用 client.post('/match') 实际请求 /api/match
// 不要在调用时再加 /api 前缀，否则会变成 /api/api/match

// 请求拦截：添加 Token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：处理 401
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 非 401 或已重试，直接抛出
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // 检查是否被踢出登录（单设备限制）
    const errorDetail = (error.response?.data as any)?.error;
    if (errorDetail === 'Session expired, please login again') {
      Modal.warning({
        title: '账号已在其他设备登录',
        content: '您的账号已在其他设备登录，当前会话已失效',
        okText: '重新登录',
        onOk: clearTokensAndRedirect,
      });
      return Promise.reject(error);
    }

    // 刷新 Token 的请求本身 401，跳转登录
    if (originalRequest.url?.includes('/auth/refresh')) {
      handleSessionExpired();
      return Promise.reject(error);
    }

    // 尝试刷新 Token
    if (!isRefreshing) {
      isRefreshing = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        handleSessionExpired();
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
        localStorage.setItem('access_token', data.data.access_token);

        // 通知等待的请求
        refreshSubscribers.forEach((cb) => cb(data.data.access_token));
        refreshSubscribers = [];
        isRefreshing = false;

        // 重试原请求
        originalRequest._retry = true;
        originalRequest.headers.Authorization = `Bearer ${data.data.access_token}`;
        return client(originalRequest);
      } catch {
        handleSessionExpired();
        return Promise.reject(error);
      }
    }

    // 已在刷新中，排队等待
    return new Promise((resolve) => {
      refreshSubscribers.push((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        resolve(client(originalRequest));
      });
    });
  }
);

function clearTokensAndRedirect() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/login';
}

// 会话过期时显示模态框提示（避免突然跳转）
function handleSessionExpired() {
  Modal.warning({
    title: '登录已过期',
    content: '您的登录状态已失效，请重新登录',
    okText: '重新登录',
    onOk: () => {
      clearTokensAndRedirect();
    },
  });
}

export default client;
```

**流程说明**：
1. 请求返回 401
2. 检查是否有 refresh_token
3. 有：尝试刷新 → 成功则重试原请求
4. 无或刷新失败：清除 Token，跳转登录页

## 安全规范

| 项目 | 实现 |
|------|------|
| 密码存储 | bcrypt 哈希，不可逆 |
| JWT Secret | 从环境变量 `JWT_SECRET` 读取，不提交代码 |
| 登录限流 | 同一 IP 5次/分钟（可选，MVP 可跳过）|
| 日志脱敏 | 密码字段不记录日志 |
| XSS 防护 | MVP 用 localStorage；**生产环境升级**：HttpOnly Cookie + SameSite=Strict |

### JWT 配置管理

**简化方案**：JWT 配置直接在代码中定义常量，Secret 从环境变量读取（无需 `config/auth.yaml`）：

```python
# api/middleware/auth.py
import os

JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = 'HS256'

# Token 过期时间（支持环境变量覆盖，便于开发/生产环境灵活调整）
ACCESS_TOKEN_EXPIRE = int(os.environ.get('ACCESS_TOKEN_EXPIRE', 900))      # 默认 15 分钟
REFRESH_TOKEN_EXPIRE = int(os.environ.get('REFRESH_TOKEN_EXPIRE', 604800))  # 默认 7 天
```

> **配置说明**：
> - 开发环境可设置较长的 `ACCESS_TOKEN_EXPIRE`（如 3600 秒）减少频繁刷新
> - 生产环境建议使用默认值（900 秒）保证安全性
> - **推荐使用项目根目录 `.env` 文件**配置（避免污染系统环境变量）

**`.env` 文件示例**（需添加到 `.gitignore`）：

```bash
# .env (项目根目录，不提交到版本控制)
JWT_SECRET=your-secure-random-string-at-least-32-chars
ACCESS_TOKEN_EXPIRE=900
REFRESH_TOKEN_EXPIRE=604800

# 管理员账号（仅初始化时使用）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-admin-password
```

**启动时加载 `.env`**：

```python
# run_api.py 或 api/__init__.py 开头
from dotenv import load_dotenv
load_dotenv()  # 从项目根目录 .env 文件加载

import os
if not os.environ.get('JWT_SECRET'):
    raise RuntimeError("JWT_SECRET 未设置，请在 .env 文件中配置后重启")
```

> **依赖**：需在 `requirements.txt` 添加 `python-dotenv>=1.0.0`

### AuthService 登录实现（并发安全）

使用行锁避免同一用户同时登录的竞态条件：

```python
# src/services/auth_service.py
import bcrypt
import jwt
from datetime import datetime, timedelta

class AuthService:
    def __init__(self, db_name: str = None):
        from lib.client.db import MySQLClient
        import config
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)

    def login(self, username: str, password: str) -> dict:
        """
        用户登录（使用行锁保证并发安全）
        """
        with self.client as client:  # 事务上下文
            # SELECT ... FOR UPDATE 获取行锁，防止并发登录竞态
            user = client.fetch_one(
                "SELECT id, username, password_hash FROM users WHERE username = %s FOR UPDATE",
                (username,)
            )
            if not user:
                raise UnauthorizedException(error="Invalid credentials")

            # 验证密码
            if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                raise UnauthorizedException(error="Invalid credentials")

            # 更新最后登录时间（在行锁保护下）
            client.execute(
                "UPDATE users SET last_login_at = NOW() WHERE id = %s",
                (user['id'],)
            )

        # 生成 Token（事务外）
        return self._generate_tokens(user['id'])

    def get_last_login_time(self, user_id: int) -> datetime | None:
        """获取用户最后登录时间"""
        row = self.client.fetch_one(
            "SELECT last_login_at FROM users WHERE id = %s",
            (user_id,)
        )
        return row['last_login_at'] if row else None

    def _generate_tokens(self, user_id: int) -> dict:
        """生成 access_token 和 refresh_token"""
        from api.middleware.auth import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE, REFRESH_TOKEN_EXPIRE

        now = datetime.utcnow()
        access_payload = {'user_id': user_id, 'exp': now + timedelta(seconds=ACCESS_TOKEN_EXPIRE), 'iat': now}
        refresh_payload = {'user_id': user_id, 'exp': now + timedelta(seconds=REFRESH_TOKEN_EXPIRE), 'iat': now}

        return {
            'access_token': jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM),
            'refresh_token': jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM),
            'token_type': 'Bearer',
            'expires_in': ACCESS_TOKEN_EXPIRE
        }
```

**并发安全说明**：
- `SELECT ... FOR UPDATE` 在事务内获取行锁
- 同一用户的并发登录请求会串行化执行
- 只有一个请求能成功更新 `last_login_at`，其他请求的 Token 在验证时会因 `iat < last_login_at` 而失效

### 管理员账号初始化

管理员凭证**从 `.env` 文件读取**，避免硬编码和污染系统环境变量：

```python
# scripts/setup_database.py 新增函数
from dotenv import load_dotenv
import os
import bcrypt

def create_admin_user(client):
    """创建预置管理员账号（从 .env 读取凭证）"""
    load_dotenv()

    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD')

    if not password:
        print("[Warning] ADMIN_PASSWORD 未在 .env 中设置，跳过管理员创建")
        print("         请在 .env 文件中添加: ADMIN_PASSWORD=your-secure-password")
        return

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # 使用 INSERT IGNORE 保证幂等性（账号已存在则跳过）
    client.execute(
        """INSERT IGNORE INTO users (username, password_hash, role)
           VALUES (%s, %s, 'admin')""",
        (username, password_hash)
    )
    print(f"[DB Init] 管理员账号 '{username}' 已创建/验证")
```

**安全说明**：
- `.env` 文件必须添加到 `.gitignore`，不提交版本控制
- 使用 `INSERT IGNORE` 保证脚本可重复运行（幂等）
- 密码使用 bcrypt 哈希存储，不可逆

### 日志脱敏

敏感字段不得出现在日志中，使用辅助函数处理：

```python
# lib/utils/sanitize.py
SENSITIVE_KEYS = {'password', 'password_hash', 'access_token', 'refresh_token', 'secret', 'token'}

def sanitize_for_log(data: dict) -> dict:
    """移除敏感字段，用于日志输出"""
    if not isinstance(data, dict):
        return data
    return {k: '***' if k.lower() in SENSITIVE_KEYS else v for k, v in data.items()}
```

**全局集成（推荐）**：在请求日志中间件中自动脱敏所有请求/响应体：

```python
# api/middleware/request_logger.py
from lib.utils.sanitize import sanitize_for_log

@app.before_request
def log_request():
    if request.is_json:
        safe_body = sanitize_for_log(request.get_json(silent=True) or {})
        log.debug(f"[{request.method}] {request.path} - body: {safe_body}")

@app.after_request
def log_response(response):
    # 仅在 DEBUG 模式记录响应体
    if app.debug and response.is_json:
        safe_body = sanitize_for_log(response.get_json(silent=True) or {})
        log.debug(f"[{request.method}] {request.path} - response: {safe_body}")
    return response
```

> **说明**：此中间件确保所有路由的请求/响应体在记录时自动过滤敏感词（password, access_token 等），无需在每个路由手动调用。

## 前端项目结构

```
frontend/src/
├── api/              # API 封装
├── components/       # 通用组件
├── pages/            # 页面组件
├── types/            # 类型定义
├── contexts/         # React Context（迭代 2 新增）
│   └── AuthContext.tsx
├── routes/           # 路由配置（迭代 2 新增）
│   └── PrivateRoute.tsx
└── App.tsx
```

## CORS 配置

### 开发环境

前端使用 Vite 代理，无需后端 CORS 配置：

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
})
```

### 生产环境

生产部署时，前后端可能分离部署（不同域名/端口），需配置 `flask-cors`：

```python
# api/__init__.py
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    # CORS 配置（仅生产环境按需启用）
    if os.environ.get('ENABLE_CORS', 'false').lower() == 'true':
        CORS(app, origins=os.environ.get('CORS_ORIGINS', '*').split(','))

    # ...其他初始化
    return app
```

**环境变量说明**：
- `ENABLE_CORS`：是否启用 CORS（默认 `false`）
- `CORS_ORIGINS`：允许的来源，多个用逗号分隔（如 `https://frontend.example.com,https://admin.example.com`）

> **推荐部署方式**：使用 Nginx 反向代理统一入口，避免跨域问题。

## 后端 Schema 待更新项（迭代 3）

### api/schemas/match.py 需要补充的定义

现有 Schema 与实际返回存在差异，需要补齐以下内容：

#### 1. CompositeMatchResultItem 缺少字段

```python
class CompositeMatchResultItem(BaseModel):
    """综合匹配单个结果"""
    id: Optional[int] = Field(default=None, description="代码片段 ID")
    content: str = Field(default="", description="代码内容")
    composite_score: float = Field(description="综合得分")
    kp_count: int = Field(description="涉及的知识点数量")
    kp_details: List[dict] = Field(default_factory=list, description="各知识点详细得分")
    score_aggregation: str = Field(description="使用的聚合方式")
    file_path: Optional[str] = Field(default=None, description="源文件路径")
    # 以下为新增字段
    partial_match: Optional[bool] = Field(default=None, description="是否为部分匹配（降级模式时为 True）")
    difficulty: Optional[float] = Field(default=None, description="难度值（矩阵模式需要）")
```

#### 2. 新增 MatrixResultItem（单KP矩阵模式专用）

矩阵模式返回的结构与列表模式的 `MatchResultItem` 不同（简化版，不含详情字段）：

```python
class MatrixResultItem(BaseModel):
    """矩阵模式匹配结果（简化版）"""
    id: Optional[int] = Field(default=None, description="代码片段 ID")
    content: str = Field(default="", description="代码内容")
    score: float = Field(description="综合得分（不含难度权重）")
    ast_ratio: float = Field(description="AST 匹配率")
    keyword_score: float = Field(description="关键词得分")
    difficulty: float = Field(description="难度值")
    file_path: Optional[str] = Field(default=None, description="源文件路径")
    # 可选字段（内部使用，暴露以便前端缓存/调试）
    content_hash: Optional[str] = Field(default=None, description="内容哈希")
    method_name: Optional[str] = Field(default=None, description="方法名")
    lines_of_code: Optional[int] = Field(default=None, description="代码行数")
    fallback: Optional[bool] = Field(default=None, description="是否为兜底结果")
```

#### 3. 更新 MatrixMatchResponse.matrix 类型

```python
class MatrixMatchResponse(BaseModel):
    """矩阵匹配响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    kp_id: int = Field(description="查询的知识点 ID")
    shape: List[int] = Field(description="矩阵形状 [m, n]")
    levels: List[str] = Field(description="难度级别名称列表")
    per_level: int = Field(description="每级别请求的片段数")
    matrix: Dict[str, List[MatrixResultItem]] = Field(description="按难度分级的代码片段矩阵")  # 更精确类型
    total: int = Field(default=0, description="结果总数")
```

> **注意**：后端 Schema 主要用于文档和类型提示。实际响应由 `SearchService` 直接构建 dict 返回，Pydantic 模型未参与序列化。前端以实际 API 响应为准。

---

## 迭代 1 额外变更记录

> 以下改动在迭代 1 实现过程中根据用户反馈添加，不在原提案范围内。

### 知识点中文名称支持

**背景**：用户要求知识点树显示中文名称，提升可读性。

**变更内容**：

1. **数据库**：`knowledge_points` 表新增 `name_zh VARCHAR(255)` 字段
   ```sql
   ALTER TABLE knowledge_points ADD COLUMN name_zh VARCHAR(255) AFTER name;
   ```

2. **数据**：`kp_dml.sql` 更新，147 条知识点均添加中文翻译
   - 15 个 L1 分类（如 "Core Syntax & Types" → "核心语法与类型"）
   - 32 个 L2 模块
   - 100 个 L3 知识点

3. **后端**：
   - `src/db_manager/database.py`：表定义添加 `name_zh VARCHAR(255)` 字段
   - `src/services/knowledge_service.py`：`get_tree()` CTE 查询添加 `name_zh` 字段

4. **前端**：
   - `types/knowledge.ts`：`KnowledgeTreeNode` 添加 `name_zh: string | null`
   - `KnowledgeTree.tsx`：优先显示中文名，英文名作为灰色副标题
   - `Dashboard.tsx`：当前选中知识点显示中文名

### 知识点树交互优化

**变更内容**：
- 添加 `expandAction="click"` 属性，点击整行即可展开/折叠节点，无需点击小箭头
- 修复 antd Spin 组件 `tip` → `children` deprecated warning
