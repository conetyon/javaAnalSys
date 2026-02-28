/**
 * Dashboard 主页面
 * 左侧知识点树 + 右侧匹配结果区
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Layout,
  Card,
  Slider,
  InputNumber,
  Button,
  Empty,
  Spin,
  Alert,
  Space,
  Typography,
  message,
  Tooltip,
} from 'antd';
import { ReloadOutlined, SearchOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import KnowledgeTree from '../components/KnowledgeTree';
import MatchResultCard from '../components/MatchResultCard';
import { match } from '../api/match';
import { MatchResultItem } from '../types/match';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

export default function Dashboard() {
  const [searchParams] = useSearchParams();

  // 状态
  const [selectedKp, setSelectedKp] = useState<{
    id: number;
    name: string;
    name_zh: string | null;
    level: number;
  } | null>(null);
  const [results, setResults] = useState<MatchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  // 参数
  const [topK, setTopK] = useState(10);
  const [targetDifficulty, setTargetDifficulty] = useState(0.5);

  // 从 URL 参数初始化
  useEffect(() => {
    const kpIdParam = searchParams.get('kp_ids');
    const topKParam = searchParams.get('top_k');
    const diffParam = searchParams.get('target_difficulty');

    if (topKParam) setTopK(Number(topKParam));
    if (diffParam) setTargetDifficulty(Number(diffParam));

    // 如果有 kp_id 参数，需要等待树加载后自动选中（迭代 3 实现）
    if (kpIdParam) {
      const ids = kpIdParam.split(',').map(Number);
      if (ids.length === 1) {
        // 单 KP 模式，设置 selectedKp（需要知道 name，暂时跳过）
      }
    }
  }, [searchParams]);

  // 执行匹配
  const handleMatch = async (kpId: number, kpName: string, append = false) => {
    setLoading(true);
    setError(null);

    try {
      const response = await match({
        kp_id: kpId,
        top_k: append ? topK + 5 : topK,
        target_difficulty: targetDifficulty,
      });

      if (append) {
        setTopK(topK + 5);
      }

      setResults(response.data);
      setTotal(response.total);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '匹配失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 选择知识点
  const handleSelectKp = (id: number, name: string, name_zh: string | null, level: number) => {
    setSelectedKp({ id, name, name_zh, level });

    // 仅叶子节点（level=3）触发匹配
    if (level === 3) {
      handleMatch(id, name);
    } else {
      setResults([]);
      setTotal(0);
      setError(null);
    }
  };

  // 加载更多
  const handleLoadMore = () => {
    if (selectedKp && selectedKp.level === 3) {
      handleMatch(selectedKp.id, selectedKp.name, true);
    }
  };

  // 重试
  const handleRetry = () => {
    if (selectedKp && selectedKp.level === 3) {
      handleMatch(selectedKp.id, selectedKp.name);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 左侧知识点树 */}
      <Sider
        width={300}
        theme="light"
        style={{
          borderRight: '1px solid #f0f0f0',
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
        }}
      >
        <div style={{ padding: '16px 8px' }}>
          <Title level={5} style={{ margin: '0 0 16px 8px' }}>
            Java 知识点
          </Title>
          <KnowledgeTree
            onSelect={handleSelectKp}
            selectedKey={selectedKp?.id}
          />
        </div>
      </Sider>

      {/* 右侧内容区 */}
      <Layout style={{ marginLeft: 300 }}>
        <Content style={{ padding: 24 }}>
          {/* 参数配置面板 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space size="large" wrap>
              <Space>
                <Text>返回数量:</Text>
                <InputNumber
                  min={1}
                  max={50}
                  value={topK}
                  onChange={(v) => v && setTopK(v)}
                  style={{ width: 80 }}
                />
              </Space>
              <Space style={{ minWidth: 300 }}>
                <Text>
                  期望难度:
                  <Tooltip title="难度权重仅占10%，主要按代码相关性排序。0=简单，1=困难">
                    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
                  </Tooltip>
                </Text>
                <Slider
                  min={0}
                  max={1}
                  step={0.05}
                  value={targetDifficulty}
                  onChange={setTargetDifficulty}
                  tooltip={{ formatter: (v) => v !== undefined ? `${(v * 100).toFixed(0)}%` : '' }}
                  style={{ width: 150 }}
                />
                <Text type="secondary" style={{ minWidth: 60 }}>
                  {targetDifficulty <= 0.3 ? '简单' : targetDifficulty <= 0.6 ? '中等' : '困难'}
                </Text>
              </Space>
              {selectedKp?.level === 3 && (
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={() => handleMatch(selectedKp.id, selectedKp.name)}
                  loading={loading}
                >
                  重新匹配
                </Button>
              )}
            </Space>
          </Card>

          {/* 当前选中的知识点 */}
          {selectedKp && (
            <div style={{ marginBottom: 16 }}>
              <Text strong>当前选中: </Text>
              <Text>{selectedKp.name_zh || selectedKp.name}</Text>
              {selectedKp.name_zh && (
                <Text type="secondary" style={{ marginLeft: 8 }}>({selectedKp.name})</Text>
              )}
              {selectedKp.level !== 3 && (
                <Text type="secondary"> (请选择叶子节点进行匹配)</Text>
              )}
            </div>
          )}

          {/* 加载状态 */}
          {loading && (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin size="large"><span>正在匹配...</span></Spin>
            </div>
          )}

          {/* 错误提示 */}
          {error && !loading && (
            <Alert
              message="匹配失败"
              description={error}
              type="error"
              showIcon
              action={
                <Button size="small" icon={<ReloadOutlined />} onClick={handleRetry}>
                  重试
                </Button>
              }
              style={{ marginBottom: 16 }}
            />
          )}

          {/* 结果列表 */}
          {!loading && !error && results.length > 0 && (
            <>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">
                  共找到 {total} 个匹配结果，当前显示 {results.length} 个
                </Text>
              </div>

              {results.map((item, index) => (
                <MatchResultCard key={item.id || index} item={item} rank={index + 1} />
              ))}

              {/* 加载更多 */}
              {results.length < total && (
                <div style={{ textAlign: 'center', marginTop: 16 }}>
                  <Button onClick={handleLoadMore} loading={loading}>
                    加载更多
                  </Button>
                </div>
              )}
            </>
          )}

          {/* 空态 */}
          {!loading && !error && results.length === 0 && selectedKp?.level === 3 && (
            <Empty description="暂无匹配结果" />
          )}

          {/* 初始状态 */}
          {!selectedKp && (
            <Empty
              description="请从左侧选择一个知识点"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Content>
      </Layout>
    </Layout>
  );
}
