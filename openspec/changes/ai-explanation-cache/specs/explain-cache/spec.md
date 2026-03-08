# Spec: AI 解释缓存模块

## 概述

为 AI 代码解释功能提供缓存支持，减少 LLM 调用，提升响应速度。

## 数据库表设计

### explain_cache 表

```sql
CREATE TABLE IF NOT EXISTS explain_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(128) NOT NULL UNIQUE COMMENT '缓存键：snippet_id:kp_ids_hash:user_level',
    snippet_id INT NOT NULL,
    kp_ids_hash VARCHAR(64) NOT NULL COMMENT 'kp_ids 排序后的 MD5',
    user_level ENUM('beginner', 'intermediate', 'advanced') NOT NULL DEFAULT 'beginner',
    content TEXT NOT NULL COMMENT '完整的 AI 解释内容',
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL COMMENT '过期时间（默认 7 天后）',
    hit_count INT DEFAULT 0 COMMENT '命中次数',
    last_hit_at TIMESTAMP NULL COMMENT '最后命中时间',
    INDEX idx_cache_key (cache_key),
    INDEX idx_snippet_id (snippet_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

## API 变更

### POST /api/explain

**新增请求参数**：
```json
{
  "force_refresh": false  // 可选，强制重新生成
}
```

**新增响应字段**（SSE done 事件）：
```json
{
  "type": "done",
  "tokens": {...},
  "from_cache": true,
  "cached_at": "2026-03-08T10:30:00Z"
}
```

## 缓存服务接口

### CacheService

```python
class ExplainCacheService:
    def get_cache_key(self, snippet_id: int, kp_ids: List[int], user_level: str) -> str:
        """生成缓存键"""
        pass

    def get_cached(self, cache_key: str) -> Optional[Dict]:
        """获取缓存，返回 {content, tokens, created_at} 或 None"""
        pass

    def set_cached(self, cache_key: str, content: str, tokens: Dict,
                   snippet_id: int, kp_ids: List[int], user_level: str) -> None:
        """存储缓存"""
        pass

    def invalidate_by_snippet(self, snippet_id: int) -> int:
        """清除指定代码片段的所有缓存，返回清除数量"""
        pass

    def cleanup_expired(self) -> int:
        """清理过期缓存，返回清除数量"""
        pass
```

## 缓存流程

```
请求到达
    ↓
生成 cache_key
    ↓
查询 explain_cache
    ↓
┌─ 命中 ─────────────────────┐
│  更新 hit_count, last_hit_at │
│  返回缓存内容（SSE 格式）      │
│  from_cache = true           │
│  不消耗配额                   │
└─────────────────────────────┘
    ↓ 未命中
调用 LLM 生成
    ↓
存储到 explain_cache
    ↓
返回生成内容
from_cache = false
消耗配额
```

## 配置项

```yaml
# config/cache.yaml
explain_cache:
  ttl_days: 7           # 缓存过期天数
  max_entries: 10000    # 最大缓存条目
  cleanup_interval: 24h # 清理任务间隔
```

## 注意事项

1. **缓存键设计**：kp_ids 需排序后再 hash，确保 [1,2] 和 [2,1] 命中同一缓存
2. **并发写入**：使用 `INSERT ... ON DUPLICATE KEY UPDATE` 避免重复
3. **大内容处理**：content 字段使用 TEXT 类型，支持长文本
4. **监控指标**：记录 hit_count 用于分析缓存效果
