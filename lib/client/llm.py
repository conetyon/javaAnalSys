"""
LLM Client for OpenAI-compatible APIs

Provides streaming completion support for AI code explanation feature.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

import json
import time
import socket
from typing import Generator, Optional, Dict, Any

import requests

from lib.globals import Cfg, core_logger as log


class LLMClient:
    """
    LLM API client with streaming support.

    Uses OpenAI-compatible chat completions API.
    Supports fallback endpoint when primary fails.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """
        Initialize LLM client.

        Args:
            endpoint: API endpoint URL (default: from config)
            model: Model name (default: from config)
            api_key: API key (default: from config/env)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        """
        llm_cfg = Cfg.llm
        if llm_cfg:
            self.endpoint = endpoint or llm_cfg.endpoint
            self.model = model or llm_cfg.model
            self.api_key = api_key or llm_cfg.get_api_key()
            self.timeout = timeout or llm_cfg.timeout
            self.max_tokens = max_tokens or llm_cfg.max_tokens
            self.temperature = temperature if temperature is not None else llm_cfg.temperature

            # 兜底配置
            self.fallback_endpoint = None
            self.fallback_model = None
            self.fallback_api_key = None
            if llm_cfg.fallback:
                self.fallback_endpoint = llm_cfg.fallback.endpoint
                self.fallback_model = llm_cfg.fallback.model
                self.fallback_api_key = llm_cfg.fallback.get_api_key()
        else:
            self.endpoint = endpoint or ""
            self.model = model or ""
            self.api_key = api_key or ""
            self.timeout = timeout
            self.max_tokens = max_tokens
            self.temperature = temperature
            self.fallback_endpoint = None
            self.fallback_model = None
            self.fallback_api_key = None

    def stream_completion(
        self,
        messages: list,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream chat completion responses.
        Automatically tries fallback endpoint if primary fails.

        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Yields:
            Dict with keys:
            - type: "content" or "done" or "error"
            - content: text chunk (for type="content")
            - usage: token usage dict (for type="done")
            - error: error message (for type="error")
        """
        # 尝试主端点
        primary_error = None
        for chunk in self._stream_from_endpoint(
            self.endpoint, self.model, self.api_key,
            messages, max_tokens, temperature, "primary"
        ):
            if chunk["type"] == "error":
                primary_error = chunk["error"]
                break
            yield chunk
            if chunk["type"] == "done":
                return  # 成功完成

        # 主端点失败，尝试兜底端点
        if primary_error and self.fallback_endpoint and self.fallback_api_key:
            log.warning(f"[LLMClient] Primary endpoint failed: {primary_error}, trying fallback...")
            for chunk in self._stream_from_endpoint(
                self.fallback_endpoint, self.fallback_model, self.fallback_api_key,
                messages, max_tokens, temperature, "fallback"
            ):
                yield chunk
                if chunk["type"] in ("done", "error"):
                    return
        elif primary_error:
            yield {"type": "error", "error": primary_error}

    def _stream_from_endpoint(
        self,
        endpoint: str,
        model: str,
        api_key: str,
        messages: list,
        max_tokens: Optional[int],
        temperature: Optional[float],
        endpoint_name: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream from a specific endpoint."""
        if not endpoint or not api_key:
            yield {"type": "error", "error": f"AI 服务未配置，请联系管理员"}
            return

        url = f"{endpoint.rstrip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "stream": True
        }

        start_time = time.time()
        total_content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0}

        try:
            log.info(f"[LLMClient] [{endpoint_name}] Sending request to {url}, model={model}")

            session = requests.Session()
            response = session.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(10, self.timeout)
            )

            log.info(f"[LLMClient] [{endpoint_name}] Response status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                log.error(f"[LLMClient] [{endpoint_name}] API error: {response.status_code} - {error_text}")
                yield {"type": "error", "error": f"AI 服务返回错误 ({response.status_code})，请稍后重试"}
                return

            log.info(f"[LLMClient] [{endpoint_name}] Starting to iterate response...")
            line_count = 0
            buffer = ""

            # 强制设置响应编码为 UTF-8（LLM API 返回 UTF-8 但可能没有在响应头指定）
            response.encoding = 'utf-8'

            # 使用 iter_content 而不是 iter_lines，手动处理行分割
            # 避免 UTF-8 多字节字符被切割
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if not chunk:
                    continue

                buffer += chunk

                # 按 SSE 的双换行分割事件
                while '\n\n' in buffer:
                    event, buffer = buffer.split('\n\n', 1)

                    # 处理每一行
                    for line in event.split('\n'):
                        if not line or not line.startswith('data: '):
                            continue

                        line_count += 1
                        if line_count <= 3:
                            log.info(f"[LLMClient] [{endpoint_name}] Line #{line_count}: {line[:80]}...")

                        data_str = line[6:]

                        if data_str == '[DONE]':
                            log.info(f"[LLMClient] [{endpoint_name}] Received [DONE] signal")
                            break

                        try:
                            data = json.loads(data_str)
                            choice = data.get('choices', [{}])[0]
                            delta = choice.get('delta', {})
                            content = delta.get('content', '')

                            if content:
                                total_content += content
                                yield {"type": "content", "content": content}

                            if 'usage' in data:
                                usage = data['usage']

                        except json.JSONDecodeError as e:
                            log.warning(f"[LLMClient] [{endpoint_name}] JSON decode error: {e}")
                            continue

            if usage['prompt_tokens'] == 0:
                prompt_text = " ".join(m.get('content', '') for m in messages)
                usage['prompt_tokens'] = len(prompt_text) // 4
                usage['completion_tokens'] = len(total_content) // 4

            latency_ms = int((time.time() - start_time) * 1000)
            log.info(f"[LLMClient] [{endpoint_name}] Completed: {len(total_content)} chars, {latency_ms}ms")

            yield {
                "type": "done",
                "usage": usage,
                "latency_ms": latency_ms
            }

        except requests.exceptions.Timeout:
            log.error(f"[LLMClient] [{endpoint_name}] Request timeout")
            yield {"type": "error", "error": "请求超时，AI 服务响应过慢，请稍后重试"}
        except requests.exceptions.ConnectionError as e:
            log.error(f"[LLMClient] [{endpoint_name}] Connection error: {e}")
            yield {"type": "error", "error": "无法连接 AI 服务，请检查网络或稍后重试"}
        except socket.timeout:
            log.error(f"[LLMClient] [{endpoint_name}] Socket timeout")
            yield {"type": "error", "error": "网络连接超时，请稍后重试"}
        except Exception as e:
            log.error(f"[LLMClient] [{endpoint_name}] Unexpected error: {e}")
            yield {"type": "error", "error": f"AI 服务异常: {str(e)}"}

    def completion(
        self,
        messages: list,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Non-streaming chat completion (for simple use cases).

        Args:
            messages: List of message dicts
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Returns:
            Dict with keys: content, usage, latency_ms, error (if any)
        """
        content_parts = []
        result = {"content": "", "usage": {}, "latency_ms": 0}

        for chunk in self.stream_completion(messages, max_tokens, temperature):
            if chunk["type"] == "content":
                content_parts.append(chunk["content"])
            elif chunk["type"] == "done":
                result["usage"] = chunk["usage"]
                result["latency_ms"] = chunk["latency_ms"]
            elif chunk["type"] == "error":
                result["error"] = chunk["error"]
                return result

        result["content"] = "".join(content_parts)
        return result


# Singleton instance (lazy initialization)
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
        log.info(f"[LLMClient] Initialized: endpoint={_llm_client.endpoint}, model={_llm_client.model}")
        log.info(f"[LLMClient] Fallback: endpoint={_llm_client.fallback_endpoint}, model={_llm_client.fallback_model}")
    return _llm_client


def reset_llm_client():
    """Reset LLM client singleton (for testing/config reload)."""
    global _llm_client
    _llm_client = None
    log.info("[LLMClient] Singleton reset")
