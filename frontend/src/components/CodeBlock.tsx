/**
 * 代码高亮组件
 * 使用 react-syntax-highlighter 展示 Java 代码
 */

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language?: string;
  maxHeight?: number;
}

export default function CodeBlock({
  code,
  language = 'java',
  maxHeight
}: CodeBlockProps) {
  return (
    <div style={{
      maxHeight: maxHeight ? `${maxHeight}px` : undefined,
      overflow: maxHeight ? 'auto' : undefined,
    }}>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        showLineNumbers
        wrapLines
        customStyle={{
          margin: 0,
          borderRadius: 6,
          fontSize: 13,
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
