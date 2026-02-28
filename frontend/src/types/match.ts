/**
 * 匹配相关类型
 */

// 匹配请求参数
export interface MatchParams {
  kp_id: number;
  top_k?: number;
  target_difficulty?: number;
  ast_min_ratio?: number;
  keyword_min_score?: number;
}

// 匹配结果项
export interface MatchResultItem {
  id: number | null;  // 代码片段 ID（正常情况下不为 null，收藏功能需检查）
  content: string;
  score: number;
  ast_ratio: number;
  ast_coverage: number;
  keyword_score: number;
  keyword_hit: number;
  keyword_total: number;
  difficulty: number;
  details?: string;
  details_md?: string;
  file_path?: string;
}
