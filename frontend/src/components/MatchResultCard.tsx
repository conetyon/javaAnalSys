/**
 * 匹配结果卡片组件
 * 展示代码、得分、文件路径，支持复制、折叠、收藏、AI 解释
 */

import { useState, useMemo } from 'react';
import { Card, Typography, Space, Button, Tag, message, Tooltip } from 'antd';
import {
  CopyOutlined,
  DownOutlined,
  UpOutlined,
  StarOutlined,
  StarFilled,
  RobotOutlined
} from '@ant-design/icons';
import CodeBlock from './CodeBlock';
import CodeExplainer from './CodeExplainer';
import { MatchResultItem, HighlightRange } from '../types/match';

const { Text } = Typography;

interface MatchResultCardProps {
  item: MatchResultItem;
  rank: number;
  kpId?: number;           // 知识点 ID（用于 AI 解释）
  kpIds?: number[];        // 多知识点 ID（组合匹配模式）
  kpName?: string;         // 知识点名称（用于 AI 解释）
  extra?: React.ReactNode;  // 额外内容（如组合匹配的知识点列表）
  isFavorite?: boolean;     // 是否已收藏
  onFavoriteToggle?: (snippetId: number, isFavorite: boolean) => void;  // 收藏切换回调
  showFavorite?: boolean;   // 是否显示收藏按钮
  showExplain?: boolean;    // 是否显示 AI 解释按钮
  isComposite?: boolean;    // 是否为组合匹配模式（隐藏 AST/KW 指标）
}

const MAX_LINES_COLLAPSED = 20;

// 从 highlight_ranges 提取需要高亮的行号数组
function extractHighlightLines(ranges?: HighlightRange[]): number[] {
  if (!ranges || ranges.length === 0) return [];
  const lines: number[] = [];
  for (const range of ranges) {
    for (let line = range.start_line; line <= range.end_line; line++) {
      lines.push(line);
    }
  }
  return [...new Set(lines)].sort((a, b) => a - b);
}

export default function MatchResultCard({
  item,
  rank,
  kpId,
  kpIds,
  kpName,
  extra,
  isFavorite = false,
  onFavoriteToggle,
  showFavorite = false,
  showExplain = false,
  isComposite = false,
}: MatchResultCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [showExplainer, setShowExplainer] = useState(false);

  const lines = item.content.split('\n');
  const needsFolding = lines.length > MAX_LINES_COLLAPSED;
  const displayCode = expanded ? item.content : lines.slice(0, MAX_LINES_COLLAPSED).join('\n');

  // 计算高亮行（memoized）
  const highlightLines = useMemo(
    () => extractHighlightLines(item.highlight_ranges),
    [item.highlight_ranges]
  );

  // 复制代码
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(item.content);
      message.success('代码已复制到剪贴板');
    } catch {
      message.error('复制失败，请手动选择复制');
    }
  };

  // 收藏切换
  const handleFavorite = async () => {
    if (!onFavoriteToggle || !item.id) return;
    setFavoriteLoading(true);
    try {
      await onFavoriteToggle(item.id, !isFavorite);
    } finally {
      setFavoriteLoading(false);
    }
  };

  // 得分颜色
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'green';
    if (score >= 0.6) return 'blue';
    if (score >= 0.4) return 'orange';
    return 'default';
  };

  // 难度标签
  const getDifficultyLabel = (diff: number) => {
    if (diff <= 0.3) return { text: '简单', color: 'green' };
    if (diff <= 0.6) return { text: '中等', color: 'orange' };
    return { text: '困难', color: 'red' };
  };

  const diffLabel = getDifficultyLabel(item.difficulty);

  return (
    <Card
      size="small"
      title={
        <Space>
          <Tag color="blue">#{rank}</Tag>
          <Tag color={getScoreColor(item.score)}>
            {isComposite ? '综合得分' : '得分'}: {(item.score * 100).toFixed(1)}%
          </Tag>
          {/* 单选模式显示 AST/KW 指标 */}
          {!isComposite && (
            <>
              <Tooltip title="AST 匹配率">
                <Tag>AST: {(item.ast_ratio * 100).toFixed(0)}%</Tag>
              </Tooltip>
              <Tooltip title={`关键词命中: ${item.keyword_hit}/${item.keyword_total}`}>
                <Tag>KW: {(item.keyword_score * 100).toFixed(0)}%</Tag>
              </Tooltip>
            </>
          )}
          {/* 组合模式显示知识点数量 */}
          {isComposite && item.keyword_total > 0 && (
            <Tooltip title="涉及的知识点数量">
              <Tag color="purple">涉及 {item.keyword_total} 个知识点</Tag>
            </Tooltip>
          )}
          <Tooltip title={`代码复杂度: ${(item.difficulty * 100).toFixed(0)}%`}>
            <Tag color={diffLabel.color}>{diffLabel.text}</Tag>
          </Tooltip>
          {/* 高亮行提示 */}
          {highlightLines.length > 0 && (
            <Tooltip title={`关键行: ${highlightLines.join(', ')}`}>
              <Tag color="gold">标注 {highlightLines.length} 行</Tag>
            </Tooltip>
          )}
        </Space>
      }
      extra={
        <Space>
          {/* AI 解释按钮 */}
          {showExplain && item.id && kpId && (
            <Tooltip title="AI 代码解释">
              <Button
                type={showExplainer ? 'primary' : 'text'}
                icon={<RobotOutlined />}
                onClick={() => setShowExplainer(!showExplainer)}
                size="small"
              >
                解释
              </Button>
            </Tooltip>
          )}
          {showFavorite && item.id && (
            <Tooltip title={isFavorite ? '取消收藏' : '收藏'}>
              <Button
                type="text"
                icon={isFavorite ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                onClick={handleFavorite}
                loading={favoriteLoading}
                size="small"
              />
            </Tooltip>
          )}
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={handleCopy}
            size="small"
          >
            复制
          </Button>
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <CodeBlock code={displayCode} highlightRanges={item.highlight_ranges} />

      {needsFolding && (
        <div style={{ textAlign: 'center', marginTop: 8 }}>
          <Button
            type="link"
            size="small"
            icon={expanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '收起' : `展开全部 (${lines.length} 行)`}
          </Button>
        </div>
      )}

      {item.file_path && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            来源: {item.file_path}
          </Text>
        </div>
      )}

      {/* AI 解释面板 */}
      {showExplainer && item.id && kpId && (
        <CodeExplainer
          snippetId={item.id}
          kpId={kpId}
          kpIds={kpIds}
          kpName={kpName}
          code={item.content}
          highlightRanges={item.highlight_ranges}
          onClose={() => setShowExplainer(false)}
        />
      )}

      {/* 额外内容（如组合匹配的知识点列表） */}
      {extra}
    </Card>
  );
}
