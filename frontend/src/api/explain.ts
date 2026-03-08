/**
 * AI 代码解释 API
 * 处理流式解释响应和配额查询
 */

import client from './client';
import { fetchSSE, createSSEController, SSECallbacks, SSEOptions } from '../utils/sse';

// ============== Types ==============

export type UserLevel = 'beginner' | 'intermediate' | 'advanced';

export interface ExplainRequest {
  snippet_id: number;
  kp_id: number;
  kp_ids?: number[];  // 多知识点支持（组合匹配模式）
  user_level?: UserLevel;
}

export interface ChatRequest {
  snippet_id: number;
  kp_id: number;
  kp_ids?: number[];  // 多知识点支持
  question: string;
  session_id?: string;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
}

export interface QuotaInfo {
  daily_limit: number;
  used_today: number;
  remaining: number;
  reset_at: string | null;
  unlimited: boolean;
}

// ============== SSE Streaming APIs ==============

/**
 * 流式请求 AI 代码解释
 */
export function streamExplain(
  request: ExplainRequest,
  callbacks: SSECallbacks<TokenUsage>,
  options?: SSEOptions
): { abort: () => void } {
  const { controller, abort } = createSSEController();

  fetchSSE<TokenUsage>(
    '/api/explain',
    request,
    callbacks,
    { signal: controller.signal, ...options }
  );

  return { abort };
}

/**
 * 流式请求多轮对话
 */
export function streamChat(
  request: ChatRequest,
  callbacks: SSECallbacks<TokenUsage>,
  options?: SSEOptions
): { abort: () => void } {
  const { controller, abort } = createSSEController();

  fetchSSE<TokenUsage>(
    '/api/explain/chat',
    request,
    callbacks,
    { signal: controller.signal, ...options }
  );

  return { abort };
}

// ============== REST APIs ==============

/**
 * 获取用户配额信息
 */
export async function getQuota(): Promise<QuotaInfo> {
  const response = await client.get<{ code: number; data: QuotaInfo }>('/user/quota');
  return response.data.data;
}

/**
 * 检查解释服务健康状态
 */
export async function checkExplainHealth(): Promise<boolean> {
  try {
    const response = await client.get('/explain/health');
    return response.data?.data?.status === 'ok';
  } catch {
    return false;
  }
}
