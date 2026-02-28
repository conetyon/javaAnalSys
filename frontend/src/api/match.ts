/**
 * 匹配 API
 */

import client from './client';
import { MatchResponse } from '../types/api';
import { MatchParams, MatchResultItem } from '../types/match';

// 单知识点匹配
export async function match(params: MatchParams): Promise<MatchResponse<MatchResultItem>> {
  const { data } = await client.post<MatchResponse<MatchResultItem>>('/match', params);
  return data;
}
