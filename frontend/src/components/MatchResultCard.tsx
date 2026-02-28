/**
 * 匹配结果卡片组件
 * 展示代码、得分、文件路径，支持复制和折叠
 */

import { useState } from 'react';
import { Card, Typography, Space, Button, Tag, message, Tooltip } from 'antd';
import { CopyOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import CodeBlock from './CodeBlock';
import { MatchResultItem } from '../types/match';

const { Text } = Typography;

interface MatchResultCardProps {
  item: MatchResultItem;
  rank: number;
}

const MAX_LINES_COLLAPSED = 20;

export default function MatchResultCard({ item, rank }: MatchResultCardProps) {
  const [expanded, setExpanded] = useState(false);

  const lines = item.content.split('\n');
  const needsFolding = lines.length > MAX_LINES_COLLAPSED;
  const displayCode = expanded ? item.content : lines.slice(0, MAX_LINES_COLLAPSED).join('\n');

  // 复制代码
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(item.content);
      message.success('代码已复制到剪贴板');
    } catch {
      message.error('复制失败，请手动选择复制');
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
            得分: {(item.score * 100).toFixed(1)}%
          </Tag>
          <Tooltip title="AST 匹配率">
            <Tag>AST: {(item.ast_ratio * 100).toFixed(0)}%</Tag>
          </Tooltip>
          <Tooltip title={`关键词命中: ${item.keyword_hit}/${item.keyword_total}`}>
            <Tag>KW: {(item.keyword_score * 100).toFixed(0)}%</Tag>
          </Tooltip>
          <Tooltip title={`代码复杂度: ${(item.difficulty * 100).toFixed(0)}%`}>
            <Tag color={diffLabel.color}>{diffLabel.text}</Tag>
          </Tooltip>
        </Space>
      }
      extra={
        <Button
          type="text"
          icon={<CopyOutlined />}
          onClick={handleCopy}
          size="small"
        >
          复制
        </Button>
      }
      style={{ marginBottom: 16 }}
    >
      <CodeBlock code={displayCode} />

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
    </Card>
  );
}
