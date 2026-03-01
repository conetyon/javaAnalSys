# user-auth Specification

## Purpose
User authentication and authorization system providing JWT-based authentication, user registration/login, match history tracking, and code snippet favorites management. Supports single-device login policy and automatic session management.
## Requirements
### Requirement: 用户注册接口（迭代 2）

系统 MUST 提供用户注册 API（`POST /api/auth/register`）。

#### Scenario: 字段校验规则

- **WHEN** 收到注册请求
- **THEN** 校验以下规则：
  - `username`: 3-50 字符，仅字母/数字/下划线
  - `password`: 8-128 字符
  - `email`: 可选，符合邮箱格式

#### Scenario: 成功注册

- **WHEN** 请求携带有效用户名、密码
- **THEN** 创建用户记录，密码使用 bcrypt 哈希存储
- **AND** 响应 201 Created，body 包含 `code`, `message`

#### Scenario: 用户名已存在

- **WHEN** 用户名已被注册
- **THEN** 响应 400 Bad Request
- **AND** `error` 字段说明原因

#### Scenario: 必填字段缺失

- **WHEN** 请求缺少 username 或 password
- **THEN** 响应 400 Bad Request

### Requirement: 用户登录接口（迭代 2）

系统 MUST 提供登录 API（`POST /api/auth/login`），返回 JWT Token。

#### Scenario: 登录成功

- **WHEN** 请求携带正确凭据
- **THEN** 返回 access_token（15 分钟过期）和 refresh_token（7 天过期）

#### Scenario: 返回结构统一

- **WHEN** 登录成功
- **THEN** 响应包含 `code`, `message`, `data`
- **AND** `data` 包含 `access_token`, `refresh_token`, `token_type`, `expires_in`

#### Scenario: 凭据错误

- **WHEN** 用户名存在但密码错误
- **THEN** 响应 401 Unauthorized
- **AND** 不透露具体是用户名还是密码错误

#### Scenario: 用户不存在

- **WHEN** 用户名不存在
- **THEN** 响应 401 Unauthorized
- **AND** 返回信息与密码错误相同（防止用户枚举）

#### Scenario: 必填字段缺失

- **WHEN** 请求缺少 username 或 password
- **THEN** 响应 400 Bad Request

### Requirement: Token 刷新接口（迭代 2）

系统 MUST 提供 Token 刷新 API（`POST /api/auth/refresh`）。

#### Scenario: 刷新成功

- **WHEN** 请求携带有效 refresh_token
- **THEN** 返回新的 access_token

#### Scenario: 返回结构统一

- **WHEN** 刷新成功
- **THEN** 响应包含 `code`, `message`, `data`
- **AND** `data` 包含 `access_token`, `expires_in`

#### Scenario: refresh_token 无效

- **WHEN** refresh_token 签名无效或被篡改
- **THEN** 响应 401 Unauthorized

#### Scenario: refresh_token 过期

- **WHEN** refresh_token 已过期（超过 7 天）
- **THEN** 响应 401 Unauthorized

#### Scenario: refresh_token 缺失

- **WHEN** 请求未携带 refresh_token
- **THEN** 响应 400 Bad Request

### Requirement: JWT 鉴权装饰器（迭代 2）

系统 MUST 提供 `@require_auth` 装饰器验证 Token。

#### Scenario: Token 有效

- **WHEN** 请求携带有效 Authorization Bearer Token
- **THEN** 请求正常处理
- **AND** 可通过 `g.user_id` 获取当前用户 ID

#### Scenario: Token 过期或无效

- **WHEN** access_token 已过期（超过 15 分钟）或签名无效
- **THEN** 响应 401 Unauthorized
- **AND** `error` 字段值为 "Invalid or expired token"（统一错误信息，不泄露具体原因）

#### Scenario: Token 签名无效

- **WHEN** Token 签名被篡改
- **THEN** 响应 401 Unauthorized
- **AND** `error` 字段值为 "Invalid or expired token"（与过期场景统一）

#### Scenario: Authorization Header 缺失

- **WHEN** 请求未携带 Authorization Header
- **THEN** 响应 401 Unauthorized

#### Scenario: Bearer 格式错误

- **WHEN** Authorization Header 不是 "Bearer {token}" 格式
- **THEN** 响应 401 Unauthorized

#### Scenario: 单设备登录校验失败

- **WHEN** Token 签发时间早于用户最后登录时间
- **THEN** 响应 401 Unauthorized
- **AND** `error` 字段值为 "Session expired, please login again"
- **AND** 前端应清除本地 Token 并跳转登录页

### Requirement: 单设备登录策略（迭代 2）

系统 MUST 限制同一账号只能在一个设备登录。

#### Scenario: 新设备登录踢出旧设备

- **WHEN** 用户在新设备登录
- **THEN** 更新 `users.last_login_at` 为当前时间
- **AND** 旧设备的后续请求返回 401（Token 签发时间 < last_login_at）

#### Scenario: 实现机制

- **GIVEN** Token 包含 `iat`（签发时间戳）
- **AND** 数据库存储 `users.last_login_at`
- **WHEN** @require_auth 验证 Token
- **THEN** 比对 `iat` >= `last_login_at.timestamp()`
- **AND** 不满足则拒绝请求

### Requirement: 匹配历史接口（迭代 3）

系统 MUST 提供匹配历史 API（`GET /api/user/history`）。

> **幂等性说明**：历史记录为用户行为日志，允许重复写入，不做去重。

#### Scenario: 查询历史

- **WHEN** 已登录用户请求 `GET /api/user/history?page=1&page_size=20`
- **THEN** 返回当前用户的匹配历史（分页，按时间倒序）
- **AND** 默认 `page=1`, `page_size=20`

#### Scenario: 历史记录自动写入

- **WHEN** 已登录用户调用匹配 API
- **AND** 响应 HTTP 200 且 `data` 数组长度 > 0
- **THEN** 后端自动写入一条历史记录
- **AND** 记录包含 `kp_ids`, `kp_names`（冗余存储）, `params`, `mode`

#### Scenario: 空结果不写入

- **WHEN** 匹配 API 返回空结果或请求失败
- **THEN** 不写入历史记录

#### Scenario: 未认证访问

- **WHEN** 未携带有效 Authorization Token
- **THEN** 响应 401 Unauthorized

#### Scenario: 返回结构统一

- **WHEN** 查询历史成功
- **THEN** 响应包含 `code`, `message`, `data`, `total`, `page`, `page_size`

#### Scenario: 空历史

- **WHEN** 用户没有历史记录
- **THEN** 返回空数组 `data: []`，`total: 0`

### Requirement: 收藏接口（迭代 3）

系统 MUST 提供收藏 API（`/api/user/favorites`）。

#### Scenario: 添加收藏

- **WHEN** 已登录用户 `POST /api/user/favorites` 携带 `snippet_id`
- **THEN** 创建收藏记录
- **AND** 响应 200 OK（或 201 Created）

#### Scenario: 重复收藏（幂等）

- **WHEN** `snippet_id` 已被该用户收藏
- **THEN** 响应 200 OK
- **AND** 不创建重复记录（唯一约束保证）

#### Scenario: 取消收藏

- **WHEN** 已登录用户 `DELETE /api/user/favorites/{snippet_id}`
- **THEN** 删除收藏记录
- **AND** 响应 200 OK

#### Scenario: 取消不存在的收藏（幂等）

- **WHEN** 收藏记录不存在
- **THEN** 响应 200 OK（幂等操作）

#### Scenario: 查询收藏列表

- **WHEN** 已登录用户 `GET /api/user/favorites?page=1&page_size=20`
- **THEN** 返回收藏列表（分页，按收藏时间倒序）
- **AND** 包含代码片段内容（JOIN code_snippets）
- **AND** 默认 `page=1`, `page_size=20`

#### Scenario: 未认证访问

- **WHEN** 未携带有效 Authorization Token
- **THEN** 响应 401 Unauthorized

#### Scenario: 返回结构统一

- **WHEN** 查询收藏成功
- **THEN** 响应包含 `code`, `message`, `data`, `total`, `page`, `page_size`

#### Scenario: 空收藏

- **WHEN** 用户没有收藏
- **THEN** 返回空数组 `data: []`，`total: 0`

### Requirement: 级联删除行为（迭代 3）

系统 MUST 在删除用户或代码片段时自动清理关联数据。

#### Scenario: 用户删除级联

- **WHEN** 用户账号被删除（仅管理员可操作）
- **THEN** 自动删除该用户的所有历史记录
- **AND** 自动删除该用户的所有收藏
- **AND** 不影响其他用户的数据

#### Scenario: 代码片段删除级联

- **WHEN** 代码片段被删除
- **THEN** 自动删除所有用户对该片段的收藏记录（FK CASCADE）

### Requirement: 用户无法自行注销账号

系统 MUST NOT 提供用户自助注销功能。

#### Scenario: 无注销入口

- **WHEN** 用户访问任何页面
- **THEN** 不存在"注销账号"或"删除账号"选项
- **AND** 账号删除仅限管理员后台操作

