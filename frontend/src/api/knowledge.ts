/**
 * 知识点 API
 */

import client from './client';
import { ApiResponse } from '../types/api';
import { KnowledgeTreeNode, KnowledgePoint } from '../types/knowledge';

// 获取知识点树
export async function getKnowledgeTree(): Promise<KnowledgeTreeNode[]> {
  const { data } = await client.get<ApiResponse<KnowledgeTreeNode[]>>('/knowledge/tree');
  return data.data;
}

// 获取知识点列表
export async function getKnowledgeList(): Promise<KnowledgePoint[]> {
  const { data } = await client.get<ApiResponse<KnowledgePoint[]>>('/knowledge/list');
  return data.data;
}

// 获取单个知识点详情
export async function getKnowledgeById(id: number): Promise<KnowledgePoint> {
  const { data } = await client.get<ApiResponse<KnowledgePoint>>(`/knowledge/${id}`);
  return data.data;
}

// 获取子知识点
export async function getKnowledgeChildren(parentId: number): Promise<KnowledgePoint[]> {
  const { data } = await client.get<ApiResponse<KnowledgePoint[]>>(`/knowledge/${parentId}/children`);
  return data.data;
}
