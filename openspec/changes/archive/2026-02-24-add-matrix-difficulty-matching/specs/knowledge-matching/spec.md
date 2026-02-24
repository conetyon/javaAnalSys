## ADDED Requirements

### Requirement: 矩阵模式打分策略

系统 SHALL 在矩阵模式下使用不同于列表模式的打分权重，移除难度权重以避免职责重叠。

#### Scenario: 矩阵模式权重归一化

- **WHEN** 使用矩阵匹配端点 (`/api/match/matrix` 或 `/api/match/composite/matrix`)
- **THEN** 系统使用归一化权重：`w_ast=0.22, w_keyword=0.78, w_difficulty=0.0`
- **AND** 难度不参与打分，仅作为分类维度

#### Scenario: 列表模式权重不变

- **WHEN** 使用列表匹配端点 (`/api/match` 或 `/api/match/composite`)
- **THEN** 系统继续使用原有权重：`w_ast=0.2, w_keyword=0.7, w_difficulty=0.1`
- **AND** 难度参与打分

### Requirement: 难度分桶逻辑

系统 SHALL 根据代码片段的难度值将其分配到对应的难度级别桶中。

#### Scenario: 默认三级分桶

- **WHEN** 片段难度值为 0.25
- **THEN** 片段被分配到 "easy" 桶（范围 [0, 0.33)）

#### Scenario: 中等难度分桶

- **WHEN** 片段难度值为 0.5
- **THEN** 片段被分配到 "medium" 桶（范围 [0.33, 0.66)）

#### Scenario: 高难度分桶

- **WHEN** 片段难度值为 0.8
- **THEN** 片段被分配到 "hard" 桶（范围 [0.66, 1.0]）

#### Scenario: 边界值处理

- **WHEN** 片段难度值恰好为 0.33
- **THEN** 片段被分配到 "medium" 桶（左闭右开区间）

### Requirement: 级别内排序

系统 SHALL 在每个难度级别内按语义相关性得分降序排列代码片段。

#### Scenario: 同一级别内按得分排序

- **WHEN** "easy" 级别有 3 个片段，得分分别为 0.8, 0.9, 0.7
- **THEN** 返回顺序为得分 0.9, 0.8, 0.7 的片段

#### Scenario: 得分相同时按 ID 排序

- **WHEN** 两个片段得分相同
- **THEN** 按片段 ID 升序排列，保证结果稳定性
