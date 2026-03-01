/**
 * Dashboard 主页面
 * 左侧知识点树 + 右侧匹配结果区
 * 支持列表模式和矩阵模式切换
 * 支持单选和多选（组合匹配）
 */

import { useState, useEffect, useCallback } from 'react';
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
  Segmented,
  Tag,
  Select,
} from 'antd';
import {
  ReloadOutlined,
  SearchOutlined,
  QuestionCircleOutlined,
  UnorderedListOutlined,
  AppstoreOutlined,
  UserOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import KnowledgeTree from '../components/KnowledgeTree';
import MatchResultCard from '../components/MatchResultCard';
import MatrixView from '../components/MatrixView';
import { match, matchMatrix, matchComposite, matchCompositeMatrix } from '../api/match';
import { getFavoriteIds, addFavorite, removeFavorite } from '../api/user';
import { useAuth } from '../contexts/AuthContext';
import type {
  MatchResultItem,
  MatrixResultItem,
  CompositeMatchResultItem,
  MatchMode,
  SelectionMode,
} from '../types/match';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

type SelectedKp = { id: number; name: string; name_zh: string | null };

// sessionStorage key for persisting dashboard state
const DASHBOARD_STATE_KEY = 'dashboard_state';

// Type for persisted state
interface PersistedState {
  selectionMode: SelectionMode;
  selectedKp: { id: number; name: string; name_zh: string | null; level: number } | null;
  checkedKps: SelectedKp[];
  matchMode: MatchMode;
  topK: number;
  targetDifficulty: number;
  perLevel: number;
  scoreAggregation: 'average' | 'min' | 'sum';
}

// Load persisted state from sessionStorage
function loadPersistedState(): Partial<PersistedState> {
  try {
    const saved = sessionStorage.getItem(DASHBOARD_STATE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch {
    // Ignore parse errors
  }
  return {};
}

// Save state to sessionStorage
function savePersistedState(state: PersistedState) {
  try {
    sessionStorage.setItem(DASHBOARD_STATE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage errors
  }
}

export default function Dashboard() {
  const [searchParams] = useSearchParams();
  const { isAuthenticated } = useAuth();

  // Load persisted state on mount
  const persistedState = loadPersistedState();

  // 选择模式状态
  const [selectionMode, setSelectionMode] = useState<SelectionMode>(
    persistedState.selectionMode || 'single'
  );

  // 收藏状态
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());

  // 单选状态
  const [selectedKp, setSelectedKp] = useState<{
    id: number;
    name: string;
    name_zh: string | null;
    level: number;
  } | null>(persistedState.selectedKp || null);

  // 多选状态
  const [checkedKps, setCheckedKps] = useState<SelectedKp[]>(
    persistedState.checkedKps || []
  );

  // 模式状态
  const [matchMode, setMatchMode] = useState<MatchMode>(
    persistedState.matchMode || 'list'
  );

  // 列表模式结果
  const [listResults, setListResults] = useState<MatchResultItem[]>([]);
  const [compositeListResults, setCompositeListResults] = useState<CompositeMatchResultItem[]>([]);
  const [listTotal, setListTotal] = useState(0);

  // 矩阵模式结果
  const [matrixData, setMatrixData] = useState<{
    matrix: Record<string, MatrixResultItem[]> | Record<string, CompositeMatchResultItem[]>;
    levels: string[];
    total: number;
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 参数（从持久化状态恢复）
  const [topK, setTopK] = useState(persistedState.topK || 10);
  const [targetDifficulty, setTargetDifficulty] = useState(persistedState.targetDifficulty ?? 0.5);
  const [perLevel, setPerLevel] = useState(persistedState.perLevel || 5);
  const [scoreAggregation, setScoreAggregation] = useState<'average' | 'min' | 'sum'>(
    persistedState.scoreAggregation || 'average'
  );

  // 保存状态到 sessionStorage
  useEffect(() => {
    savePersistedState({
      selectionMode,
      selectedKp,
      checkedKps,
      matchMode,
      topK,
      targetDifficulty,
      perLevel,
      scoreAggregation,
    });
  }, [selectionMode, selectedKp, checkedKps, matchMode, topK, targetDifficulty, perLevel, scoreAggregation]);

  // 从 URL 参数初始化（优先级高于持久化状态）
  useEffect(() => {
    const modeParam = searchParams.get('mode');
    const topKParam = searchParams.get('top_k');
    const diffParam = searchParams.get('target_difficulty');

    if (modeParam === 'matrix') setMatchMode('matrix');
    if (topKParam) setTopK(Number(topKParam));
    if (diffParam) setTargetDifficulty(Number(diffParam));
  }, [searchParams]);

  // 清空结果
  const clearResults = useCallback(() => {
    setListResults([]);
    setCompositeListResults([]);
    setListTotal(0);
    setMatrixData(null);
    setError(null);
  }, []);

  // 加载收藏列表（登录后）
  useEffect(() => {
    if (isAuthenticated) {
      getFavoriteIds()
        .then((data) => setFavoriteIds(new Set(data.snippet_ids)))
        .catch(() => setFavoriteIds(new Set()));
    } else {
      setFavoriteIds(new Set());
    }
  }, [isAuthenticated]);

  // 恢复匹配结果（从历史/收藏页面返回时）
  const [initialized, setInitialized] = useState(false);
  useEffect(() => {
    if (initialized) return;
    setInitialized(true);

    // 如果有保存的选中状态，自动触发匹配
    if (selectionMode === 'single' && selectedKp?.level === 3) {
      if (matchMode === 'list') {
        handleSingleListMatch(selectedKp.id);
      } else {
        handleSingleMatrixMatch(selectedKp.id);
      }
    } else if (selectionMode === 'multiple' && checkedKps.length > 0) {
      const kpIds = checkedKps.map((kp) => kp.id);
      if (matchMode === 'list') {
        handleCompositeListMatch(kpIds);
      } else {
        handleCompositeMatrixMatch(kpIds);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialized]);

  // 收藏切换
  const handleFavoriteToggle = async (snippetId: number, shouldFavorite: boolean) => {
    try {
      if (shouldFavorite) {
        await addFavorite(snippetId);
        setFavoriteIds((prev) => new Set([...prev, snippetId]));
        message.success('已添加收藏');
      } else {
        await removeFavorite(snippetId);
        setFavoriteIds((prev) => {
          const next = new Set(prev);
          next.delete(snippetId);
          return next;
        });
        message.success('已取消收藏');
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : '操作失败');
    }
  };

  // 执行单KP列表匹配
  const handleSingleListMatch = async (kpId: number, append = false) => {
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

      setListResults(response.data);
      setCompositeListResults([]);
      setListTotal(response.total);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '匹配失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 执行单KP矩阵匹配
  const handleSingleMatrixMatch = async (kpId: number) => {
    setLoading(true);
    setError(null);

    try {
      const response = await matchMatrix({
        kp_id: kpId,
        per_level: perLevel,
      });

      setMatrixData({
        matrix: response.matrix,
        levels: response.levels,
        total: response.total,
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '匹配失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 执行组合列表匹配
  const handleCompositeListMatch = async (kpIds: number[]) => {
    setLoading(true);
    setError(null);

    try {
      const response = await matchComposite({
        kp_ids: kpIds,
        top_k: topK,
        target_difficulty: targetDifficulty,
        score_aggregation: scoreAggregation,
      });

      setCompositeListResults(response.data);
      setListResults([]);
      setListTotal(response.total);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '匹配失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 执行组合矩阵匹配
  const handleCompositeMatrixMatch = async (kpIds: number[]) => {
    setLoading(true);
    setError(null);

    try {
      const response = await matchCompositeMatrix({
        kp_ids: kpIds,
        per_level: perLevel,
        score_aggregation: scoreAggregation,
      });

      setMatrixData({
        matrix: response.matrix,
        levels: response.levels,
        total: response.total,
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '匹配失败';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // 执行匹配（根据当前模式）
  const handleMatch = async (append = false) => {
    if (selectionMode === 'single') {
      if (!selectedKp || selectedKp.level !== 3) return;
      if (matchMode === 'list') {
        await handleSingleListMatch(selectedKp.id, append);
      } else {
        await handleSingleMatrixMatch(selectedKp.id);
      }
    } else {
      if (checkedKps.length === 0) return;
      const kpIds = checkedKps.map((kp) => kp.id);
      if (matchMode === 'list') {
        await handleCompositeListMatch(kpIds);
      } else {
        await handleCompositeMatrixMatch(kpIds);
      }
    }
  };

  // 选择知识点（单选模式）
  const handleSelectKp = (id: number, name: string, name_zh: string | null, level: number) => {
    if (selectionMode !== 'single') return;

    setSelectedKp({ id, name, name_zh, level });

    // 仅叶子节点（level=3）触发匹配
    if (level === 3) {
      if (matchMode === 'list') {
        handleSingleListMatch(id);
      } else {
        handleSingleMatrixMatch(id);
      }
    } else {
      clearResults();
    }
  };

  // 勾选变化（多选模式）
  const handleCheckedChange = (kps: SelectedKp[]) => {
    setCheckedKps(kps);
  };

  // 移除已选知识点
  const handleRemoveChecked = (id: number) => {
    setCheckedKps(checkedKps.filter((kp) => kp.id !== id));
  };

  // 模式切换
  const handleModeChange = (mode: MatchMode) => {
    setMatchMode(mode);
    clearResults();

    // 如果有选中的知识点，自动触发匹配
    if (selectionMode === 'single' && selectedKp?.level === 3) {
      setTimeout(() => {
        if (mode === 'list') {
          handleSingleListMatch(selectedKp.id);
        } else {
          handleSingleMatrixMatch(selectedKp.id);
        }
      }, 0);
    } else if (selectionMode === 'multiple' && checkedKps.length > 0) {
      setTimeout(() => {
        const kpIds = checkedKps.map((kp) => kp.id);
        if (mode === 'list') {
          handleCompositeListMatch(kpIds);
        } else {
          handleCompositeMatrixMatch(kpIds);
        }
      }, 0);
    }
  };

  // 选择模式切换
  const handleSelectionModeChange = (mode: SelectionMode) => {
    setSelectionMode(mode);
    clearResults();
    // 切换时清空选择
    if (mode === 'single') {
      setCheckedKps([]);
    } else {
      setSelectedKp(null);
    }
  };

  // 加载更多（仅单选列表模式）
  const handleLoadMore = () => {
    if (selectionMode === 'single' && selectedKp?.level === 3 && matchMode === 'list') {
      handleSingleListMatch(selectedKp.id, true);
    }
  };

  // 重试
  const handleRetry = () => {
    handleMatch();
  };

  // 是否有结果
  const hasResults = listResults.length > 0 || compositeListResults.length > 0 || (matrixData && matrixData.total > 0);
  const isReady = selectionMode === 'single'
    ? selectedKp?.level === 3
    : checkedKps.length > 0;

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

          {/* 选择模式切换 */}
          <div style={{ marginBottom: 12, padding: '0 8px' }}>
            <Segmented
              block
              value={selectionMode}
              onChange={(value) => handleSelectionModeChange(value as SelectionMode)}
              options={[
                { value: 'single', icon: <UserOutlined />, label: '单选' },
                { value: 'multiple', icon: <TeamOutlined />, label: '多选' },
              ]}
            />
          </div>

          <KnowledgeTree
            onSelect={handleSelectKp}
            selectedKey={selectionMode === 'single' ? selectedKp?.id : undefined}
            checkable={selectionMode === 'multiple'}
            checkedKeys={checkedKps.map((kp) => kp.id)}
            onCheckedChange={handleCheckedChange}
          />
        </div>
      </Sider>

      {/* 右侧内容区 */}
      <Layout style={{ marginLeft: 300 }}>
        <Content style={{ padding: 24 }}>
          {/* 参数配置面板 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space size="large" wrap>
              {/* 显示模式切换 */}
              <Segmented
                value={matchMode}
                onChange={(value) => handleModeChange(value as MatchMode)}
                options={[
                  { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
                  { value: 'matrix', icon: <AppstoreOutlined />, label: '矩阵' },
                ]}
              />

              {/* 列表模式参数 */}
              {matchMode === 'list' && (
                <>
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
                </>
              )}

              {/* 矩阵模式参数 */}
              {matchMode === 'matrix' && (
                <Space>
                  <Text>每级数量:</Text>
                  <InputNumber
                    min={1}
                    max={20}
                    value={perLevel}
                    onChange={(v) => v && setPerLevel(v)}
                    style={{ width: 80 }}
                  />
                  <Tooltip title="每个难度等级返回的结果数量">
                    <QuestionCircleOutlined style={{ color: '#999' }} />
                  </Tooltip>
                </Space>
              )}

              {/* 多选模式：聚合策略 */}
              {selectionMode === 'multiple' && (
                <Space>
                  <Text>聚合策略:</Text>
                  <Select
                    value={scoreAggregation}
                    onChange={setScoreAggregation}
                    style={{ width: 100 }}
                    options={[
                      { value: 'average', label: '平均' },
                      { value: 'min', label: '最小' },
                      { value: 'sum', label: '求和' },
                    ]}
                  />
                  <Tooltip title="average=均衡匹配, min=严格全部满足, sum=覆盖面优先">
                    <QuestionCircleOutlined style={{ color: '#999' }} />
                  </Tooltip>
                </Space>
              )}

              {isReady && (
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={() => handleMatch()}
                  loading={loading}
                >
                  {selectionMode === 'multiple' ? '组合匹配' : '重新匹配'}
                </Button>
              )}
            </Space>
          </Card>

          {/* 当前选中的知识点 */}
          {selectionMode === 'single' && selectedKp && (
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

          {/* 多选已选择的知识点 */}
          {selectionMode === 'multiple' && checkedKps.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Text strong>已选择 {checkedKps.length} 个知识点: </Text>
              <div style={{ marginTop: 8 }}>
                {checkedKps.map((kp) => (
                  <Tag
                    key={kp.id}
                    closable
                    onClose={() => handleRemoveChecked(kp.id)}
                    style={{ marginBottom: 4 }}
                  >
                    {kp.name_zh || kp.name}
                  </Tag>
                ))}
              </div>
            </div>
          )}

          {selectionMode === 'multiple' && checkedKps.length === 0 && (
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">请在左侧勾选知识点（最多5个）进行组合匹配</Text>
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

          {/* 单选列表模式结果 */}
          {!loading && !error && matchMode === 'list' && selectionMode === 'single' && listResults.length > 0 && (
            <>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">
                  共找到 {listTotal} 个匹配结果，当前显示 {listResults.length} 个
                </Text>
              </div>

              {listResults.map((item, index) => (
                <MatchResultCard
                  key={item.id || index}
                  item={item}
                  rank={index + 1}
                  showFavorite={isAuthenticated}
                  isFavorite={item.id ? favoriteIds.has(item.id) : false}
                  onFavoriteToggle={handleFavoriteToggle}
                />
              ))}

              {/* 加载更多 */}
              {listResults.length < listTotal && (
                <div style={{ textAlign: 'center', marginTop: 16 }}>
                  <Button onClick={handleLoadMore} loading={loading}>
                    加载更多
                  </Button>
                </div>
              )}
            </>
          )}

          {/* 多选列表模式结果 */}
          {!loading && !error && matchMode === 'list' && selectionMode === 'multiple' && compositeListResults.length > 0 && (
            <>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">
                  共找到 {listTotal} 个匹配结果（同时涉及所选 {checkedKps.length} 个知识点）
                </Text>
              </div>

              {compositeListResults.map((item, index) => (
                <MatchResultCard
                  key={item.id || index}
                  item={{
                    id: item.id,
                    content: item.content,
                    score: item.composite_score,
                    ast_ratio: 0,
                    ast_coverage: 0,
                    keyword_score: 0,
                    keyword_hit: 0,
                    keyword_total: item.kp_count,
                    difficulty: item.difficulty || 0,
                    file_path: item.file_path,
                  }}
                  rank={index + 1}
                  showFavorite={isAuthenticated}
                  isFavorite={item.id ? favoriteIds.has(item.id) : false}
                  onFavoriteToggle={handleFavoriteToggle}
                  isComposite={true}
                  extra={
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        涉及知识点: {item.kp_details.map((d) => d.kp_name).join(', ')}
                      </Text>
                    </div>
                  }
                />
              ))}
            </>
          )}

          {/* 矩阵模式结果 */}
          {!loading && !error && matchMode === 'matrix' && matrixData && (
            <MatrixView
              matrix={matrixData.matrix}
              levels={matrixData.levels}
              total={matrixData.total}
              isComposite={selectionMode === 'multiple'}
              showFavorite={isAuthenticated}
              favoriteIds={favoriteIds}
              onFavoriteToggle={handleFavoriteToggle}
            />
          )}

          {/* 空态 */}
          {!loading && !error && isReady && !hasResults && (
            <Empty description="暂无匹配结果" />
          )}

          {/* 初始状态 */}
          {!selectedKp && selectionMode === 'single' && (
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
