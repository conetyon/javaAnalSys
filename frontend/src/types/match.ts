/**
 * 匹配相关类型
 */

// ============== 列表模式 ==============

// 匹配请求参数（单 KP 列表模式）
export interface MatchParams {
  kp_id: number;
  top_k?: number;
  target_difficulty?: number;
  ast_min_ratio?: number;
  keyword_min_score?: number;
  difficulty_mode?: 'exact' | 'relaxed';
}

// 匹配结果项（列表模式，含完整详情）
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

// ============== 矩阵模式 ==============

// 矩阵匹配请求参数（单 KP）
export interface MatrixMatchParams {
  kp_id: number;
  per_level?: number;
  ast_min_ratio?: number;
  keyword_min_score?: number;
}

// 矩阵模式结果项（简化版，与列表模式不同）
// 注意：矩阵模式不返回 ast_coverage, keyword_hit, keyword_total, details, details_md
export interface MatrixResultItem {
  id: number | null;
  content: string;
  score: number;        // 综合得分（不含难度权重）
  ast_ratio: number;
  keyword_score: number;
  difficulty: number;   // 难度值（用于分级的依据）
  file_path?: string;
  content_hash?: string;
  method_name?: string;
  lines_of_code?: number;
  fallback?: boolean;
}

// 矩阵匹配响应（单 KP）
export interface MatrixMatchResponse {
  code: number;
  message: string;
  kp_id: number;
  shape: [number, number];
  levels: string[];
  per_level: number;
  matrix: Record<string, MatrixResultItem[]>;
  total: number;
}

// ============== 组合匹配 ==============

// 组合匹配请求参数（列表模式）
export interface CompositeMatchParams {
  kp_ids: number[];
  top_k?: number;
  target_difficulty?: number;
  ast_min_ratio?: number;
  keyword_min_score?: number;
  difficulty_mode?: 'exact' | 'relaxed';
  score_aggregation?: 'average' | 'min' | 'sum';
}

// 组合匹配结果项（列表和矩阵模式共用）
export interface CompositeMatchResultItem {
  id: number | null;
  content: string;
  composite_score: number;
  kp_count: number;
  kp_details: Array<{
    kp_id: number;
    kp_name: string;
    score: number;
    ast_ratio?: number;
    keyword_score?: number;
  }>;
  score_aggregation: string;
  file_path?: string;
  partial_match?: boolean;
  difficulty?: number;
}

// 组合匹配响应（列表模式）
export interface CompositeMatchResponse {
  code: number;
  message: string;
  kp_ids: number[];
  total: number;
  data: CompositeMatchResultItem[];
}

// ============== 组合矩阵模式 ==============

// 组合矩阵匹配请求参数
export interface CompositeMatrixMatchParams {
  kp_ids: number[];
  per_level?: number;
  ast_min_ratio?: number;
  keyword_min_score?: number;
  score_aggregation?: 'average' | 'min' | 'sum';
}

// 组合矩阵匹配响应
export interface CompositeMatrixMatchResponse {
  code: number;
  message: string;
  kp_ids: number[];
  shape: [number, number];
  levels: string[];
  per_level: number;
  matrix: Record<string, CompositeMatchResultItem[]>;
  total: number;
}

// ============== 匹配模式 ==============

export type MatchMode = 'list' | 'matrix';
export type SelectionMode = 'single' | 'multiple';

