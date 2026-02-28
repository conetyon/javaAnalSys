/**
 * 知识点相关类型
 */

export interface KnowledgeTreeNode {
  id: number;
  name: string;
  name_zh: string | null;
  parent_id: number | null;
  level: number;
  children: KnowledgeTreeNode[];
  // 后端自动添加，用于 Ant Design Tree 适配
  title: string;
  key: number;
}

export interface KnowledgePoint {
  id: number;
  name: string;
  name_zh: string | null;
  parent_id: number | null;
  level: number;
  keywords?: string;
  ast_template?: string;
}
