# Tasks: AI 代码解释功能优化

## 迭代 1：功能完善

### 1.1 前端 - 矩阵模式 AI 解释入口
- [x] 1.1.1 检查 `MatchResultCard.tsx` 当前 AI 解释按钮的渲染条件
- [x] 1.1.2 确保矩阵模式（`/api/match/matrix`）返回的结果也显示 AI 解释按钮
- [x] 1.1.3 确保组合矩阵模式（`/api/match/composite/matrix`）返回的结果也显示 AI 解释按钮
- [x] 1.1.4 验证 `CodeExplainer` 组件在矩阵模式下正常工作

### 1.2 后端 - Prompt 验证与优化
- [x] 1.2.1 审查 `ExplainService._build_explain_messages()` 方法
- [x] 1.2.2 验证知识点信息完整性：name, name_zh, keywords, ast_template
- [x] 1.2.3 验证代码片段信息完整性：content, file_path, method_name
- [x] 1.2.4 添加 prompt 调试日志（DEBUG 级别）
- [ ] 1.2.5 测试不同知识点的 prompt 输出质量

### 1.3 后端 - Fallback 流式响应修复
- [x] 1.3.1 分析 `lib/client/llm.py` 中 fallback 切换时的 generator 行为
- [x] 1.3.2 确认 fallback 返回的 chunk 是否正确 yield 给调用方
- [x] 1.3.3 检查 `stream_completion()` 在 primary error 后是否继续 yield fallback 内容
- [ ] 1.3.4 添加 fallback 切换时的调试日志：每个 chunk 的 yield 时机
- [ ] 1.3.5 测试场景：主 API 失败 → fallback 成功 → 前端实时显示
- [x] 1.3.6 **配置修复**：修改 fallback 模型 ID 为 `gpt-5.2-chat`

### 1.4 多知识点支持（新增）
- [x] 1.4.1 修改 API Schema 支持 `kp_ids` 数组参数
- [x] 1.4.2 修改 `ExplainService.stream_explain()` 支持多知识点
- [x] 1.4.3 合并多知识点的 keywords 和 highlights
- [x] 1.4.4 前端传递 kpIds 到 CodeExplainer 组件

### 1.5 测试验证
- [ ] 1.5.1 测试单知识点列表模式 AI 解释
- [ ] 1.5.2 测试单知识点矩阵模式 AI 解释
- [ ] 1.5.3 测试组合知识点列表模式 AI 解释
- [ ] 1.5.4 测试组合知识点矩阵模式 AI 解释
- [ ] 1.5.5 测试 LLM fallback 切换

## 迭代 2：性能优化

### 2.1 性能分析
- [ ] 2.1.1 添加详细的时间戳日志（请求开始、LLM 首字节、完成）
- [ ] 2.1.2 分析 prompt token 数量与响应时间的关系
- [ ] 2.1.3 评估网络延迟 vs LLM 处理时间

### 2.2 优化措施
- [ ] 2.2.1 精简 system prompt（移除冗余说明）
- [ ] 2.2.2 考虑分段生成（先概述，用户点击后详解）
- [ ] 2.2.3 评估响应缓存策略（Redis/内存 LRU）
- [ ] 2.2.4 考虑预生成热门知识点的解释模板

### 2.3 监控与告警
- [ ] 2.3.1 添加 LLM 响应时间指标到 `/api/metrics`
- [ ] 2.3.2 设置慢请求告警阈值（> 30秒）

## 完成标准

- [x] 所有匹配模式都有 AI 解释入口
- [x] Prompt 包含完整的知识点信息（支持多知识点）
- [ ] 平均响应时间 < 25 秒（迭代 2）
