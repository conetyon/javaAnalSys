# 变更：添加 Java 知识点匹配系统前端界面

## 为什么需要

后端 API 已完整实现，知识点查询和代码匹配功能达到 98.0% 准确率。但目前没有用户界面供终端用户（Java 学习者）使用系统。

## 敏捷迭代计划

本提案采用敏捷开发模式，分 3 个迭代交付，每个迭代可独立部署和验收。

### 迭代 1：MVP 核心功能

**目标**：实现最小可用产品，用户可浏览知识点并获取匹配代码

**状态**：✅ 已完成（2026-02-28）

**交付物**：
- 知识点树形浏览器（支持中英双语）
- 列表模式代码匹配
- 代码语法高亮展示
- 参数配置面板

**额外实现**（超出原计划）：
- 知识点中文名称支持（`name_zh` 字段）
- 点击整行展开/折叠树节点
- 中英文双语搜索过滤

**依赖**：无新增后端开发，使用现有 API（仅扩展 `name_zh` 字段）

**验收标准**：
- [x] 前端项目可运行在 localhost:5173
- [x] 可浏览知识点树（L1→L2→L3），支持中英文显示
- [x] 点击叶子节点触发匹配，显示代码结果
- [x] 代码片段 Java 语法高亮

---

### 迭代 2：用户认证系统

**目标**：实现用户注册登录，为历史/收藏功能奠定基础

**交付物**：
- 用户注册、登录页面
- JWT Token 鉴权
- 路由守卫（未登录重定向）
- 后端认证接口

**依赖**：
- 新增数据库表：`users`
- 新增后端接口：`/api/auth/*`

**验收标准**：
- [ ] 用户可注册新账号
- [ ] 用户可登录获取 Token
- [ ] 未登录用户访问 /history 或 /favorites 页面时重定向到登录页
- [ ] Token 过期后自动刷新或跳转登录

---

### 迭代 3：高级功能

**目标**：完成矩阵模式、组合匹配、历史和收藏功能

**交付物**：
- 矩阵模式（按难度分级）
- 组合知识点匹配
- 匹配历史记录
- 代码收藏功能

**依赖**：
- 新增数据库表：`match_history`, `favorites`
- 新增后端接口：`/api/user/*`

**验收标准**：
- [ ] 可切换列表/矩阵模式
- [ ] 可多选知识点进行组合匹配
- [ ] 可查看匹配历史
- [ ] 可收藏/取消收藏代码片段

---

## 技术栈选型

**前端**：

- React 18.x + TypeScript 5.x
- Ant Design 5.x
- react-syntax-highlighter
- Vite + Axios

**新增（认证相关）**：
- PyJWT + bcrypt（后端）
- React Context（前端状态）

## 工程实践与编码规范

- 前端引入 ESLint + Prettier，保持一致的代码风格
- TypeScript 开启 `strict` 基本约束（不额外引入复杂泛型）
- API 调用统一封装，集中处理错误码、空态和加载态
- 每次迭代包含最小测试：接口冒烟 + 关键 UI 交互

## 数据库 Schema 变更

| 迭代 | 新增表 | 实现方式 |
|------|--------|----------|
| 迭代 2 | `users` | 修改 `src/db_manager/database.py` 的 `_init_tables` 方法 |
| 迭代 3 | `match_history`, `favorites` | 修改 `src/db_manager/database.py` 的 `_init_tables` 方法 |

## 后端实现准则

后端新增代码需与现有风格一致：

| 项目 | 准则 | 参考 |
|------|------|------|
| 路由 | Flask Blueprint | `api/routes/__init__.py` |
| 校验 | Pydantic BaseModel | `api/schemas/match.py` |
| 服务 | 懒加载单例 | `api/routes/knowledge.py` |
| 日志 | `lib.globals.api_logger` | `api/routes/match.py` |
| 数据库 | `CREATE TABLE IF NOT EXISTS` | `src/db_manager/database.py` |

## 设计决策（简化原则）

本提案采用以下简化决策，降低实现复杂度：

| 决策 | 选择 | 理由 |
|------|------|------|
| 多设备登录 | **禁止**，新登录踢出旧设备 | 无需服务端存储 Token，通过 `last_login_at` 比对实现 |
| Token 轮换 | **不轮换** refresh_token | 减少复杂度，7 天过期即失效 |
| 用户注销 | **不提供**自助注销 | 仅管理员可删除账号，减少边界情况 |
| 登录限流 | **MVP 不实现** | 简化实现，生产环境可后续添加 |
| 历史记录 kp_names | **冗余存储** | 避免查询时 JOIN，平衡存储与速度 |
| 收藏片段删除 | **级联删除** | FK CASCADE 自动清理，保持数据一致性 |

## 风险评估

| 风险 | 缓解措施 |
|------|----------|
| 迭代间依赖 | 迭代 1 可独立运行，不依赖认证 |
| Token 安全 | access_token 15 分钟过期，refresh_token 7 天；MVP 暂存 localStorage，部署 HTTPS |
| localStorage XSS 风险 | MVP 可接受；生产环境建议使用 HttpOnly Cookie 或迁移到 BFF 模式 |
| 开发周期 | 每迭代 1-2 周，可灵活调整范围 |
| JWT Secret 泄露 | 从环境变量读取，不提交代码；启动时校验 |

## 成功标准（按迭代）

| 迭代 | 核心指标 |
|------|----------|
| 迭代 1 | 知识点浏览 + 列表匹配可用 |
| 迭代 2 | 用户可注册登录 |
| 迭代 3 | 矩阵模式前端对接 + 历史收藏完整 |

## 技术债务跟踪

以下为已识别的技术债务，需在后续迭代或生产部署前处理：

| ID | 优先级 | 描述 | 触发条件 | 解决方案 |
|----|--------|------|----------|----------|
| TD-001 | P2 | localStorage 存储 JWT 存在 XSS 风险 | 生产部署前 | 迁移到 HttpOnly Cookie + SameSite=Strict |
| TD-002 | P3 | 密码复杂度校验未启用 | 用户量增长后 | 启用后端 Pydantic 校验 + 前端实时提示 |
| TD-003 | P3 | 登录限流未实现 | 发现暴力破解尝试 | 添加 IP 级别限流（5次/分钟） |
| TD-004 | P4 | 端点列表两处维护易遗漏同步 | 新增端点时 | 提取共享常量 `ENDPOINT_INFO` 到 `api/constants.py` |

**TD-001 详细说明**：
- **当前状态**：MVP 使用 localStorage 存储 access_token 和 refresh_token
- **风险**：若应用存在 XSS 漏洞，攻击者可窃取 Token
- **缓解措施**（当前）：
  - 前端避免使用 `dangerouslySetInnerHTML`
  - 依赖 React 默认的 XSS 防护
  - access_token 15 分钟过期，限制窃取后的有效时间
- **目标方案**：
  - 后端在 `/api/auth/login` 响应中通过 `Set-Cookie` 写入 Token
  - Cookie 属性：`HttpOnly; Secure; SameSite=Strict`
  - 前端无需 localStorage，由浏览器自动携带 Cookie
