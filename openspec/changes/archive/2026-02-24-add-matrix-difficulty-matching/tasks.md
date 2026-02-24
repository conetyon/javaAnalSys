## 1. 数据模式定义

- [ ] 1.1 在 `api/schemas/match.py` 中添加 `DifficultyLevel` 模型
- [ ] 1.2 在 `api/schemas/match.py` 中添加 `MatrixMatchRequest` 请求模型
- [ ] 1.3 在 `api/schemas/match.py` 中添加 `MatrixMatchResponse` 响应模型
- [ ] 1.4 在 `api/schemas/match.py` 中添加 `CompositeMatrixMatchRequest` 请求模型
- [ ] 1.5 在 `api/schemas/match.py` 中添加 `CompositeMatrixMatchResponse` 响应模型

## 2. 服务层实现

- [ ] 2.1 在 `src/services/search_service.py` 中添加 `matrix_search()` 方法
- [ ] 2.2 在 `src/services/search_service.py` 中添加 `composite_matrix_search()` 方法
- [ ] 2.3 实现难度分桶逻辑（默认 easy/medium/hard 三级）
- [ ] 2.4 实现矩阵模式权重归一化（移除难度权重）

## 3. API 路由实现

- [ ] 3.1 在 `api/routes/match.py` 中添加 `/api/match/matrix` 路由
- [ ] 3.2 在 `api/routes/match.py` 中添加 `/api/match/composite/matrix` 路由
- [ ] 3.3 添加请求参数校验和错误处理

## 4. 测试

- [ ] 4.1 添加矩阵匹配单元测试
- [ ] 4.2 添加综合矩阵匹配单元测试
- [ ] 4.3 验证难度分桶边界条件

## 5. 文档更新

- [ ] 5.1 更新 `README.md` 添加矩阵 API 说明
- [ ] 5.2 更新 `CLAUDE.md` API 章节
- [ ] 5.3 更新 `openspec/project.md` 如有必要
