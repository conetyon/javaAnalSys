## ADDED Requirements

### Requirement: 代码行高亮

CodeBlock 组件 SHALL 支持高亮显示指定的代码行。

#### Scenario: 高亮关键行

- **WHEN** CodeBlock 组件接收 `highlightLines={[3, 4, 5, 6]}` prop
- **THEN** 第 3-6 行显示高亮背景色
- **AND** 高亮样式与语法高亮不冲突

**实现方式**（使用 react-syntax-highlighter 的 lineProps）：
```tsx
<SyntaxHighlighter
  wrapLines
  lineProps={(lineNumber) => ({
    style: highlightLines?.includes(lineNumber)
      ? { backgroundColor: 'rgba(255, 200, 50, 0.2)' }
      : {},
  })}
>
  {code}
</SyntaxHighlighter>
```

#### Scenario: 无高亮行

- **WHEN** CodeBlock 组件未接收 `highlightLines` prop 或为空数组
- **THEN** 所有行正常显示，无额外高亮

### Requirement: AI 解释面板

系统 SHALL 提供 AI 解释面板组件，支持代码解释和多轮问答。

#### Scenario: 触发 AI 解释

- **WHEN** 用户点击代码片段卡片上的"AI 解释"按钮
- **THEN** 显示解释面板
- **AND** 自动调用 `/api/explain` 获取解释
- **AND** 流式显示 AI 回复内容

#### Scenario: SSE 连接断开处理

- **WHEN** SSE 连接中途断开（网络不稳定）
- **THEN** 显示已接收的部分内容
- **AND** 显示"连接中断"提示和"重试"按钮
- **AND** 点击重试按钮可重新发起请求

#### Scenario: 多轮问答

- **WHEN** 用户在解释面板中输入问题并提交
- **THEN** 调用 `/api/explain/chat` 获取回答
- **AND** 保留对话历史，支持上下文连续对话

#### Scenario: AI 生成新示例

- **WHEN** AI 判断当前代码不理想或用户要求换例子
- **THEN** AI 回复中包含新的示例代码
- **AND** 新代码以代码块格式显示，支持语法高亮

#### Scenario: 配额耗尽提示

- **WHEN** 用户配额耗尽时点击"AI 解释"
- **THEN** 显示配额耗尽提示
- **AND** 提示包含配额重置时间
- **AND** 关键行标注仍可见（降级体验）

### Requirement: 配额指示器

系统 SHALL 显示用户当前的 AI 解释配额状态。

#### Scenario: 显示剩余配额

- **WHEN** 登录用户查看页面
- **THEN** 显示"AI 解释: 剩余 38/50 次"或类似提示

#### Scenario: 配额即将耗尽警告

- **WHEN** 用户配额剩余少于 10 次
- **THEN** 配额指示器显示警告色（如黄色）

#### Scenario: 配额耗尽状态

- **WHEN** 用户配额为 0
- **THEN** 配额指示器显示错误色（如红色）
- **AND** 显示"配额已用完，明日 0 点重置"

### Requirement: AI 内容免责声明

系统 SHALL 在 AI 解释面板显示免责声明，明确 AI 生成内容的责任归属。

#### Scenario: 显示免责声明

- **WHEN** AI 解释面板显示内容
- **THEN** 面板底部显示提示文字："AI 生成内容仅供参考，请自行验证代码正确性"
- **AND** 提示文字使用次要样式（灰色、小字体）
