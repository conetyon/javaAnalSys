"""
Quota Service - AI Explanation Usage Quota Management

Manages daily usage quotas for the AI code explanation feature.
Uses Beijing time (Asia/Shanghai) for daily resets.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

import config
from lib.client.db import MySQLClient
from lib.globals import Cfg, core_logger as log


class QuotaService:
    """
    Quota management service for AI explanation feature.

    Features:
    - Daily quota limits per user
    - Automatic reset at midnight Beijing time
    - Admin users have unlimited quota
    - On-demand quota record creation
    """

    def __init__(self, db_name: str = None):
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)

        # Load config
        quota_cfg = Cfg.quota
        if quota_cfg:
            self.default_daily_limit = quota_cfg.default_daily_limit
            self.admin_unlimited = quota_cfg.admin_unlimited
            self.reset_timezone = quota_cfg.reset_timezone
        else:
            self.default_daily_limit = 50
            self.admin_unlimited = True
            self.reset_timezone = "Asia/Shanghai"

    def check_quota(self, user_id: int, user_role: str = 'user') -> bool:
        """
        Check if user has remaining quota.

        Args:
            user_id: User ID
            user_role: User role ('user' or 'admin')

        Returns:
            True if quota available, False if exhausted
        """
        # Admin bypass
        if self.admin_unlimited and user_role == 'admin':
            return True

        quota = self._get_or_create_quota(user_id)
        if quota is None:
            return False

        # Check if reset needed
        self._maybe_reset_quota(user_id, quota)

        # Re-fetch after potential reset
        quota = self._get_quota(user_id)
        if quota is None:
            return False

        return quota['used_today'] < quota['daily_limit']

    def consume_quota(self, user_id: int) -> bool:
        """
        Consume one quota unit.

        Args:
            user_id: User ID

        Returns:
            True if successful, False if quota exhausted
        """
        quota = self._get_or_create_quota(user_id)
        if quota is None:
            return False

        # Check if reset needed
        self._maybe_reset_quota(user_id, quota)

        # Re-fetch
        quota = self._get_quota(user_id)
        if quota is None:
            return False

        if quota['used_today'] >= quota['daily_limit']:
            return False

        # Increment usage
        self.client.execute(
            "UPDATE user_quotas SET used_today = used_today + 1 WHERE user_id = %s",
            (user_id,)
        )
        return True

    def get_quota_info(self, user_id: int, user_role: str = 'user') -> Dict[str, Any]:
        """
        Get detailed quota information for a user.

        Args:
            user_id: User ID
            user_role: User role

        Returns:
            Dict with daily_limit, used_today, remaining, reset_at, unlimited
        """
        # Admin check
        if self.admin_unlimited and user_role == 'admin':
            return {
                "daily_limit": -1,
                "used_today": 0,
                "remaining": -1,
                "reset_at": None,
                "unlimited": True
            }

        quota = self._get_or_create_quota(user_id)
        if quota is None:
            return {
                "daily_limit": self.default_daily_limit,
                "used_today": 0,
                "remaining": self.default_daily_limit,
                "reset_at": self._get_next_reset_time(),
                "unlimited": False
            }

        # Check if reset needed
        self._maybe_reset_quota(user_id, quota)
        quota = self._get_quota(user_id)

        daily_limit = quota['daily_limit']
        used_today = quota['used_today']

        return {
            "daily_limit": daily_limit,
            "used_today": used_today,
            "remaining": max(0, daily_limit - used_today),
            "reset_at": self._get_next_reset_time(),
            "unlimited": False
        }

    def set_daily_limit(self, user_id: int, new_limit: int) -> bool:
        """
        Set custom daily limit for a user.

        Args:
            user_id: User ID
            new_limit: New daily limit

        Returns:
            True if successful
        """
        quota = self._get_or_create_quota(user_id)
        if quota is None:
            return False

        self.client.execute(
            "UPDATE user_quotas SET daily_limit = %s WHERE user_id = %s",
            (new_limit, user_id)
        )
        return True

    def _get_quota(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get quota record for user."""
        row = self.client.fetch_one(
            """SELECT daily_limit, used_today, last_reset_date
               FROM user_quotas WHERE user_id = %s""",
            (user_id,)
        )
        return dict(row) if row else None

    def _get_or_create_quota(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get or create quota record for user."""
        quota = self._get_quota(user_id)
        if quota:
            return quota

        # Create new record
        today = self._get_beijing_date()
        try:
            self.client.execute(
                """INSERT INTO user_quotas (user_id, daily_limit, used_today, last_reset_date)
                   VALUES (%s, %s, 0, %s)""",
                (user_id, self.default_daily_limit, today)
            )
        except Exception as e:
            # Handle race condition (concurrent inserts)
            if "Duplicate entry" not in str(e):
                log.error(f"[QuotaService] Failed to create quota: {e}")
                return None

        return self._get_quota(user_id)

    def _maybe_reset_quota(self, user_id: int, quota: Dict[str, Any]) -> None:
        """Reset quota if a new day has started (Beijing time)."""
        last_reset = quota['last_reset_date']
        today = self._get_beijing_date()

        if last_reset < today:
            self.client.execute(
                """UPDATE user_quotas
                   SET used_today = 0, last_reset_date = %s
                   WHERE user_id = %s""",
                (today, user_id)
            )
            log.debug(f"[QuotaService] Reset quota for user {user_id}")

    def _get_beijing_date(self) -> date:
        """Get current date in Beijing timezone."""
        tz = ZoneInfo(self.reset_timezone)
        return datetime.now(tz).date()

    def _get_next_reset_time(self) -> str:
        """Get next reset time as ISO string with timezone."""
        tz = ZoneInfo(self.reset_timezone)
        now = datetime.now(tz)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if tomorrow <= now:
            from datetime import timedelta
            tomorrow = tomorrow + timedelta(days=1)
        return tomorrow.isoformat()


# Singleton instance
_quota_service: Optional[QuotaService] = None


def get_quota_service() -> QuotaService:
    """Get singleton QuotaService instance."""
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
    return _quota_service
