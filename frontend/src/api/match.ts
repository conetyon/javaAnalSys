/**
 * 匹配 API
 */

import client from './client';
import { MatchResponse } from '../types/api';
import {
  MatchParams,
  MatchResultItem,
  MatrixMatchParams,
  MatrixMatchResponse,
  CompositeMatchParams,
  CompositeMatchResponse,
  CompositeMatrixMatchParams,
  CompositeMatrixMatchResponse,
} from '../types/match';

// ============== 列表模式 ==============

/**
 * 单知识点匹配（列表模式）
 */
export async function match(params: MatchParams): Promise<MatchResponse<MatchResultItem>> {
  const { data } = await client.post<MatchResponse<MatchResultItem>>('/match', params);
  return data;
}

/**
 * 组合知识点匹配（列表模式）
 */
export async function matchComposite(params: CompositeMatchParams): Promise<CompositeMatchResponse> {
  const { data } = await client.post<CompositeMatchResponse>('/match/composite', params);
  return data;
}

// ============== 矩阵模式 ==============

/**
 * 单知识点匹配（矩阵模式，按难度分级）
 */
export async function matchMatrix(params: MatrixMatchParams): Promise<MatrixMatchResponse> {
  const { data } = await client.post<MatrixMatchResponse>('/match/matrix', params);
  return data;
}

/**
 * 组合知识点匹配（矩阵模式，按难度分级）
 */
export async function matchCompositeMatrix(params: CompositeMatrixMatchParams): Promise<CompositeMatrixMatchResponse> {
  const { data } = await client.post<CompositeMatrixMatchResponse>('/match/composite/matrix', params);
  return data;
}
