/**
 * Favorites Page
 * Shows user's favorite code snippets with pagination
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Typography,
  Button,
  Space,
  Empty,
  message,
  Pagination,
  Popconfirm,
} from 'antd';
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { getFavorites, removeFavorite } from '../api/user';
import CodeBlock from '../components/CodeBlock';
import type { FavoriteItem } from '../types/user';

const { Title, Text } = Typography;

export default function FavoritesPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<FavoriteItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const loadFavorites = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFavorites(page, pageSize);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      message.error(err instanceof Error ? err.message : 'Failed to load favorites');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  const handleRemove = async (snippetId: number) => {
    try {
      await removeFavorite(snippetId);
      message.success('Removed from favorites');
      // Reload current page
      loadFavorites();
    } catch (err) {
      message.error(err instanceof Error ? err.message : 'Failed to remove');
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Title level={4} style={{ margin: 0 }}>My Favorites</Title>
        </Space>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">Total {total} favorites</Text>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadFavorites}
            loading={loading}
          >
            Refresh
          </Button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>Loading...</div>
        ) : items.length === 0 ? (
          <Empty description="No favorites yet" />
        ) : (
          <>
            {items.map((item) => (
              <Card
                key={item.id}
                size="small"
                style={{ marginBottom: 16 }}
                extra={
                  <Popconfirm
                    title="Remove from favorites?"
                    onConfirm={() => handleRemove(item.snippet_id)}
                    okText="Yes"
                    cancelText="No"
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      size="small"
                    >
                      Remove
                    </Button>
                  </Popconfirm>
                }
              >
                <CodeBlock code={item.content} />
                {item.file_path && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Source: {item.file_path}
                    </Text>
                  </div>
                )}
                <div style={{ marginTop: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Added: {new Date(item.created_at).toLocaleString('zh-CN')}
                  </Text>
                </div>
              </Card>
            ))}

            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                showSizeChanger
                pageSizeOptions={['10', '20', '50']}
                onChange={(p, ps) => {
                  setPage(p);
                  setPageSize(ps);
                }}
              />
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
