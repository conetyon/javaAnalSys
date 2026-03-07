/**
 * AI 代码解释组件
 * 左右布局：代码（左）+ AI解释（右）
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { Button, Input, Card, Typography, Space, Tag, Spin, Alert, Tooltip, Row, Col } from 'antd';
import {
  RobotOutlined,
  SendOutlined,
  StopOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  CodeOutlined
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamExplain, streamChat, TokenUsage, UserLevel } from '../api/explain';
import CodeBlock from './CodeBlock';
import { HighlightRange } from '../types/match';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

// Markdown 容器样式
const markdownStyles = `
  .markdown-body {
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    word-wrap: break-word;
  }
  .markdown-body p {
    margin: 0 0 12px 0;
  }
  .markdown-body p:last-child {
    margin-bottom: 0;
  }
  .markdown-body h1, .markdown-body h2, .markdown-body h3 {
    margin: 16px 0 8px 0;
    font-weight: 600;
  }
  .markdown-body h1 { font-size: 20px; }
  .markdown-body h2 { font-size: 18px; }
  .markdown-body h3 { font-size: 16px; }
  .markdown-body ul, .markdown-body ol {
    margin: 0 0 12px 0;
    padding-left: 24px;
  }
  .markdown-body li {
    margin: 4px 0;
  }
  .markdown-body code {
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .markdown-body pre {
    background: #282c34;
    color: #abb2bf;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 12px 0;
  }
  .markdown-body pre code {
    background: transparent;
    padding: 0;
    color: inherit;
    white-space: pre;
    word-break: normal;
  }
  .markdown-body strong {
    font-weight: 600;
  }
  .markdown-body blockquote {
    border-left: 4px solid #ddd;
    margin: 12px 0;
    padding: 8px 16px;
    color: #666;
    background: #f9f9f9;
  }
  .markdown-body hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 16px 0;
  }
`;

/**
 * 清理不完整的 Markdown（流式输出时可能截断）
 * 更加保守的策略：宁可少显示也不要显示乱码
 */
function sanitizeMarkdown(text: string): string {
  if (!text) return '';

  let result = text;

  // 1. 处理未闭合的代码块（```）
  // 找到所有代码块开始/结束标记
  const codeBlockPattern = /```/g;
  const matches = [...result.matchAll(codeBlockPattern)];

  if (matches.length % 2 !== 0) {
    // 有未闭合的代码块
    const lastOpenIndex = matches[matches.length - 1].index!;
    // 截断到最后一个未闭合代码块之前，或者保留但添加闭合标记
    // 为了更好的用户体验，截断到最后一个完整代码块
    result = result.slice(0, lastOpenIndex);
  }

  // 2. 处理未闭合的行内代码（`）
  // 需要排除代码块内的 ``` 情况
  // 简化处理：统计不在 ``` 中的单独 ` 数量
  let inCodeBlock = false;
  let singleBacktickCount = 0;
  let lastSingleBacktickIndex = -1;

  for (let i = 0; i < result.length; i++) {
    if (result.slice(i, i + 3) === '```') {
      inCodeBlock = !inCodeBlock;
      i += 2; // 跳过 ```
    } else if (result[i] === '`' && !inCodeBlock) {
      singleBacktickCount++;
      lastSingleBacktickIndex = i;
    }
  }

  // 如果有奇数个行内代码标记，添加闭合
  if (singleBacktickCount % 2 !== 0 && lastSingleBacktickIndex >= 0) {
    result = result + '`';
  }

  // 3. 移除末尾不完整的内容
  // 移除末尾不完整的列表项
  result = result.replace(/\n[-*]\s*$/, '');
  result = result.replace(/\n\d+\.\s*$/, '');

  // 移除末尾不完整的标题
  result = result.replace(/\n#{1,6}\s*$/, '');

  // 移除末尾不完整的粗体/斜体
  result = result.replace(/\*{1,2}$/, '');
  result = result.replace(/_{1,2}$/, '');

  // 4. 移除末尾的换行和空格
  result = result.trimEnd();

  return result;
}

interface CodeExplainerProps {
  snippetId: number;
  kpId: number;
  kpName?: string;
  code: string;  // 代码内容
  highlightRanges?: HighlightRange[];  // 高亮范围
  onClose?: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function CodeExplainer({
  snippetId,
  kpId,
  kpName,
  code,
  highlightRanges,
  onClose
}: CodeExplainerProps) {
  // State
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const [userLevel] = useState<UserLevel>('beginner');

  // Refs for aborting and preventing duplicate requests
  const abortRef = useRef<(() => void) | null>(null);
  const isMountedRef = useRef(false);

  // 打开时自动请求解释（兼容 React StrictMode）
  useEffect(() => {
    // StrictMode 会 double-render，用 isMountedRef 跳过第一次的 cleanup
    isMountedRef.current = true;

    // 延迟发送请求，避免 StrictMode cleanup 取消
    const timer = setTimeout(() => {
      if (isMountedRef.current && !explanation && !loading && !error) {
        requestExplanation();
      }
    }, 0);

    return () => {
      clearTimeout(timer);
      // 只在真正卸载时 abort（不是 StrictMode 的 cleanup）
      if (!isMountedRef.current) {
        abortRef.current?.();
      }
      isMountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Request initial explanation
  const requestExplanation = useCallback(() => {
    // Abort any existing request first
    abortRef.current?.();

    setLoading(true);
    setError(null);
    setExplanation('');
    setTokenUsage(null);

    const { abort } = streamExplain(
      { snippet_id: snippetId, kp_id: kpId, user_level: userLevel },
      {
        onChunk: (content) => {
          setExplanation((prev) => prev + content);
        },
        onDone: (tokens) => {
          setLoading(false);
          setTokenUsage(tokens);
        },
        onError: (err) => {
          setLoading(false);
          setError(err);
        },
      }
    );

    abortRef.current = abort;
  }, [snippetId, kpId, userLevel]);

  // Send follow-up question
  const sendQuestion = useCallback(() => {
    if (!question.trim() || loading) return;

    const userMessage: Message = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion('');
    setLoading(true);
    setError(null);

    let assistantContent = '';

    const { abort } = streamChat(
      {
        snippet_id: snippetId,
        kp_id: kpId,
        question: question.trim(),
        session_id: sessionId
      },
      {
        onChunk: (content) => {
          assistantContent += content;
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = { ...updated[lastIdx], content: assistantContent };
            } else {
              updated.push({ role: 'assistant', content: assistantContent });
            }
            return updated;
          });
        },
        onDone: (tokens) => {
          setLoading(false);
          setTokenUsage(tokens);
          // Ensure final message is added
          setMessages((prev) => {
            const lastIdx = prev.length - 1;
            if (lastIdx >= 0 && prev[lastIdx].role === 'assistant') {
              return prev;
            }
            return [...prev, { role: 'assistant', content: assistantContent }];
          });
        },
        onError: (err) => {
          setLoading(false);
          setError(err);
        },
        onSessionId: (id) => {
          setSessionId(id);
        },
      }
    );

    abortRef.current = abort;
  }, [snippetId, kpId, question, sessionId, loading]);

  // Stop generation
  const handleStop = useCallback(() => {
    abortRef.current?.();
    setLoading(false);
  }, []);

  // Retry on error
  const handleRetry = useCallback(() => {
    requestMadeRef.current = false;  // Allow retry
    requestExplanation();
  }, [requestExplanation]);

  return (
    <>
      {/* 注入 Markdown 样式 */}
      <style>{markdownStyles}</style>

      <Card
        size="small"
        title={
          <Space>
            <RobotOutlined />
            <span>AI 代码解释</span>
            {kpName && <Tag color="blue">{kpName}</Tag>}
          </Space>
        }
        extra={
          <Space>
            {tokenUsage && (
              <Tooltip title={`Prompt: ${tokenUsage.prompt_tokens}, Completion: ${tokenUsage.completion_tokens}`}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {tokenUsage.prompt_tokens + tokenUsage.completion_tokens} tokens
                </Text>
              </Tooltip>
            )}
            {onClose && (
              <Button type="text" size="small" onClick={onClose}>
                关闭
              </Button>
            )}
          </Space>
        }
        style={{ marginTop: 12 }}
      >
        {/* 左右布局：代码 + 解释 */}
        <Row gutter={16}>
          {/* 左侧：代码 */}
          <Col xs={24} md={12}>
            <div style={{ marginBottom: 8 }}>
              <Space>
                <CodeOutlined />
                <Text strong>代码片段</Text>
              </Space>
            </div>
            <div style={{
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              maxHeight: 400,
              overflow: 'auto',
            }}>
              <CodeBlock code={code} highlightRanges={highlightRanges} />
            </div>
          </Col>

          {/* 右侧：AI 解释 */}
          <Col xs={24} md={12}>
            <div style={{ marginBottom: 8 }}>
              <Space>
                <RobotOutlined />
                <Text strong>AI 解释</Text>
              </Space>
            </div>

            {/* Error display */}
            {error && (
              <Alert
                type="error"
                message={error}
                showIcon
                style={{ marginBottom: 12 }}
                action={
                  <Button size="small" onClick={handleRetry} icon={<ReloadOutlined />}>
                    重试
                  </Button>
                }
              />
            )}

            {/* Loading state */}
            {loading && !explanation && (
              <div style={{
                textAlign: 'center',
                padding: '40px 0',
                background: '#f6f8fa',
                borderRadius: 6,
              }}>
                <Spin tip="正在生成解释..." />
              </div>
            )}

            {/* Explanation content */}
            {(explanation || (!loading && !error)) && (
              <div
                className="markdown-body"
                style={{
                  background: '#f6f8fa',
                  padding: '12px 16px',
                  borderRadius: 6,
                  maxHeight: 300,
                  overflow: 'auto',
                  minHeight: 100,
                }}
              >
                {explanation ? (
                  <>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {sanitizeMarkdown(explanation)}
                    </ReactMarkdown>
                    {loading && <Spin size="small" style={{ marginLeft: 8 }} />}
                  </>
                ) : (
                  <Paragraph type="secondary" style={{ margin: 0 }}>
                    正在加载 AI 解释...
                  </Paragraph>
                )}
              </div>
            )}

            {/* Chat messages */}
            {messages.length > 0 && (
              <div style={{ marginTop: 12, maxHeight: 200, overflow: 'auto' }}>
                {messages.map((msg, idx) => (
                  <div
                    key={idx}
                    style={{
                      marginBottom: 8,
                      textAlign: msg.role === 'user' ? 'right' : 'left'
                    }}
                  >
                    <div
                      style={{
                        display: 'inline-block',
                        maxWidth: '90%',
                        padding: '8px 12px',
                        borderRadius: 8,
                        background: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
                        color: msg.role === 'user' ? '#fff' : 'inherit',
                        fontSize: 13,
                      }}
                    >
                      {msg.role === 'assistant' ? (
                        <div className="markdown-body">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {sanitizeMarkdown(msg.content)}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Question input */}
            {explanation && (
              <div style={{ marginTop: 12 }}>
                <Space.Compact style={{ width: '100%' }}>
                  <TextArea
                    placeholder="输入问题，例如：为什么要用这种写法？"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onPressEnter={(e) => {
                      if (!e.shiftKey) {
                        e.preventDefault();
                        sendQuestion();
                      }
                    }}
                    autoSize={{ minRows: 1, maxRows: 2 }}
                    disabled={loading}
                  />
                  {loading ? (
                    <Button
                      danger
                      icon={<StopOutlined />}
                      onClick={handleStop}
                    >
                      停止
                    </Button>
                  ) : (
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      onClick={sendQuestion}
                      disabled={!question.trim()}
                    >
                      发送
                    </Button>
                  )}
                </Space.Compact>
              </div>
            )}
          </Col>
        </Row>

        {/* Disclaimer */}
        <div style={{ marginTop: 12, textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            <InfoCircleOutlined style={{ marginRight: 4 }} />
            AI 生成内容仅供参考，请自行验证代码正确性
          </Text>
        </div>
      </Card>
    </>
  );
}
