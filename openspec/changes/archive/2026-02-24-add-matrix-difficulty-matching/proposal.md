# Change: 添加按难度分级的矩阵匹配功能

## Why

当前匹配 API 返回扁平列表，无法按难度级别分类展示。教育场景需要按学习者水平（初级/中级/高级）分级推荐代码示例。

## What Changes

- 新增 `POST /api/match/matrix` 端点，单知识点按难度分级返回
- 新增 `POST /api/match/composite/matrix` 端点，综合知识点按难度分级返回
- 矩阵模式下难度作为分类维度，不参与打分（权重归零）
- 新增 Pydantic 请求/响应数据模式

## Impact

- Affected specs: `api-service`, `knowledge-matching`
- Affected code: `api/routes/match.py`, `api/schemas/match.py`, `src/services/search_service.py`
