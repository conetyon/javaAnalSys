/**
 * 代码高亮组件
 * 使用 react-syntax-highlighter 展示 Java 代码
 * 支持关键行高亮标注，右侧固定区域显示知识点标签
 */

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { CSSProperties, useMemo, useRef, useEffect, useState } from 'react';
import { Tooltip, Tag } from 'antd';
import type { HighlightRange } from '../types/match';

interface CodeBlockProps {
  code: string;
  language?: string;
  maxHeight?: number;
  highlightLines?: number[];  // 简单模式：只传行号
  highlightRanges?: HighlightRange[];  // 完整模式：包含 label
}

export default function CodeBlock({
  code,
  language = 'java',
  maxHeight,
  highlightLines = [],
  highlightRanges = []
}: CodeBlockProps) {
  const codeContainerRef = useRef<HTMLDivElement>(null);
  const tagContainerRef = useRef<HTMLDivElement>(null);
  const [lineHeight, setLineHeight] = useState(21);

  // 计算当前代码的行数（用于过滤超出范围的高亮）
  const totalVisibleLines = useMemo(() => code.split('\n').length, [code]);

  // 构建行号到标签的映射（只包含可见行）
  const { highlightSet, lineLabels } = useMemo(() => {
    const set = new Set<number>();
    const labels = new Map<number, string[]>();

    // 从 highlightRanges 提取（只保留可见行范围内的）
    for (const range of highlightRanges) {
      // 跳过完全超出可见范围的
      if (range.start_line > totalVisibleLines) continue;

      for (let line = range.start_line; line <= Math.min(range.end_line, totalVisibleLines); line++) {
        set.add(line);
        if (!labels.has(line)) {
          labels.set(line, []);
        }
        // 只添加到起始行
        if (line === range.start_line && range.label) {
          labels.get(line)!.push(range.label);
        }
      }
    }

    // 兼容简单模式（只保留可见行范围内的）
    for (const line of highlightLines) {
      if (line <= totalVisibleLines) {
        set.add(line);
      }
    }

    return { highlightSet: set, lineLabels: labels };
  }, [highlightLines, highlightRanges, totalVisibleLines]);

  // 计算行高
  useEffect(() => {
    if (codeContainerRef.current) {
      const codeElement = codeContainerRef.current.querySelector('code');
      if (codeElement) {
        const style = window.getComputedStyle(codeElement);
        const lh = parseFloat(style.lineHeight);
        if (!isNaN(lh)) {
          setLineHeight(lh);
        }
      }
    }
  }, [code]);

  // 同步滚动：代码区滚动时，标签区也跟着滚动
  useEffect(() => {
    const codeContainer = codeContainerRef.current;
    const tagContainer = tagContainerRef.current;
    if (!codeContainer || !tagContainer) return;

    const handleScroll = () => {
      tagContainer.scrollTop = codeContainer.scrollTop;
    };

    codeContainer.addEventListener('scroll', handleScroll);
    return () => codeContainer.removeEventListener('scroll', handleScroll);
  }, []);

  // 行属性函数：为高亮行添加背景色
  const lineProps = (lineNumber: number): { style: CSSProperties } => {
    if (highlightSet.has(lineNumber)) {
      return {
        style: {
          backgroundColor: 'rgba(255, 193, 7, 0.15)',
          borderLeft: '3px solid #ffc107',
          marginLeft: '-3px',
          display: 'block',
        }
      };
    }
    return { style: {} };
  };

  // 获取所有标签（按行排序，合并同一行的标签）
  const sortedLabels = useMemo(() => {
    const result: Array<{ line: number; labels: string[] }> = [];
    const lineMap = new Map<number, string[]>();

    // 按行合并标签
    for (const [line, labels] of lineLabels.entries()) {
      if (!lineMap.has(line)) {
        lineMap.set(line, []);
      }
      lineMap.get(line)!.push(...labels);
    }

    // 转换为数组并排序
    for (const [line, labels] of lineMap.entries()) {
      result.push({ line, labels });
    }

    return result.sort((a, b) => a.line - b.line);
  }, [lineLabels]);

  const hasLabels = sortedLabels.length > 0;
  const tagColumnWidth = hasLabels ? 200 : 0;

  return (
    <div style={{
      display: 'flex',
      borderRadius: 6,
      overflow: 'hidden',
      background: '#282c34',
    }}>
      {/* 代码区（左侧） */}
      <div
        ref={codeContainerRef}
        style={{
          flex: 1,
          minWidth: 0,
          maxHeight: maxHeight ? `${maxHeight}px` : undefined,
          overflow: 'auto',
        }}
      >
        <SyntaxHighlighter
          language={language}
          style={oneDark}
          showLineNumbers
          wrapLines
          lineProps={lineProps}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            fontSize: 13,
            background: 'transparent',
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>

      {/* 标签区（右侧） */}
      {hasLabels && (
        <div
          ref={tagContainerRef}
          style={{
            width: tagColumnWidth,
            flexShrink: 0,
            maxHeight: maxHeight ? `${maxHeight}px` : undefined,
            overflow: 'hidden',  // 隐藏滚动条，通过同步滚动实现
            background: '#282c34',
            borderLeft: '1px solid #3e4451',
            paddingTop: 12,  // 与代码区顶部对齐
            paddingBottom: 12,
          }}
        >
          {/* 标签容器 - 使用相对定位 */}
          <div style={{
            position: 'relative',
            height: totalVisibleLines * lineHeight,
          }}>
            {sortedLabels.map(({ line, labels }, idx) => {
              // 合并多个标签为一个显示字符串
              const combinedLabel = labels.join(' | ');
              const tooltipContent = labels.length > 1
                ? `第 ${line} 行:\n${labels.map(l => `• ${l}`).join('\n')}`
                : `第 ${line} 行: ${labels[0]}`;

              return (
                <div
                  key={idx}
                  style={{
                    position: 'absolute',
                    top: (line - 1) * lineHeight,
                    left: 8,
                    right: 8,
                  }}
                >
                  <Tooltip
                    title={<span style={{ whiteSpace: 'pre-line' }}>{tooltipContent}</span>}
                    placement="left"
                  >
                    <Tag
                      color="gold"
                      style={{
                        display: 'inline-block',
                        fontSize: 11,
                        lineHeight: '18px',
                        padding: '1px 6px',
                        margin: 0,
                        cursor: 'default',
                        maxWidth: tagColumnWidth - 20,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {combinedLabel}
                    </Tag>
                  </Tooltip>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
