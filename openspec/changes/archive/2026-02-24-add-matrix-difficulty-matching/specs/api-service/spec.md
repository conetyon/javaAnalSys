## ADDED Requirements

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
