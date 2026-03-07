/**
 * 配额指示器组件
 * 显示用户的 AI 解释配额使用情况
 */

import { useState, useEffect, useCallback } from 'react';
import { Tooltip, Progress, Space, Typography, Badge, Spin } from 'antd';
import { ThunderboltOutlined, CrownOutlined, ReloadOutlined } from '@ant-design/icons';
import { getQuota, QuotaInfo } from '../api/explain';

const { Text } = Typography;

interface QuotaIndicatorProps {
  compact?: boolean;  // 紧凑模式（仅显示图标和数字）
  showRefresh?: boolean;  // 显示刷新按钮
  onQuotaChange?: (quota: QuotaInfo) => void;  // 配额变化回调
}

export default function QuotaIndicator({
  compact = false,
  showRefresh = false,
  onQuotaChange
}: QuotaIndicatorProps) {
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuota = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getQuota();
      setQuota(data);
      onQuotaChange?.(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '获取配额失败');
    } finally {
      setLoading(false);
    }
  }, [onQuotaChange]);

  useEffect(() => {
    fetchQuota();
  }, [fetchQuota]);

  // Loading state
  if (loading && !quota) {
    return <Spin size="small" />;
  }

  // Error state
  if (error) {
    return (
      <Tooltip title={error}>
        <Text type="danger" style={{ cursor: 'pointer' }} onClick={fetchQuota}>
          <ThunderboltOutlined /> --
        </Text>
      </Tooltip>
    );
  }

  // No quota data
  if (!quota) {
    return null;
  }

  // Unlimited (admin)
  if (quota.unlimited) {
    return (
      <Tooltip title="管理员无限配额">
        <Badge count={<CrownOutlined style={{ color: '#faad14' }} />}>
          <Space size={4}>
            <ThunderboltOutlined style={{ color: '#52c41a' }} />
            {!compact && <Text type="secondary">无限</Text>}
          </Space>
        </Badge>
      </Tooltip>
    );
  }

  // Calculate usage percentage
  const usagePercent = quota.daily_limit > 0
    ? Math.round((quota.used_today / quota.daily_limit) * 100)
    : 0;

  // Determine color based on remaining
  const getStatusColor = () => {
    if (quota.remaining <= 0) return '#ff4d4f';  // 红色：已用完
    if (quota.remaining <= 10) return '#faad14';  // 黄色：即将用完
    return '#52c41a';  // 绿色：充足
  };

  // Format reset time
  const formatResetTime = () => {
    if (!quota.reset_at) return '';
    try {
      const resetDate = new Date(quota.reset_at);
      return resetDate.toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '';
    }
  };

  const tooltipContent = (
    <div>
      <div>今日已用: {quota.used_today} / {quota.daily_limit}</div>
      <div>剩余: {quota.remaining}</div>
      {quota.reset_at && <div>重置时间: {formatResetTime()}</div>}
    </div>
  );

  // Compact mode
  if (compact) {
    return (
      <Tooltip title={tooltipContent}>
        <Space size={4} style={{ cursor: 'pointer' }}>
          <ThunderboltOutlined style={{ color: getStatusColor() }} />
          <Text style={{ color: getStatusColor() }}>
            {quota.remaining}
          </Text>
        </Space>
      </Tooltip>
    );
  }

  // Full mode
  return (
    <Tooltip title={tooltipContent}>
      <Space size={8} align="center">
        <ThunderboltOutlined style={{ color: getStatusColor() }} />
        <Progress
          percent={usagePercent}
          size="small"
          showInfo={false}
          strokeColor={getStatusColor()}
          trailColor="#f0f0f0"
          style={{ width: 60 }}
        />
        <Text type={quota.remaining <= 0 ? 'danger' : 'secondary'}>
          {quota.remaining}/{quota.daily_limit}
        </Text>
        {showRefresh && (
          <ReloadOutlined
            style={{ cursor: 'pointer', color: '#1890ff' }}
            onClick={(e) => {
              e.stopPropagation();
              fetchQuota();
            }}
            spin={loading}
          />
        )}
      </Space>
    </Tooltip>
  );
}
