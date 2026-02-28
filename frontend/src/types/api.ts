/**
 * API 通用响应类型
 */

// 基础响应（所有 API 共用）
export interface BaseResponse {
  code: number;
  message: string;
}

// 通用 API 响应（带 data 字段）
export interface ApiResponse<T> extends BaseResponse {
  data: T;
}

// 匹配响应（带 kp_id 和 total）
export interface MatchResponse<T> extends BaseResponse {
  kp_id: number;
  total: number;
  data: T[];
}

// API 异常响应
export interface ApiException extends BaseResponse {
  error?: string;
  details?: Record<string, unknown>;
}
