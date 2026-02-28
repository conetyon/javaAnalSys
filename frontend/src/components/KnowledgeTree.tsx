/**
 * 知识点树组件
 * 三级层级展示，点击叶子节点触发匹配
 */

import { useEffect, useState, useMemo } from 'react';
import { Tree, Spin, message, Badge, Input } from 'antd';
import type { TreeProps, TreeDataNode } from 'antd';
import {
  FolderOutlined,
  FolderOpenOutlined,
  CodeOutlined,
  BookOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { getKnowledgeTree } from '../api/knowledge';
import { KnowledgeTreeNode } from '../types/knowledge';

interface KnowledgeTreeProps {
  onSelect: (kpId: number, kpName: string, kpNameZh: string | null, level: number) => void;
  selectedKey?: number;
}

const STORAGE_KEY = 'knowledge_tree_expanded';

// 统计子节点（L3）数量
function countLeafNodes(node: KnowledgeTreeNode): number {
  if (node.level === 3) return 1;
  return node.children.reduce((sum, child) => sum + countLeafNodes(child), 0);
}

// 转换数据添加图标和标题
function transformTreeData(
  nodes: KnowledgeTreeNode[],
  expandedKeys: React.Key[],
  searchText: string
): TreeDataNode[] {
  const searchLower = searchText.toLowerCase();

  return nodes
    .map((node) => {
      const leafCount = countLeafNodes(node);
      const isExpanded = expandedKeys.includes(node.id);
      const matchesSearch = !searchText ||
        node.name.toLowerCase().includes(searchLower) ||
        (node.name_zh && node.name_zh.toLowerCase().includes(searchLower));
      const childrenMatch = node.children.some(
        (child) =>
          child.name.toLowerCase().includes(searchLower) ||
          (child.name_zh && child.name_zh.toLowerCase().includes(searchLower)) ||
          child.children.some((gc) =>
            gc.name.toLowerCase().includes(searchLower) ||
            (gc.name_zh && gc.name_zh.toLowerCase().includes(searchLower))
          )
      );

      // 过滤不匹配的节点
      if (searchText && !matchesSearch && !childrenMatch && node.level === 3) {
        return null;
      }

      // 选择图标
      let icon;
      if (node.level === 1) {
        icon = isExpanded ? <FolderOpenOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#1890ff' }} />;
      } else if (node.level === 2) {
        icon = isExpanded ? <FolderOpenOutlined style={{ color: '#52c41a' }} /> : <BookOutlined style={{ color: '#52c41a' }} />;
      } else {
        icon = <CodeOutlined style={{ color: '#722ed1' }} />;
      }

      // 构建标题（优先显示中文名）
      const displayName = node.name_zh || node.name;
      const title = (
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            flex: 1,
            fontWeight: node.level === 1 ? 600 : node.level === 2 ? 500 : 400,
            fontSize: node.level === 1 ? 14 : 13,
          }}>
            {displayName}
            {node.name_zh && (
              <span style={{ color: '#999', fontSize: 11, marginLeft: 6 }}>
                {node.name}
              </span>
            )}
          </span>
          {node.level < 3 && (
            <Badge
              count={leafCount}
              style={{
                backgroundColor: node.level === 1 ? '#1890ff' : '#52c41a',
                fontSize: 11,
              }}
              size="small"
            />
          )}
        </span>
      );

      const children = node.children.length > 0
        ? transformTreeData(node.children, expandedKeys, searchText).filter(Boolean) as TreeDataNode[]
        : undefined;

      // 如果搜索模式下子节点都被过滤了，且自己不匹配，则隐藏
      if (searchText && children?.length === 0 && !matchesSearch && node.level < 3) {
        return null;
      }

      return {
        // 先展开原始数据用于选择回调
        ...node,
        // 再覆盖 key/title/icon 等属性
        key: node.id,
        title,
        icon,
        children,
        isLeaf: node.level === 3,
      };
    })
    .filter(Boolean) as TreeDataNode[];
}

export default function KnowledgeTree({ onSelect, selectedKey }: KnowledgeTreeProps) {
  const [rawData, setRawData] = useState<KnowledgeTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);
  const [searchText, setSearchText] = useState('');

  // 加载知识点树
  useEffect(() => {
    const loadTree = async () => {
      try {
        const data = await getKnowledgeTree();
        setRawData(data);

        // 恢复展开状态
        const saved = sessionStorage.getItem(STORAGE_KEY);
        if (saved) {
          setExpandedKeys(JSON.parse(saved));
        } else {
          // 默认展开第一级
          setExpandedKeys(data.map((node) => node.id));
        }
      } catch (error) {
        message.error(error instanceof Error ? error.message : '加载知识点失败');
      } finally {
        setLoading(false);
      }
    };

    loadTree();
  }, []);

  // 转换后的树数据
  const treeData = useMemo(
    () => transformTreeData(rawData, expandedKeys, searchText),
    [rawData, expandedKeys, searchText]
  );

  // 搜索时自动展开匹配的节点
  useEffect(() => {
    if (searchText) {
      // 展开所有节点以显示搜索结果
      const allKeys: React.Key[] = [];
      const collectKeys = (nodes: KnowledgeTreeNode[]) => {
        nodes.forEach((node) => {
          if (node.level < 3) {
            allKeys.push(node.id);
          }
          collectKeys(node.children);
        });
      };
      collectKeys(rawData);
      setExpandedKeys(allKeys);
    }
  }, [searchText, rawData]);

  // 保存展开状态
  const handleExpand: TreeProps['onExpand'] = (keys) => {
    setExpandedKeys(keys);
    if (!searchText) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
    }
  };

  // 选择节点
  const handleSelect: TreeProps['onSelect'] = (_, info) => {
    const node = info.node as unknown as KnowledgeTreeNode;
    onSelect(node.id, node.name, node.name_zh, node.level);
  };

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin spinning={true}><span>加载知识点...</span></Spin>
      </div>
    );
  }

  // 统计总数
  const totalL3 = rawData.reduce((sum, node) => sum + countLeafNodes(node), 0);

  return (
    <div>
      {/* 搜索框 */}
      <Input
        placeholder="搜索知识点..."
        prefix={<SearchOutlined style={{ color: '#999' }} />}
        allowClear
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        style={{ marginBottom: 12 }}
      />

      {/* 统计信息 */}
      <div style={{ marginBottom: 8, fontSize: 12, color: '#999' }}>
        共 {rawData.length} 个分类，{totalL3} 个知识点
      </div>

      {/* 树 */}
      <Tree
        treeData={treeData}
        expandedKeys={expandedKeys}
        selectedKeys={selectedKey ? [selectedKey] : []}
        onExpand={handleExpand}
        onSelect={handleSelect}
        showIcon
        blockNode
        expandAction="click"
        style={{
          background: '#fafafa',
          borderRadius: 6,
          padding: '8px 4px',
        }}
      />
    </div>
  );
}
