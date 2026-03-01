/**
 * History Page
 * Shows user's match history with pagination
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Tag,
  Typography,
  Button,
  Space,
  Empty,
  message,
} from 'antd';
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { getHistory } from '../api/user';
import type { HistoryItem } from '../types/user';

const { Title, Text } = Typography;

export default function HistoryPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getHistory(page, pageSize);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      message.error(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const columns: ColumnsType<HistoryItem> = [
    {
      title: 'Knowledge Points',
      dataIndex: 'kp_names',
      key: 'kp_names',
      render: (names: string[]) => (
        <Space wrap>
          {names.map((name, idx) => (
            <Tag key={idx} color="blue">{name}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'Mode',
      dataIndex: 'mode',
      key: 'mode',
      width: 100,
      render: (mode: string) => (
        <Tag color={mode === 'matrix' ? 'purple' : 'green'}>
          {mode === 'matrix' ? 'Matrix' : 'List'}
        </Tag>
      ),
    },
    {
      title: 'Parameters',
      dataIndex: 'params',
      key: 'params',
      width: 200,
      render: (params: Record<string, unknown>) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {Object.entries(params)
            .filter(([k]) => !['kp_id', 'kp_ids'].includes(k))
            .map(([k, v]) => `${k}: ${v}`)
            .join(', ') || '-'}
        </Text>
      ),
    },
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Title level={4} style={{ margin: 0 }}>Match History</Title>
        </Space>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">Total {total} records</Text>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadHistory}
            loading={loading}
          >
            Refresh
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          locale={{
            emptyText: <Empty description="No history records yet" />,
          }}
        />
      </Card>
    </div>
  );
}
