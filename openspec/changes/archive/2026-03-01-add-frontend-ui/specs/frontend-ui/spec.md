# 前端用户界面规格

按迭代分组需求。

## ADDED Requirements

### Requirement: 知识点树形浏览（迭代 1）

系统 MUST 提供树形组件浏览知识点（左侧边栏三级树形结构）。

#### Scenario: 加载知识点树

- **WHEN** 用户访问主页面
- **THEN** 调用 GET /api/knowledge/tree 获取数据
- **AND** 展示 L1→L2→L3 三级层级结构

#### Scenario: 选择知识点触发匹配

- **WHEN** 用户点击 L3 叶子节点
- **THEN** 自动触发 POST /api/match 请求
- **AND** 右侧显示匹配结果

### Requirement: 知识点树交互细节（迭代 1）

系统 MUST 提供清晰的树交互反馈，便于快速定位。

#### Scenario: 高亮已选节点

- **WHEN** 用户选择某个 L3 节点
- **THEN** 高亮显示当前选中节点

#### Scenario: 保留展开状态

- **WHEN** 用户切换不同知识点或刷新结果
- **THEN** 保持已展开的树节点不折叠
- **AND** 展开状态存储在 `sessionStorage`（页面刷新后仍保持，关闭标签页后重置）

> **实现说明**：使用 `sessionStorage` 存储展开的节点 key 数组，优于内存存储（刷新后丢失）和 `localStorage`（跨会话保持可能造成困惑）。

### Requirement: 代码片段展示（迭代 1）

系统 MUST 提供代码展示组件（卡片形式，含代码、得分、操作按钮）。

#### Scenario: 语法高亮渲染

- **WHEN** 匹配结果加载完成
- **THEN** 使用 react-syntax-highlighter 渲染 Java 代码
- **AND** 显示行号和得分详情

#### Scenario: 复制代码

- **WHEN** 用户点击"复制代码"按钮
- **THEN** 代码内容复制到剪贴板

#### Scenario: 复制反馈

- **WHEN** 复制成功
- **THEN** 显示成功提示（如 Ant Design message）

#### Scenario: 长代码折叠

- **WHEN** 代码片段超过预设行数（如 20 行）
- **THEN** 默认折叠并提供展开/收起操作

### Requirement: 列表模式匹配（迭代 1）

系统 MUST 提供列表模式展示匹配结果（按综合得分排序）。

#### Scenario: 默认列表展示

- **WHEN** 用户选择知识点
- **THEN** 按综合得分降序展示结果

#### Scenario: 参数配置

- **WHEN** 用户调整 top_k 或 target_difficulty
- **THEN** 重新请求并更新结果

#### Scenario: 加载更多

- **WHEN** 用户点击"加载更多"
- **THEN** 增加 top_k 并重新请求
- **AND** 结果追加显示

### Requirement: 状态反馈与错误处理（迭代 1）

系统 MUST 在加载、空结果和错误场景提供清晰反馈。

#### Scenario: 加载状态

- **WHEN** 知识点树或匹配结果请求进行中
- **THEN** 显示加载状态（如 Spin/骨架屏）

#### Scenario: 空结果

- **WHEN** 匹配结果为空
- **THEN** 显示空态提示并建议调整参数

#### Scenario: 请求失败

- **WHEN** API 请求失败（非 401）
- **THEN** 显示错误提示
- **AND** 提供重试入口

### Requirement: 参数校验（迭代 1）

系统 MUST 在前端校验参数，避免无效请求。

#### Scenario: top_k 超出范围

- **WHEN** top_k 小于 1 或超过 50
- **THEN** 提示参数非法并阻止请求

#### Scenario: target_difficulty 超出范围

- **WHEN** target_difficulty 不在 0-1 范围
- **THEN** 提示参数非法并阻止请求

### Requirement: 用户登录（迭代 2）

系统 MUST 提供登录页面和 JWT 认证。

#### Scenario: 登录成功

- **WHEN** 用户输入正确凭据
- **THEN** 获取 access_token 和 refresh_token
- **AND** 存储到 localStorage（MVP）
- **AND** 跳转主页面

#### Scenario: 登录失败

- **WHEN** 用户名或密码错误
- **THEN** 显示错误提示
- **AND** 保留用户名输入，清空密码

#### Scenario: 路由守卫

- **WHEN** 未登录用户访问受保护页面（如 `/history`, `/favorites`）
- **THEN** 重定向到 /login
- **AND** 登录后返回原目标页面
- **NOTE** 主页（Dashboard）公开访问，无需登录

### Requirement: Token 自动刷新（迭代 2）

系统 MUST 实现 Token 自动刷新机制，提升用户体验。

#### Scenario: access_token 过期自动刷新

- **WHEN** API 返回 401 Unauthorized
- **AND** 本地存在 refresh_token
- **THEN** 自动调用 /api/auth/refresh 获取新 access_token
- **AND** 使用新 Token 重试原请求

#### Scenario: 刷新成功后重试

- **WHEN** Token 刷新成功
- **THEN** 原请求自动重试
- **AND** 用户无感知

#### Scenario: 刷新失败跳转登录

- **WHEN** refresh_token 也过期或无效
- **THEN** 弹出模态框提示"登录已过期，请重新登录"
- **AND** 用户点击确认后清理本地所有 Token
- **AND** 重定向到 /login

> **实现说明**：使用 Ant Design `Modal.warning` 或 `Modal.confirm`，避免突然跳转造成用户困惑。

```typescript
// api/client.ts 中的实现示例
import { Modal } from 'antd';

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
```

#### Scenario: 并发请求处理

- **WHEN** 多个请求同时遇到 401
- **THEN** 只发起一次刷新请求
- **AND** 所有等待的请求在刷新成功后重试

#### Scenario: 无 refresh_token

- **WHEN** API 返回 401 且无 refresh_token
- **THEN** 直接清理本地 Token
- **AND** 重定向到 /login

### Requirement: 用户注册（迭代 2）

系统 MUST 提供注册页面。

#### Scenario: 注册成功

- **WHEN** 用户填写有效信息
- **THEN** 创建用户账号
- **AND** 显示成功提示
- **AND** 跳转登录页

#### Scenario: 注册失败

- **WHEN** API 返回 400 Bad Request
- **THEN** 显示错误提示（如"用户名已存在"）
- **AND** 保留表单输入

#### Scenario: 前端校验

- **WHEN** 用户名不符合格式（3-50字符，字母数字下划线）
- **THEN** 实时显示校验错误
- **AND** 阻止提交

### Requirement: 账户操作（迭代 2）

系统 MUST 支持用户退出登录。

#### Scenario: 退出登录

- **WHEN** 用户点击"退出登录"
- **THEN** 清理本地 Token（access_token 和 refresh_token）
- **AND** 重定向到 /login

#### Scenario: 用户信息展示

- **WHEN** 用户已登录
- **THEN** 在顶部导航栏显示用户名

#### Scenario: 被踢出登录（单设备限制）

- **WHEN** API 返回 401 且 `error` 为 "Session expired, please login again"
- **THEN** 显示提示"您的账号已在其他设备登录"
- **AND** 清理本地 Token
- **AND** 重定向到 /login

#### Scenario: 无账号注销入口

- **WHEN** 用户查看账户菜单
- **THEN** 不显示"注销账号"或"删除账号"选项

### Requirement: 矩阵模式（迭代 3）

系统 MUST 提供矩阵模式展示（按难度 easy/medium/hard 分组）。

#### Scenario: 切换到矩阵模式

- **WHEN** 用户点击"按难度分级"
- **THEN** 调用 POST /api/match/matrix
- **AND** 显示 easy/medium/hard 三列（Tab 或分栏）

#### Scenario: 切换回列表模式

- **WHEN** 用户点击"综合推荐"
- **THEN** 调用 POST /api/match
- **AND** 恢复列表展示

#### Scenario: 矩阵空级别

- **WHEN** 某难度级别无匹配结果
- **THEN** 该级别显示空态提示

### Requirement: 组合知识点匹配（迭代 3）

系统 MUST 支持多选知识点组合匹配。

#### Scenario: 启用多选模式

- **WHEN** 用户切换到多选模式
- **THEN** 树组件变为 checkable 模式
- **AND** 显示"开始匹配"按钮

#### Scenario: 多选执行组合匹配

- **WHEN** 用户勾选多个 L3 知识点并点击匹配
- **THEN** 调用 POST /api/match/composite
- **AND** 返回涉及所有知识点的代码

#### Scenario: 多选限制

- **WHEN** 用户勾选超过 5 个知识点
- **THEN** 提示数量超限
- **AND** 阻止继续勾选

### Requirement: 匹配历史（迭代 3）

系统 MUST 记录并展示用户匹配历史。

#### Scenario: 查看历史

- **WHEN** 用户访问历史页面
- **THEN** 显示按时间倒序的匹配记录
- **AND** 每条记录显示知识点名称、匹配模式、时间

#### Scenario: 历史分页

- **WHEN** 历史记录超过一页
- **THEN** 支持分页加载

#### Scenario: 历史空态

- **WHEN** 没有匹配历史
- **THEN** 显示空态提示并引导返回首页

#### Scenario: 从历史重新匹配

- **WHEN** 用户点击历史记录项
- **THEN** 跳转到主页并预填参数
- **AND** 自动执行匹配

> **实现说明**：使用 URL 查询字符串传递参数，格式如：
> `/?mode=composite&kp_ids=101,102&top_k=15&target_difficulty=0.5`
>
> **优势**：
> - 链接可分享、可收藏
> - 支持浏览器前进/后退
> - 前端使用 `useSearchParams` 解析
>
> **参数映射**：
> | URL 参数 | 类型 | 说明 |
> |----------|------|------|
> | `mode` | string | `list` / `matrix` / `composite` |
> | `kp_ids` | string | 逗号分隔的知识点 ID |
> | `top_k` | number | 返回数量 |
> | `target_difficulty` | number | 目标难度 (0-1) |

### Requirement: 代码收藏（迭代 3）

系统 MUST 支持收藏代码片段（结果卡片上的收藏按钮）。

#### Scenario: 收藏代码

- **WHEN** 用户点击收藏按钮
- **THEN** 调用 POST /api/user/favorites
- **AND** 按钮变为已收藏状态（实心图标）

#### Scenario: 取消收藏

- **WHEN** 用户再次点击已收藏按钮
- **THEN** 调用 DELETE /api/user/favorites/{snippet_id}
- **AND** 按钮恢复未收藏状态

#### Scenario: 查看收藏列表

- **WHEN** 用户访问收藏页面
- **THEN** 显示所有收藏的代码片段

#### Scenario: 收藏空态

- **WHEN** 收藏列表为空
- **THEN** 显示空态提示并引导返回首页

#### Scenario: 收藏状态同步

- **WHEN** 代码片段已被收藏
- **AND** 在匹配结果中展示该片段
- **THEN** 收藏按钮显示已收藏状态
