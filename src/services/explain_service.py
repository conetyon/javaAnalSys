"""
Explain Service - AI-Powered Code Explanation

Provides streaming AI explanations for Java code snippets,
including multi-turn conversation support.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

import json
import time
import uuid
from typing import Generator, Optional, Dict, Any, List

import config
from lib.client.db import MySQLClient
from lib.client.llm import get_llm_client
from lib.globals import core_logger as log
from src.services.highlight_service import get_highlight_service


class SessionCache:
    """Simple in-memory session cache with TTL and size limit."""

    def __init__(self, max_size: int = 1000, ttl: int = 1800):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._ttl = ttl

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        item = self._cache.get(key)
        if item and time.time() - item['ts'] < self._ttl:
            return item['data']
        self._cache.pop(key, None)
        return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        # Evict if at capacity
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        self._cache[key] = {'data': value, 'ts': time.time()}

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['ts'])
        del self._cache[oldest_key]


# Global session cache
_session_cache = SessionCache()


class ExplainService:
    """
    AI code explanation service.

    Features:
    - Streaming explanation generation
    - Multi-turn conversation with context memory
    - Automatic code regeneration for poor examples
    - Request logging for audit
    """

    def __init__(self, db_name: str = None):
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)
        self.llm_client = get_llm_client()
        self.highlight_service = get_highlight_service()

    def stream_explain(
        self,
        user_id: int,
        snippet_id: int,
        kp_id: int,
        user_level: str = 'beginner',
        kp_ids: List[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream AI explanation for a code snippet.

        Args:
            user_id: Requesting user's ID
            snippet_id: Code snippet ID
            kp_id: Primary knowledge point ID (used if kp_ids is None)
            user_level: User expertise level (beginner/intermediate/advanced)
            kp_ids: Optional list of knowledge point IDs for composite matching

        Yields:
            Dict with type (content/done/error) and relevant data
        """
        # 使用 kp_ids 如果提供，否则使用单个 kp_id
        effective_kp_ids = kp_ids if kp_ids else [kp_id]
        log.info(f"[ExplainService.stream_explain] Starting: user={user_id}, snippet={snippet_id}, kps={effective_kp_ids}")
        start_time = time.time()

        # Fetch snippet
        log.debug(f"[ExplainService] Fetching snippet {snippet_id}")
        snippet = self._get_snippet(snippet_id)
        if not snippet:
            log.warning(f"[ExplainService] Snippet {snippet_id} not found")
            yield {"type": "error", "error": "代码片段不存在"}
            return

        # Fetch all KPs and merge their info
        kps = []
        all_keywords = []
        all_highlights = []

        for kid in effective_kp_ids:
            log.debug(f"[ExplainService] Fetching KP {kid}")
            kp = self._get_knowledge_point(kid)
            if not kp:
                log.warning(f"[ExplainService] KP {kid} not found")
                yield {"type": "error", "error": f"知识点 {kid} 不存在"}
                return
            kps.append(kp)

            # Extract keywords
            kp_keywords = self._parse_json_field(kp.get('keywords')) or []
            all_keywords.extend(kp_keywords)

            # Compute highlights for this KP
            highlights = self.highlight_service.compute_highlights(
                snippet['content'],
                self._parse_json_field(kp.get('ast_template')),
                kp_keywords
            )
            all_highlights.extend(highlights)

        # Deduplicate and sort highlights
        seen_ranges = set()
        unique_highlights = []
        for h in all_highlights:
            key = (h['start_line'], h['end_line'], h['type'])
            if key not in seen_ranges:
                seen_ranges.add(key)
                unique_highlights.append(h)
        unique_highlights.sort(key=lambda x: x['start_line'])

        # Deduplicate keywords
        unique_keywords = list(dict.fromkeys(all_keywords))

        # Build KP display name (combine all KP names)
        if len(kps) == 1:
            kp_name = kps[0]['name']
            kp_name_zh = kps[0].get('name_zh', '')
        else:
            kp_name = ' + '.join(kp['name'] for kp in kps)
            kp_name_zh = ' + '.join(kp.get('name_zh') or kp['name'] for kp in kps)

        # Build prompt
        log.debug(f"[ExplainService] Building messages for {len(kps)} KPs")
        messages = self._build_explain_messages(
            code=snippet['content'],
            kp_name=kp_name,
            kp_name_zh=kp_name_zh,
            highlights=unique_highlights,
            user_level=user_level,
            keywords=unique_keywords
        )

        # Stream from LLM
        log.info(f"[ExplainService] Calling LLM stream_completion")
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        latency_ms = 0

        for chunk in self.llm_client.stream_completion(messages):
            if chunk["type"] == "content":
                yield chunk
            elif chunk["type"] == "done":
                total_usage = chunk.get("usage", total_usage)
                latency_ms = chunk.get("latency_ms", 0)
                log.info(f"[ExplainService] LLM completed: latency={latency_ms}ms")
                yield {
                    "type": "done",
                    "tokens": total_usage
                }
            elif chunk["type"] == "error":
                log.error(f"[ExplainService] LLM error: {chunk.get('error')}")
                yield chunk
                latency_ms = int((time.time() - start_time) * 1000)

        # Log request (use primary KP ID + full kp_ids list)
        self._log_request(
            user_id=user_id,
            snippet_id=snippet_id,
            kp_id=effective_kp_ids[0],
            request_type='explain',
            prompt_tokens=total_usage.get("prompt_tokens"),
            completion_tokens=total_usage.get("completion_tokens"),
            latency_ms=latency_ms,
            kp_ids=effective_kp_ids if len(effective_kp_ids) > 1 else None
        )

    def stream_chat(
        self,
        user_id: int,
        snippet_id: int,
        kp_id: int,
        question: str,
        session_id: Optional[str] = None,
        kp_ids: List[int] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream AI response for a follow-up question.

        Args:
            user_id: Requesting user's ID
            snippet_id: Code snippet ID
            kp_id: Primary knowledge point ID
            question: User's question
            session_id: Optional session ID for multi-turn context
            kp_ids: Optional list of knowledge point IDs for composite matching

        Yields:
            Dict with type (content/done/error/session_id) and relevant data
        """
        start_time = time.time()
        effective_kp_ids = kp_ids if kp_ids else [kp_id]

        # Fetch snippet
        snippet = self._get_snippet(snippet_id)
        if not snippet:
            yield {"type": "error", "error": "代码片段不存在"}
            return

        # Fetch all KPs and build combined name
        kps = []
        for kid in effective_kp_ids:
            kp = self._get_knowledge_point(kid)
            if not kp:
                yield {"type": "error", "error": f"知识点 {kid} 不存在"}
                return
            kps.append(kp)

        # Build KP display name
        if len(kps) == 1:
            kp_name = kps[0]['name']
            kp_name_zh = kps[0].get('name_zh', '')
        else:
            kp_name = ' + '.join(kp['name'] for kp in kps)
            kp_name_zh = ' + '.join(kp.get('name_zh') or kp['name'] for kp in kps)

        # Get or create session
        if session_id:
            session = _session_cache.get(session_id)
        else:
            session = None
            session_id = str(uuid.uuid4())

        history = session.get("history", []) if session else []

        # Build prompt
        messages = self._build_chat_messages(
            code=snippet['content'],
            kp_name=kp_name,
            kp_name_zh=kp_name_zh,
            question=question,
            history=history
        )

        # Yield session ID immediately
        yield {"type": "session_id", "session_id": session_id}

        # Stream from LLM
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        latency_ms = 0
        response_content = []

        for chunk in self.llm_client.stream_completion(messages):
            if chunk["type"] == "content":
                response_content.append(chunk["content"])
                yield chunk
            elif chunk["type"] == "done":
                total_usage = chunk.get("usage", total_usage)
                latency_ms = chunk.get("latency_ms", 0)
                yield {
                    "type": "done",
                    "tokens": total_usage
                }
            elif chunk["type"] == "error":
                yield chunk
                latency_ms = int((time.time() - start_time) * 1000)

        # Update session with new history
        full_response = "".join(response_content)
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": full_response})

        # Keep only last 10 turns to avoid context overflow
        if len(history) > 20:
            history = history[-20:]

        _session_cache.set(session_id, {
            "history": history,
            "snippet_id": snippet_id,
            "kp_ids": effective_kp_ids
        })

        # Log request
        self._log_request(
            user_id=user_id,
            snippet_id=snippet_id,
            kp_id=effective_kp_ids[0],
            request_type='chat',
            prompt_tokens=total_usage.get("prompt_tokens"),
            completion_tokens=total_usage.get("completion_tokens"),
            latency_ms=latency_ms,
            kp_ids=effective_kp_ids if len(effective_kp_ids) > 1 else None
        )

    def _build_explain_messages(
        self,
        code: str,
        kp_name: str,
        kp_name_zh: str,
        highlights: List[Dict[str, Any]],
        user_level: str,
        keywords: List[str] = None
    ) -> List[Dict[str, str]]:
        """Build messages for explanation prompt."""
        level_desc = {
            "beginner": "初学者",
            "intermediate": "中级学习者",
            "advanced": "高级开发者"
        }.get(user_level, "学习者")

        highlights_text = ""
        if highlights:
            highlights_text = "\n".join([
                f"- 第 {h['start_line']}-{h['end_line']} 行: {h['label']}"
                for h in highlights[:10]  # Limit to top 10
            ])
        else:
            highlights_text = "（未检测到特定关键行）"

        # 知识点关键词（用于增强 LLM 上下文）
        keywords_text = ""
        if keywords:
            keywords_text = f"\n【核心关键词】{', '.join(keywords[:8])}"

        kp_display = f"{kp_name}"
        if kp_name_zh:
            kp_display = f"{kp_name} ({kp_name_zh})"

        system_prompt = f"""你是一位 Java 教学助手，正在帮助学生理解代码。

【知识点】{kp_display}{keywords_text}

【当前代码片段】
```java
{code}
```

【关键行标注】
{highlights_text}

【学生水平】{level_desc}

请用简洁易懂的语言解释这段代码：
1. 概述代码的功能和主要逻辑
2. 逐行或逐块解释代码，重点说明标注的关键行如何体现该知识点
3. 如有必要，指出代码中值得注意的写法或潜在改进点

**重要要求**：
- 必须基于上面给出的代码片段进行解释，不要自己编写新的示例代码
- 即使代码较复杂，也要帮助学生理解这段具体代码
- 解释应紧扣实际代码内容，不要偏离原始代码

回答要求：
- 使用中文
- 适合 {level_desc} 水平的学习者
- 重点突出，避免冗长
- 如果代码中包含疑似敏感信息（如 API Key、密码、Token），不要在解释中暴露这些值"""

        # DEBUG: 记录 prompt 构建信息
        log.debug(f"[ExplainService] Prompt built: kp={kp_display}, highlights={len(highlights or [])}, keywords={len(keywords or [])}")

        return [{"role": "system", "content": system_prompt}]

    def _build_chat_messages(
        self,
        code: str,
        kp_name: str,
        kp_name_zh: str,
        question: str,
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Build messages for chat prompt."""
        kp_display = f"{kp_name}"
        if kp_name_zh:
            kp_display = f"{kp_name} ({kp_name_zh})"

        # Format history
        history_text = ""
        if history:
            for msg in history[-6:]:  # Last 3 turns
                role_label = "学生" if msg["role"] == "user" else "助手"
                history_text += f"{role_label}: {msg['content']}\n\n"

        system_prompt = f"""你是一位 Java 教学助手，正在与学生进行问答。

【知识点】{kp_display}

【当前代码片段】
```java
{code}
```

【对话历史】
{history_text if history_text else '（首次对话）'}

请针对学生的问题进行解答。

如果学生要求"换一个例子"、"有没有更简单的"、"这个太复杂了"等，直接编写一个更合适的示例代码并解释。

回答要求：
- 使用中文
- 直接回答问题，不要重复之前说过的内容
- 生成的代码要简洁、正确、可运行"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": question})

        return messages

    def _get_snippet(self, snippet_id: int) -> Optional[Dict[str, Any]]:
        """Get code snippet by ID."""
        row = self.client.fetch_one(
            "SELECT id, content, file_path FROM code_snippets WHERE id = %s",
            (snippet_id,)
        )
        return dict(row) if row else None

    def _get_knowledge_point(self, kp_id: int) -> Optional[Dict[str, Any]]:
        """Get knowledge point by ID."""
        row = self.client.fetch_one(
            "SELECT id, name, name_zh, ast_template, keywords FROM knowledge_points WHERE id = %s",
            (kp_id,)
        )
        return dict(row) if row else None

    def _parse_json_field(self, value: Any) -> Any:
        """Parse JSON field that might be string or already parsed."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def _log_request(
        self,
        user_id: int,
        snippet_id: int,
        kp_id: int,
        request_type: str,
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int],
        latency_ms: int,
        kp_ids: List[int] = None
    ) -> None:
        """Log request to explain_logs table."""
        try:
            # kp_ids 序列化为 JSON 字符串
            kp_ids_json = json.dumps(kp_ids) if kp_ids else None
            self.client.execute(
                """INSERT INTO explain_logs
                   (user_id, snippet_id, kp_id, kp_ids, request_type, prompt_tokens, completion_tokens, latency_ms)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, snippet_id, kp_id, kp_ids_json, request_type, prompt_tokens, completion_tokens, latency_ms)
            )
        except Exception as e:
            log.error(f"[ExplainService] Failed to log request: {e}")


# Singleton instance
_explain_service: Optional[ExplainService] = None


def get_explain_service() -> ExplainService:
    """Get singleton ExplainService instance."""
    global _explain_service
    if _explain_service is None:
        _explain_service = ExplainService()
    return _explain_service
