/**
 * SSE (Server-Sent Events) 处理工具
 * 用于处理 AI 解释功能的流式响应
 */

import { getToken } from '../api/client';

export interface SSECallbacks<T = unknown> {
  onChunk: (content: string) => void;
  onDone: (data: T) => void;
  onError: (error: string) => void;
  onSessionId?: (sessionId: string) => void;
}

export interface SSEOptions {
  signal?: AbortSignal;
  timeout?: number;  // 超时时间（毫秒），默认 120000
}

/**
 * 获取 SSE 请求的完整 URL
 * 开发环境中直接访问后端，避免 Vite 代理缓冲问题
 */
function getSSEUrl(path: string): string {
  // 开发环境：直接访问后端 (http://localhost:5000)
  // 生产环境：使用相对路径（由反向代理处理）
  if (import.meta.env.DEV) {
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
    return `${backendUrl}${path}`;
  }
  return path;
}

/**
 * 通用 SSE POST 请求处理器
 * 使用 fetch + ReadableStream 处理流式响应
 */
export async function fetchSSE<T = unknown>(
  url: string,
  body: Record<string, unknown>,
  callbacks: SSECallbacks<T>,
  options: SSEOptions = {}
): Promise<void> {
  const { onChunk, onDone, onError, onSessionId } = callbacks;
  const { signal: externalSignal, timeout = 120000 } = options;

  // 创建超时控制器
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => {
    timeoutController.abort();
  }, timeout);

  // 合并外部 signal 和超时 signal
  const combinedSignal = externalSignal
    ? createCombinedSignal(externalSignal, timeoutController.signal)
    : timeoutController.signal;

  try {
    const token = getToken();
    // 使用 getSSEUrl 获取完整 URL（开发环境绕过 Vite 代理）
    const fullUrl = getSSEUrl(url);
    console.log('[SSE] Requesting:', fullUrl);

    const response = await fetch(fullUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',  // 明确告知服务器需要 SSE 响应
        'Cache-Control': 'no-cache',    // 禁用缓存
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal: combinedSignal,
    });

    // 处理 HTTP 错误
    if (!response.ok) {
      clearTimeout(timeoutId);
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        const err = await response.json();
        onError(err.message || err.error || `HTTP ${response.status}`);
      } else {
        onError(`HTTP ${response.status}: ${response.statusText}`);
      }
      return;
    }

    // 检查是否为 SSE 响应
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('text/event-stream')) {
      clearTimeout(timeoutId);
      onError('Unexpected response type');
      return;
    }

    // 读取流式响应
    const reader = response.body?.getReader();
    if (!reader) {
      clearTimeout(timeoutId);
      onError('No response body');
      return;
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let hasReceivedData = false;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // 收到数据后重置超时
        hasReceivedData = true;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE 格式: "data: {...}\n\n"
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';  // 保留未完成的部分

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);  // 移除 "data: " 前缀
            try {
              const data = JSON.parse(dataStr);

              switch (data.type) {
                case 'connected':
                  // 连接确认，重置超时
                  console.log('[SSE] Connected to server');
                  break;
                case 'content':
                  console.log('[SSE] Content chunk:', data.content);  // 调试：查看原始数据
                  onChunk(data.content);
                  break;
                case 'done':
                  onDone(data.tokens as T);
                  break;
                case 'error':
                  onError(data.error);
                  break;
                case 'session_id':
                  onSessionId?.(data.session_id);
                  break;
              }
            } catch {
              // 忽略解析错误，继续处理
              console.warn('[SSE] Failed to parse:', dataStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
      clearTimeout(timeoutId);
    }

  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        // 检查是否是超时导致的取消
        if (timeoutController.signal.aborted) {
          onError('请求超时，AI 服务响应缓慢，请稍后重试');
        }
        // 用户主动取消，不报错
        return;
      }
      onError(error.message);
    } else {
      onError('Unknown error');
    }
  }
}

/**
 * 合并多个 AbortSignal
 */
function createCombinedSignal(...signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();

  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort();
      return controller.signal;
    }

    signal.addEventListener('abort', () => {
      controller.abort();
    });
  }

  return controller.signal;
}

/**
 * 创建 AbortController 用于取消 SSE 请求
 */
export function createSSEController(): {
  controller: AbortController;
  abort: () => void;
} {
  const controller = new AbortController();
  return {
    controller,
    abort: () => controller.abort(),
  };
}
