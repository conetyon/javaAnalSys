# 实现任务清单

按敏捷迭代分阶段实现。

---

## 迭代 1：MVP 核心功能

> 目标：知识点浏览 + 列表模式匹配，无需后端改动
> **状态：已完成** ✅ (2026-02-28)

### 1.1 项目初始化

- [x] 创建 Vite + React + TypeScript 项目（目录：`frontend/`）
- [x] 安装依赖：antd, axios, react-router-dom, react-syntax-highlighter, @types/react-syntax-highlighter
- [x] 创建 `vite.config.ts`，配置代理（将 `/api` 转发到后端 `http://localhost:5000`）
- [ ] 配置 ESLint + Prettier + TypeScript strict 基本规则
- [x] 创建完整目录结构：
  ```
  frontend/src/
  ├── api/              # API 封装层
  │   ├── client.ts     # Axios 实例
  │   ├── knowledge.ts  # 知识点 API
  │   └── match.ts      # 匹配 API
  ├── components/       # 通用组件
  │   ├── KnowledgeTree.tsx
  │   ├── CodeBlock.tsx
  │   └── MatchResultCard.tsx
  ├── pages/            # 页面组件
  │   └── Dashboard.tsx
  ├── types/            # TypeScript 类型定义（模块化）
  │   ├── api.ts        # 通用响应类型
  │   ├── knowledge.ts  # 知识点类型
  │   ├── match.ts      # 匹配类型
  │   └── index.ts      # 统一导出
  └── App.tsx           # 根组件
  ```
  > **迭代扩展**：迭代 2 新增 `contexts/`、`routes/`；迭代 3 新增 `types/auth.ts`、`types/user.ts`

### 1.2 核心组件

- [x] `components/KnowledgeTree.tsx` - 知识点树（三级层级，点击叶子触发匹配）
  - 展开状态持久化到 `sessionStorage`
  - **额外实现**：支持中英文搜索过滤
  - **额外实现**：`expandAction="click"` 点击整行展开/折叠（无需点击小箭头）
- [x] `components/CodeBlock.tsx` - 代码高亮展示（使用 react-syntax-highlighter）
- [x] `components/MatchResultCard.tsx` - 结果卡片
  - 显示代码、得分、文件路径
  - **复制代码按钮**：点击复制到剪贴板，成功后显示 Ant Design message 提示
  - **长代码折叠**：超过 20 行默认折叠，提供展开/收起操作

### 1.3 API 封装

- [x] `api/client.ts` - Axios 实例（配置响应拦截器，统一处理 `ApiException` 格式）
  - 错误透传策略：**400/404/422** 展示给用户，500 仅记录控制台
  - **重要**：`baseURL: '/api'`，调用时使用相对路径（如 `/match`，非 `/api/match`）
- [x] `api/knowledge.ts` - 知识点 API
- [x] `api/match.ts` - 匹配 API（迭代 1 范围：`POST /api/match` 单 KP 匹配）
  - **返回类型**：使用泛型 `MatchResponse<MatchResultItem>`
  ```typescript
  export async function match(params: MatchParams): Promise<MatchResponse<MatchResultItem>> {
    const { data } = await client.post<MatchResponse<MatchResultItem>>('/match', params);
    return data;
  }
  ```
- [x] `types/` - TypeScript 类型定义目录（模块化组织，参考 `design.md` 响应格式）
  - `types/api.ts` - API 通用响应类型：`BaseResponse`, `ApiResponse<T>`, `MatchResponse<T>`
  - `types/knowledge.ts` - 知识点相关类型：`KnowledgeTreeNode`
    ```typescript
    interface KnowledgeTreeNode {
      id: number;
      name: string;
      name_zh: string | null;  // [新增] 中文名称
      parent_id: number | null;
      level: number;
      children: KnowledgeTreeNode[];
      title: string;  // 后端自动添加，等于 name（Ant Design Tree 适配）
      key: number;    // 后端自动添加，等于 id（Ant Design Tree 适配）
    }
    ```
  - `types/match.ts` - 匹配相关类型：`MatchParams`, `MatchResultItem`
    ```typescript
    interface MatchResultItem {
      id: number | null;  // 代码片段 ID（正常情况下不为 null，收藏功能需检查）
      content: string;
      score: number;
      ast_ratio: number;
      ast_coverage: number;
      keyword_score: number;
      keyword_hit: number;
      keyword_total: number;
      difficulty: number;
      details?: string;
      details_md?: string;
      file_path?: string;
    }
    ```
    > **前端防御**：收藏按钮仅在 `id` 有值时可用：`<FavoriteButton disabled={!item.id} snippetId={item.id!} />`
  - `types/index.ts` - 统一导出入口（re-export all）

### 1.4 主页面

- [x] 配置 `App.tsx` 路由（react-router-dom，迭代 1 仅 `/` → Dashboard）
- [x] `pages/Dashboard.tsx` - 主面板布局（左侧树 + 右侧结果区）
  - 支持 URL 查询参数预填（迭代 1 实现解析逻辑，迭代 3 HistoryPage 跳转时使用）
  - 参数：`mode`, `kp_ids`（逗号分隔字符串，需 `split(',').map(Number)` 转数组）, `top_k`, `target_difficulty`
  - **额外实现**：当前选中知识点显示中文名（如存在）
- [x] 列表模式结果展示
- [x] "加载更多"按钮：点击后 `top_k += 5` 并重新请求，结果追加显示
- [x] 参数配置面板（top_k, target_difficulty）
  - **额外实现**：难度滑块步长 0.05，更丝滑
  - **额外实现**：难度参数 Tooltip 说明（仅占 10% 权重）
- [x] 加载状态（Spin/骨架屏）和空态提示
- [x] 错误提示和重试入口

### 1.5 额外改动（不在原提案中）

> 以下改动在实现过程中根据用户反馈添加，需同步到后续迭代

- [x] **数据库**：`knowledge_points` 表新增 `name_zh VARCHAR(255)` 字段
- [x] **数据**：`kp_dml.sql` 更新，147 条知识点均添加中文翻译
- [x] **后端**：`src/services/knowledge_service.py` 的 `get_tree()` 方法返回 `name_zh` 字段
- [x] **后端**：`src/db_manager/database.py` 表定义添加 `name_zh` 字段
- [x] **前端**：`KnowledgeTree` 组件优先显示中文名，英文名作为副标题
- [x] **前端**：搜索框支持中英文双语搜索
- [x] **前端**：点击整行展开/折叠树节点（`expandAction="click"`）

### 1.6 测试验收

- [x] 知识点树加载冒烟测试
- [x] 匹配结果展示冒烟测试
- [x] 前端可运行在 localhost:5173

**迭代 1 交付验收**：✅ 前端可运行，知识点可浏览（中英双语），列表匹配可用

---

## 迭代 2：用户认证系统

> 目标：注册登录 + Token 鉴权

### 2.1 后端基础设施

> **前置说明**：此任务包含现有技术债务修复（如清理重复代码、更新端点信息、修复文件编码），非新增功能。

- [ ] 修复 `requirements.txt` 文件编码（UTF-16 → UTF-8）
- [ ] 修改 `api/middleware/error_handler.py`：新增 `UnauthorizedException` 异常类
- [ ] 修改 `api/middleware/error_handler.py`：新增 `@app.errorhandler(401)` 处理原生 Flask 401 错误
- [ ] 修改 `api/middleware/error_handler.py`：删除 `register_error_handlers()` 函数末尾重复的请求日志中间件
      （`@app.before_request def log_request()` 和 `@app.after_request def log_response()`，位于文件末尾约第 123-133 行）
- [ ] **新增** `lib/utils/sanitize.py` - 日志脱敏辅助函数（参考 `design.md` 实现）
- [ ] 修改 `api/middleware/request_logger.py`：
  - **修改** `log_request_start()`：新增请求体记录（DEBUG 级别，调用 `sanitize_for_log()` 脱敏）
  - **修改** `log_request_end()`：新增响应体记录（仅 DEBUG 模式，调用 `sanitize_for_log()` 脱敏）
- [ ] 更新 `requirements.txt`：
  - 添加 `bcrypt>=4.0.0,<5.0.0`（密码哈希，允许小版本更新以适配不同平台）
  - 添加 `python-dotenv==1.0.1`（从 `.env` 文件加载配置）
  - 添加 `email-validator>=2.0.0,<3.0.0`（Pydantic EmailStr 依赖）
  - **已存在**：`PyJWT==2.10.1`、`flask-cors==6.0.2`（无需重复添加）
- [ ] 修改 `run_api.py`：在 `import sys` 之后、`from lib.globals import api_logger` **之前**添加 `from dotenv import load_dotenv` 和 `load_dotenv()` 调用，并在 `validate_environment()` 函数中校验 `JWT_SECRET` 环境变量
- [ ] **端点信息同步**（三处需保持一致）：
  - 修改 `run_api.py` 的 `print_api_info()` 函数：
    - 删除：`POST /api/bulk-import`, `GET /api/bulk-import/{job_id}`
    - 新增：`POST /api/match/matrix`, `POST /api/match/composite/matrix`
  - 修改 `api/__init__.py`：
    - 更新版本号为 `1.4.0`
    - 在 `endpoints` 字典新增：
      - `"matrix_match": "POST /api/match/matrix"`
      - `"composite_matrix_match": "POST /api/match/composite/matrix"`
  - 修改 `scripts/_internal/init/check_status.py`：从表检查列表中移除 `bulk_import_jobs`
  - **注意**：三处端点/表列表应保持同步，后续可考虑提取为共享配置
- [ ] **CORS 说明**：当前 `api/__init__.py` 已配置 `allow_headers: ["Content-Type", "Authorization"]`，满足 JWT 认证需求。如需生产环境限制来源，可后续添加 `ENABLE_CORS` / `CORS_ORIGINS` 环境变量控制（本迭代无需修改）
- [ ] 创建 `.env.example` 模板文件（提交到版本控制，供参考）
  ```bash
  # .env.example - 复制为 .env 并修改值
  JWT_SECRET=your-32-char-secret-here-change-me
  ACCESS_TOKEN_EXPIRE=900
  REFRESH_TOKEN_EXPIRE=604800
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD=change-me-to-secure-password
  ```
- [ ] 更新 `.gitignore`：确认 `.env` 已包含（✅ 已确认存在于第 8 行）

> **配置方案**：使用项目根目录 `.env` 文件存储敏感配置（避免污染系统环境变量）
> - `JWT_SECRET`：JWT 签名密钥
> - `ACCESS_TOKEN_EXPIRE` / `REFRESH_TOKEN_EXPIRE`：Token 过期时间
> - `ADMIN_USERNAME` / `ADMIN_PASSWORD`：管理员凭证
>
> **已有依赖**：PyJWT==2.10.1, flask-cors==6.0.2（无需重复添加）
>
> **代码清理**：`error_handler.py` 和 `request_logger.py` 存在重复的请求日志中间件，需统一到 `request_logger.py`

### 2.2 数据库 Schema

- [ ] 修改 `src/db_manager/database.py`，在 `_init_tables` 中添加 `users` 表定义
```python
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

### 2.3 后端认证模块

- [ ] `api/schemas/auth.py` - Pydantic 模型（参考 `design.md` 完整定义）
- [ ] `api/middleware/auth.py` - `@require_auth` 和 `@optional_auth` 装饰器
- [ ] `api/routes/auth.py` - register, login, refresh 接口
  - 注册成功返回 **201 Created**（非 200）
- [ ] 更新 `api/routes/__init__.py`：
  - 添加 `from .auth import auth_bp`
  - 在 `register_routes()` 中添加 `app.register_blueprint(auth_bp)`
- [ ] 启动时校验 `JWT_SECRET` 环境变量
- [ ] 为匹配 API 添加 `@optional_auth` 装饰器：
  - `match_knowledge()` (api/routes/match.py - `/api/match`)
  - `batch_match_knowledge()` (api/routes/match.py - `/api/match/batch`)
  - `composite_match_knowledge()` (api/routes/match.py - `/api/match/composite`)
  - `matrix_match_knowledge()` (api/routes/match.py - `/api/match/matrix`)
  - `composite_matrix_match_knowledge()` (api/routes/match.py - `/api/match/composite/matrix`)

### 2.4 后端服务层

- [ ] `src/services/auth_service.py` - 认证服务（含行锁并发安全登录）
  - **注意**：服务初始化采用与 `KnowledgeService` 相同的模式（参考 `src/services/knowledge_service.py:17-19`）：
    ```python
    def __init__(self, db_name: str = None):
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)
    ```
  - **注意**：`_generate_tokens()` 方法**内部**导入 JWT 配置（避免循环依赖）：
    ```python
    def _generate_tokens(self, user_id: int) -> dict:
        from api.middleware.auth import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE, REFRESH_TOKEN_EXPIRE
        # ...
    ```
  - 循环导入已通过懒加载 `_get_auth_service()` 解决（参考 `design.md`）
- [ ] 更新 `src/services/__init__.py`：添加 `from .auth_service import AuthService` 并加入 `__all__`
- [ ] 预置管理员用户脚本：
  - **新增** `scripts/setup_database.py` 的 `create_admin_user()` 函数（从 `.env` 读取 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`，参考 `design.md` 第 922-948 行实现）
  - **修改** `run_all()` 函数：在 `("初始化表结构", init_schema)` **之后**添加 `("创建管理员账号", create_admin_user)` 步骤

### 2.5 前端认证

- [ ] 创建 `frontend/src/contexts/` 目录
- [ ] 创建 `frontend/src/routes/` 目录
- [ ] `api/auth.ts` - 认证 API 封装（register, login, refresh）
- [ ] `contexts/AuthContext.tsx` - 登录状态管理
- [ ] `pages/LoginPage.tsx` - 登录页面
  - 登录成功后检查 `location.state?.from`
  - 有原目标则跳转，否则跳转 `/`
- [ ] `pages/RegisterPage.tsx` - 注册页面
- [ ] `routes/PrivateRoute.tsx` - 路由守卫
  - 未登录时重定向到 `/login`
  - **保存原目标路径**：`<Navigate to="/login" state={{ from: location }} replace />`
- [ ] 更新 `api/client.ts` - Token 拦截器 + 自动刷新逻辑（参考 `design.md` 完整实现）
  - **单设备踢出处理**：当 `error === "Session expired, please login again"` 时，显示特殊提示"您的账号已在其他设备登录"
  - **重要**：refresh 请求必须使用原生 `axios.post()` 而非 `client.post()`，避免拦截器循环
- [ ] 新增 `types/auth.ts`：添加认证相关类型
  - `LoginRequest`, `RegisterRequest`, `TokenResponse`, `UserInfo`
- [ ] 更新 `types/index.ts`：添加 `export * from './auth'`
- [ ] `components/Header.tsx` - 顶部导航栏组件
  - 显示用户名和退出按钮
  - **预留扩展点**：用户菜单使用 Ant Design `Dropdown` 组件，便于迭代 3 添加历史/收藏入口
- [ ] 更新 `pages/Dashboard.tsx`：引入 Header 组件
- [ ] 更新 `App.tsx` 路由配置：
  - 新增：`/login` → LoginPage
  - 新增：`/register` → RegisterPage
  - **保持**：`/` → Dashboard（公开访问，无需 PrivateRoute）
  - **说明**：Dashboard 后端使用 `@optional_auth`，匿名可用；登录用户显示 Header 组件和历史记录功能

### 2.6 测试验收

- [ ] 注册接口冒烟测试（成功/用户名重复）
- [ ] 登录接口冒烟测试（成功/密码错误）
- [ ] Token 刷新冒烟测试
- [ ] 未登录时 Dashboard 页面正常访问（匿名模式可用）
- [ ] 登录后 Dashboard 显示 Header 组件（用户名、退出按钮）
- [ ] 单设备登录测试（新登录使旧 Token 失效）
- [ ] `@require_auth` 和 `@optional_auth` 装饰器单元测试

**迭代 2 交付验收**：用户可注册登录，匿名可访问 Dashboard

---

## 迭代 3：高级功能

> 目标：矩阵模式 + 组合匹配 + 历史收藏

### 3.1 数据库 Schema

- [ ] 修改 `src/db_manager/database.py`：在 `_init_tables` 中添加 `match_history` 和 `favorites` 表定义
```python
# match_history（添加到 statements 列表）
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

# favorites（添加到 statements 列表）
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

- [ ] 修改 `src/db_manager/database.py`：在 `index_statements` 中添加索引
```python
# match_history: 用户+时间复合索引（添加到 index_statements 列表）
('''CREATE INDEX idx_match_history_user_created
    ON match_history(user_id, created_at DESC)''', 'idx_match_history_user_created'),

# favorites: 用户+时间复合索引（收藏列表分页查询）
('''CREATE INDEX idx_favorites_user_created
    ON favorites(user_id, created_at DESC)''', 'idx_favorites_user_created'),
```

### 3.2 后端扩展

- [ ] `api/schemas/user.py` - 历史/收藏请求响应模型（参考 `design.md` 定义）
- [ ] `src/services/user_service.py` - 用户服务（含 `get_favorites()` JOIN 查询、`record_history()` 方法）
  - **注意**：初始化需遵循现有模式 `MySQLClient(db=config.DB_NAME)`
  - **新增方法**：`get_favorite_ids(user_id: int) -> List[int]`（为 `/api/user/favorites/ids` 接口提供数据）
- [ ] 更新 `src/services/__init__.py`：添加 `from .user_service import UserService` 并加入 `__all__`
- [ ] `src/services/knowledge_service.py` - 新增 `get_kp_names(kp_ids: List[int]) -> List[str]` 方法
  - **位置**：在 `get_children()` 方法（第 116-148 行）之后、`_list_to_tree()` 静态方法（第 150 行）之前添加
  - **调用位置**：`user_service.record_history()` 调用此方法获取知识点名称存入 `kp_names` 字段
  ```python
  def get_kp_names(self, kp_ids: List[int]) -> List[str]:
      """批量获取知识点名称（与输入顺序一致，不存在的返回空字符串）"""
      if not kp_ids:
          return []
      placeholders = ','.join(['%s'] * len(kp_ids))
      sql = f"SELECT id, name FROM knowledge_points WHERE id IN ({placeholders})"
      with MySQLClient(db=self.db_name) as client:
          rows = client.fetch_all(sql, tuple(kp_ids))
      name_map = {row['id']: row['name'] for row in rows}
      return [name_map.get(kp_id, '') for kp_id in kp_ids]
  ```
- [ ] `api/routes/user.py` - history, favorites 接口
- [ ] **新增** `GET /api/user/favorites/ids` 轻量接口（必须实现，前端收藏按钮状态依赖）
  - 返回当前用户所有收藏的 snippet_id 数组
  - 响应格式：`{"code": 200, "message": "success", "data": [snippet_id, ...]}`
  - 调用 `user_service.get_favorite_ids(g.user_id)`
- [ ] 更新 `api/routes/__init__.py`：
  - 添加 `from .user import user_bp`
  - 在 `register_routes()` 中添加 `app.register_blueprint(user_bp)`
- [ ] 修改 `api/routes/match.py` - 在路由层调用 `user_service.record_history()`
  - **新增 `get_user_service()` 懒加载单例**（参考现有 `get_search_service()` 模式）：
    ```python
    _user_service = None

    def get_user_service() -> UserService:
        global _user_service
        if _user_service is None:
            from src.services.user_service import UserService
            _user_service = UserService(db_name=config.DB_NAME)
        return _user_service
    ```
  - **复用已有的 `get_knowledge_service()`**：
    ```python
    from api.routes.knowledge import get_knowledge_service
    ```
  - 使用 `@optional_auth` 装饰器（迭代 2 已添加）
  - **写入条件**：
    1. `g.user_id is not None`（已登录用户）
    2. `results and len(results) > 0`（有匹配结果）
  - 匿名访问或空结果不记录

### 3.3 矩阵模式

> **实现说明**：后端 Schema 类型定义主要用于 API 文档和类型提示，实际响应由 Service 层直接构建 dict。前端应以实际 API 响应为准。

- [ ] **后端路由已就绪**：`/api/match/matrix` 和 `/api/match/composite/matrix` 路由已存在，无需新增路由
- [ ] **补充 Schema 类型定义** - 修改 `api/schemas/match.py`：新增 `MatrixResultItem` 模型（简化版，参考 `design.md` 第 1119-1137 行）
  ```python
  class MatrixResultItem(BaseModel):
      """
      矩阵模式匹配结果（简化版）

      与 MatchResultItem 的差异：
      - 不包含：ast_coverage, keyword_hit, keyword_total, details, details_md
      - 新增：content_hash, method_name, lines_of_code, fallback
      """
      id: Optional[int] = Field(default=None, description="代码片段 ID")
      content: str = Field(default="", description="代码内容")
      score: float = Field(description="综合得分（不含难度权重）")
      ast_ratio: float = Field(description="AST 匹配率")
      keyword_score: float = Field(description="关键词得分")
      difficulty: float = Field(description="难度值")
      file_path: Optional[str] = Field(default=None, description="源文件路径")
      content_hash: Optional[str] = Field(default=None, description="内容哈希")
      method_name: Optional[str] = Field(default=None, description="方法名")
      lines_of_code: Optional[int] = Field(default=None, description="代码行数")
      fallback: Optional[bool] = Field(default=None, description="是否为兜底结果")
  ```
- [ ] 修改 `api/schemas/match.py`：`CompositeMatchResultItem` 补充字段
  ```python
  partial_match: Optional[bool] = Field(default=None, description="是否为部分匹配")
  difficulty: Optional[float] = Field(default=None, description="难度值（矩阵模式需要）")
  ```
- [ ] 修改 `api/schemas/match.py`：更新 `MatrixMatchResponse.matrix` 类型为 `Dict[str, List[MatrixResultItem]]`（当前为 `dict`，类型提示不精确）
- [ ] 扩展 `types/match.ts`：添加矩阵和组合匹配类型
  ```typescript
  // 矩阵模式结果项（简化版，与列表模式的 MatchResultItem 不同）
  // 注意：矩阵模式不返回 ast_coverage, keyword_hit, keyword_total, details, details_md
  interface MatrixResultItem {
    id: number | null;    // 代码片段 ID，收藏功能需检查（与 MatchResultItem 保持一致）
    content: string;
    score: number;        // 综合得分（不含难度权重）
    ast_ratio: number;
    keyword_score: number;
    difficulty: number;   // 难度值（用于分级的依据）
    file_path?: string;
    // 以下字段后端返回但非必须使用
    content_hash?: string;   // 内容哈希（用于缓存/去重）
    method_name?: string;    // 方法名
    lines_of_code?: number;  // 代码行数
    fallback?: boolean;      // 是否为兜底结果
  }

  // 组合匹配结果项（列表和矩阵模式共用）
  interface CompositeMatchResultItem {
    id: number | null;  // 代码片段 ID，收藏功能需检查（与 MatchResultItem 保持一致）
    content: string;
    composite_score: number;
    kp_count: number;
    kp_details: Array<{ kp_id: number; kp_name: string; score: number }>;
    score_aggregation: string;
    file_path?: string;
    partial_match?: boolean;  // 是否为部分匹配（降级模式）
    difficulty?: number;      // 难度值（矩阵模式必须，列表模式可选）
  }

  // 单KP矩阵匹配响应
  interface MatrixMatchResponse extends BaseResponse {
    kp_id: number;
    shape: [number, number];
    levels: string[];
    per_level: number;
    matrix: Record<string, MatrixResultItem[]>;  // 使用专用类型
    total: number;
  }

  // 组合知识点列表响应（列表模式，与单 KP 的 MatchResponse 类似但 kp_id → kp_ids）
  interface CompositeMatchResponse extends BaseResponse {
    kp_ids: number[];
    total: number;
    data: CompositeMatchResultItem[];
  }

  // 组合知识点矩阵响应（多 KP，与单 KP 的 kp_id 字段不同）
  interface CompositeMatrixMatchResponse extends BaseResponse {
    kp_ids: number[];
    shape: [number, number];
    levels: string[];
    per_level: number;
    matrix: Record<string, CompositeMatchResultItem[]>;
    total: number;
  }
  ```
  > **重要区别**：
  > - **列表模式**：使用 `MatchResultItem`（含完整详情字段）
  > - **单KP矩阵模式**：使用 `MatrixResultItem`（简化版，无详情字段）
  > - **组合匹配**：使用 `CompositeMatchResultItem`（列表和矩阵模式共用结构）
- [ ] 更新 `api/match.ts`：添加矩阵和组合匹配 API 封装
  - `matchMatrix(kp_id, per_level)` → `POST /api/match/matrix`
  - `matchComposite(kp_ids, aggregation)` → `POST /api/match/composite`
  - `matchCompositeMatrix(kp_ids, per_level)` → `POST /api/match/composite/matrix`
- [ ] 模式切换组件（列表/矩阵 Tab 切换）
- [ ] 矩阵视图（Tab 或分栏展示 easy/medium/hard）

### 3.4 组合匹配

- [ ] 知识点多选功能（Tree 组件 checkable 模式）
- [ ] 多选数量限制（最多 5 个 L3 知识点，超出时提示并阻止勾选）
- [ ] 调用 `/api/match/composite` 接口（后端已就绪）

### 3.5 历史和收藏

> **前置依赖**：需先完成 3.1（数据库 Schema）和 3.2（后端扩展）后才能实现收藏功能

- [ ] `api/user.ts` - 用户 API 封装（getHistory, getFavorites, getFavoriteIds, addFavorite, removeFavorite）
- [ ] 新增 `types/user.ts`：添加用户相关类型
  - `HistoryItem`, `FavoriteItem`, `HistoryResponse`, `FavoritesResponse`
- [ ] 更新 `types/index.ts`：添加 `export * from './user'`
- [ ] `pages/HistoryPage.tsx` - 匹配历史
  - 使用 Ant Design Pagination 组件
  - 支持 page/page_size 参数传递
  - 点击历史项跳转 Dashboard 并预填参数
    - URL 格式：`/?mode=list&kp_ids=101,102&top_k=10`（Dashboard 路由为 `/`）
    - 前端解析：`kp_ids.split(',').map(Number)` 转数组
- [ ] `pages/FavoritesPage.tsx` - 收藏列表
  - **复用组件**：使用 `CodeBlock` 组件显示代码内容
  - 使用 Ant Design Pagination 组件
- [ ] `MatchResultCard` 添加收藏按钮
  - **登录用户**：正常收藏/取消功能
  - **匿名用户**：按钮 `disabled` + Tooltip "请登录后收藏"
  - **收藏状态初始化**（**仅登录用户**）：
    - **状态管理位置**：Dashboard 组件维护 `favoriteIds: Set<number>` 状态
    - Dashboard 挂载时检查 `AuthContext.isLoggedIn`
    - **仅当已登录时**调用 `GET /api/user/favorites/ids`
    - 返回 `snippet_id[]`，存入 `Set<number>` 以提高查找效率（O(1)）
    - **传递给子组件**：`<MatchResultCard favoriteIds={favoriteIds} onFavoriteChange={...} />`
    - MatchResultCard 根据 ID 判断初始状态
- [ ] 更新 `components/Header.tsx`：扩展用户菜单（添加历史、收藏入口）
- [ ] 更新 `App.tsx` 路由配置：
  - `/history` → HistoryPage（使用 PrivateRoute 包裹）
  - `/favorites` → FavoritesPage（使用 PrivateRoute 包裹）

### 3.6 测试验收

- [ ] 收藏添加/取消幂等性测试
- [ ] 历史记录分页测试
- [ ] 矩阵模式 API 对接测试
- [ ] 组合匹配多选测试
- [ ] 多选超过 5 个知识点的前端校验测试
- [ ] **路由守卫测试**：未登录访问 /history 或 /favorites 时重定向到登录页
- [ ] **登录后跳转测试**：从 /favorites 重定向到登录页后，登录成功应返回 /favorites

**迭代 3 交付验收**：矩阵模式可切换，历史收藏可用

---

## 任务统计

| 迭代 | 任务数 | 状态 | 完成度 |
|------|--------|------|--------|
| 迭代 1 | 18 + 7 额外 | ✅ 已完成 | 100% |
| 迭代 2 | 44 | 🔜 待开始 | 0% |
| 迭代 3 | 36 | 🔜 待开始 | 0% |
| **合计** | **105** | - | - |
