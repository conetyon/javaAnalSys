/**
 * 矩阵视图组件
 * 按难度等级（easy/medium/hard）分栏展示匹配结果
 */

import { Tabs, Empty, Typography, Tag } from 'antd';
import type { MatrixResultItem, CompositeMatchResultItem, MatchResultItem } from '../types/match';
import MatchResultCard from './MatchResultCard';

const { Text } = Typography;

// 难度等级配置
const LEVEL_CONFIG: Record<string, { label: string; color: string }> = {
  easy: { label: '简单', color: 'green' },
  medium: { label: '中等', color: 'orange' },
  hard: { label: '困难', color: 'red' },
};

interface MatrixViewProps {
  matrix: Record<string, MatrixResultItem[]> | Record<string, CompositeMatchResultItem[]>;
  levels: string[];
  total: number;
  isComposite?: boolean;
  showFavorite?: boolean;
  showExplain?: boolean;  // 是否显示 AI 解释按钮
  kpId?: number;          // 知识点 ID（单选模式 / primary KP）
  kpIds?: number[];       // 多知识点 ID（组合匹配模式）
  kpName?: string;        // 知识点名称
  favoriteIds?: Set<number>;
  onFavoriteToggle?: (snippetId: number, isFavorite: boolean) => void;
}

export default function MatrixView({
  matrix,
  levels,
  total,
  isComposite = false,
  showFavorite = false,
  showExplain = false,
  kpId,
  kpIds,
  kpName,
  favoriteIds = new Set(),
  onFavoriteToggle,
}: MatrixViewProps) {
  if (total === 0) {
    return <Empty description="暂无匹配结果" />;
  }

  // 组合模式也支持 AI 解释（使用 primary KP context）
  const shouldShowExplain = showExplain && !!kpId;

  const tabItems = levels.map((level) => {
    const items = matrix[level] || [];
    const config = LEVEL_CONFIG[level] || { label: level, color: 'default' };

    return {
      key: level,
      label: (
        <span>
          <Tag color={config.color} style={{ marginRight: 4 }}>
            {config.label}
          </Tag>
          <Text type="secondary">({items.length})</Text>
        </span>
      ),
      children: (
        <div>
          {items.length === 0 ? (
            <Empty description={`暂无${config.label}难度的匹配结果`} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            items.map((item, index) => {
              const converted = convertToMatchResultItem(item, isComposite);
              return (
                <MatchResultCard
                  key={item.id || `${level}-${index}`}
                  item={converted}
                  rank={index + 1}
                  showFavorite={showFavorite}
                  showExplain={shouldShowExplain}
                  kpId={kpId}
                  kpIds={kpIds}
                  kpName={kpName}
                  isFavorite={converted.id ? favoriteIds.has(converted.id) : false}
                  onFavoriteToggle={onFavoriteToggle}
                  isComposite={isComposite}
                />
              );
            })
          )}
        </div>
      ),
    };
  });

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">共找到 {total} 个匹配结果，按难度分级展示</Text>
      </div>
      <Tabs items={tabItems} defaultActiveKey="medium" />
    </>
  );
}

/**
 * 将矩阵结果项转换为标准 MatchResultItem 格式
 * 用于复用 MatchResultCard 组件
 */
function convertToMatchResultItem(
  item: MatrixResultItem | CompositeMatchResultItem,
  isComposite: boolean
): MatchResultItem {
  if (isComposite) {
    const compositeItem = item as CompositeMatchResultItem;
    return {
      id: compositeItem.id,
      content: compositeItem.content,
      score: compositeItem.composite_score,
      ast_ratio: 0, // 组合模式不单独显示 AST
      ast_coverage: 0,
      keyword_score: 0,
      keyword_hit: 0,
      keyword_total: compositeItem.kp_count,
      difficulty: compositeItem.difficulty || 0,
      file_path: compositeItem.file_path,
      highlight_ranges: compositeItem.highlight_ranges || [],
    };
  }

  const matrixItem = item as MatrixResultItem;
  return {
    id: matrixItem.id,
    content: matrixItem.content,
    score: matrixItem.score,
    ast_ratio: matrixItem.ast_ratio,
    ast_coverage: 0, // 矩阵模式不返回此字段
    keyword_score: matrixItem.keyword_score,
    keyword_hit: 0, // 矩阵模式不返回此字段
    keyword_total: 0, // 矩阵模式不返回此字段
    difficulty: matrixItem.difficulty,
    file_path: matrixItem.file_path,
    highlight_ranges: matrixItem.highlight_ranges || [],
  };
}
