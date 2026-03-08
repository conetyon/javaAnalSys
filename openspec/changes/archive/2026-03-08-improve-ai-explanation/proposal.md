# Change: AI 代码解释功能优化

## Why

v1.6.0 完成了 AI 代码解释的基础功能，但存在以下问题：
1. 综合知识点矩阵模式下缺少 AI 解释入口
2. Prompt 构建需要验证知识点信息的准确性和完整性
3. LLM 响应延迟较高（~37秒），影响用户体验
4. **前端 SSE 在 fallback 切换时未实时更新**：主 endpoint 失败切换 fallback 后，前端卡住不显示内容

## What Changes

### 迭代 1：功能完善
- [x] 综合知识点矩阵结果卡片添加 AI 解释按钮
- [x] 验证并优化 ExplainService 的 prompt 构建逻辑
- [x] 确保知识点名称、关键词、AST 模板正确传递给 LLM
- [x] **修复 fallback 模型配置**：`gpt-5.2-codex` → `gpt-5.2-chat`
- [x] **新增多知识点支持**：组合匹配模式下合并所有 KP 的 keywords 和 highlights

### 迭代 2：性能优化
- [ ] 分析 LLM 响应延迟瓶颈
- [ ] 考虑 prompt 精简或分段生成
- [ ] 评估缓存策略（相同 snippet+kp 组合）

## Impact

- Affected specs: `frontend-ui`
- Affected code:
  - `frontend/src/components/MatchResultCard.tsx` - 添加 kpIds 参数
  - `frontend/src/components/MatrixView.tsx` - 移除组合模式 AI 解释限制
  - `frontend/src/components/CodeExplainer.tsx` - 支持 kpIds 数组
  - `frontend/src/pages/Dashboard.tsx` - 传递 kpIds 给矩阵和组合模式
  - `frontend/src/api/explain.ts` - 添加 kp_ids 请求参数
  - `api/schemas/explain.py` - 添加 kp_ids 可选字段
  - `api/routes/explain.py` - 传递 kp_ids 给 ExplainService
  - `src/services/explain_service.py` - 支持多知识点的 prompt 构建
  - `config/llm.yaml` - 修复 fallback 模型 ID

## Success Criteria

1. ✅ 所有匹配结果卡片（列表/矩阵/组合）都有 AI 解释入口
2. ✅ Prompt 包含完整的知识点上下文（支持多知识点合并）
3. ✅ Fallback 模型配置修复（使用支持 chatCompletion 的模型）
4. ⏳ 平均响应时间降低 30%（目标：< 25秒）- 迭代 2

## Configuration Reminder

**已完成**: 修改 `config/llm.yaml` 中 fallback 模型 ID：
- 原配置：`gpt-5.2-codex`（不支持 chatCompletion）
- 新配置：`gpt-5.2-chat`
