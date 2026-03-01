"""
User Service

Handles user-related operations: match history and favorites.

Author: Iteration 3 - Advanced Features
Created: 2026-03-01
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

import config
from lib.client.db import MySQLClient
from lib.globals import core_logger as log


class UserService:
    """
    User service for history and favorites management.

    Follows the same initialization pattern as other services.
    """

    def __init__(self, db_name: str = None):
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)

    # ============== History ==============

    def record_history(
        self,
        user_id: int,
        kp_ids: List[int],
        kp_names: List[str],
        params: dict,
        mode: str = "list"
    ) -> int:
        """
        Record a match history entry.

        Args:
            user_id: User ID
            kp_ids: List of knowledge point IDs
            kp_names: List of knowledge point names (same order as kp_ids)
            params: Match parameters (top_k, target_difficulty, etc.)
            mode: Match mode ('list', 'matrix', 'composite', 'composite_matrix')

        Returns:
            Created history record ID
        """
        import json

        self.client.execute(
            """INSERT INTO match_history (user_id, kp_ids, kp_names, params, mode)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, json.dumps(kp_ids), json.dumps(kp_names), json.dumps(params), mode)
        )

        # Get the inserted ID
        result = self.client.fetch_one("SELECT LAST_INSERT_ID() as id")
        record_id = result['id'] if result else 0

        log.debug(f"[UserService] Recorded history: user={user_id}, kp_ids={kp_ids}, mode={mode}")
        return record_id

    def get_history(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[dict], int]:
        """
        Get paginated match history for a user.

        Args:
            user_id: User ID
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (history_items, total_count)
        """
        import json

        # Get total count
        count_result = self.client.fetch_one(
            "SELECT COUNT(*) as total FROM match_history WHERE user_id = %s",
            (user_id,)
        )
        total = count_result['total'] if count_result else 0

        # Get paginated items
        offset = (page - 1) * page_size
        rows = self.client.fetch_all(
            """SELECT id, kp_ids, kp_names, params, mode, created_at
               FROM match_history
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT %s OFFSET %s""",
            (user_id, page_size, offset)
        )

        items = []
        for row in rows:
            items.append({
                'id': row['id'],
                'kp_ids': json.loads(row['kp_ids']) if isinstance(row['kp_ids'], str) else row['kp_ids'],
                'kp_names': json.loads(row['kp_names']) if isinstance(row['kp_names'], str) else row['kp_names'],
                'params': json.loads(row['params']) if isinstance(row['params'], str) else row['params'],
                'mode': row['mode'],
                'created_at': row['created_at'].isoformat() if isinstance(row['created_at'], datetime) else str(row['created_at'])
            })

        return items, total

    # ============== Favorites ==============

    def add_favorite(self, user_id: int, snippet_id: int) -> bool:
        """
        Add a code snippet to user's favorites.

        Idempotent - does nothing if already favorited.

        Args:
            user_id: User ID
            snippet_id: Code snippet ID

        Returns:
            True if added, False if already exists
        """
        try:
            self.client.execute(
                """INSERT INTO favorites (user_id, snippet_id)
                   VALUES (%s, %s)""",
                (user_id, snippet_id)
            )
            log.debug(f"[UserService] Added favorite: user={user_id}, snippet={snippet_id}")
            return True
        except Exception as e:
            # Duplicate key error (already favorited)
            if "Duplicate entry" in str(e) or "1062" in str(e):
                log.debug(f"[UserService] Favorite already exists: user={user_id}, snippet={snippet_id}")
                return False
            raise

    def remove_favorite(self, user_id: int, snippet_id: int) -> bool:
        """
        Remove a code snippet from user's favorites.

        Idempotent - does nothing if not favorited.

        Args:
            user_id: User ID
            snippet_id: Code snippet ID

        Returns:
            True if removed, False if didn't exist
        """
        self.client.execute(
            "DELETE FROM favorites WHERE user_id = %s AND snippet_id = %s",
            (user_id, snippet_id)
        )

        # Check if any row was affected
        result = self.client.fetch_one("SELECT ROW_COUNT() as affected")
        affected = result['affected'] if result else 0

        if affected > 0:
            log.debug(f"[UserService] Removed favorite: user={user_id}, snippet={snippet_id}")
            return True
        else:
            log.debug(f"[UserService] Favorite not found: user={user_id}, snippet={snippet_id}")
            return False

    def get_favorites(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[dict], int]:
        """
        Get paginated favorites for a user with snippet details.

        Args:
            user_id: User ID
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            Tuple of (favorite_items, total_count)
        """
        # Get total count
        count_result = self.client.fetch_one(
            "SELECT COUNT(*) as total FROM favorites WHERE user_id = %s",
            (user_id,)
        )
        total = count_result['total'] if count_result else 0

        # Get paginated items with snippet details (JOIN query)
        offset = (page - 1) * page_size
        rows = self.client.fetch_all(
            """SELECT f.id, f.snippet_id, f.created_at,
                      s.content, s.file_path
               FROM favorites f
               JOIN code_snippets s ON f.snippet_id = s.id
               WHERE f.user_id = %s
               ORDER BY f.created_at DESC
               LIMIT %s OFFSET %s""",
            (user_id, page_size, offset)
        )

        items = []
        for row in rows:
            items.append({
                'id': row['id'],
                'snippet_id': row['snippet_id'],
                'content': row['content'],
                'file_path': row['file_path'],
                'created_at': row['created_at'].isoformat() if isinstance(row['created_at'], datetime) else str(row['created_at'])
            })

        return items, total

    def get_favorite_ids(self, user_id: int) -> List[int]:
        """
        Get all favorited snippet IDs for a user.

        Used for frontend to check favorite status of displayed snippets.

        Args:
            user_id: User ID

        Returns:
            List of snippet IDs
        """
        rows = self.client.fetch_all(
            "SELECT snippet_id FROM favorites WHERE user_id = %s",
            (user_id,)
        )
        return [row['snippet_id'] for row in rows]

    def is_favorited(self, user_id: int, snippet_id: int) -> bool:
        """
        Check if a snippet is favorited by user.

        Args:
            user_id: User ID
            snippet_id: Code snippet ID

        Returns:
            True if favorited, False otherwise
        """
        result = self.client.fetch_one(
            "SELECT 1 FROM favorites WHERE user_id = %s AND snippet_id = %s",
            (user_id, snippet_id)
        )
        return result is not None
