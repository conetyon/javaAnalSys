# lib/client/sql.py
from __future__ import annotations

import hashlib
from typing import Dict, Optional, Any, List, Tuple
from mysql.connector import pooling as mysql_pooling, MySQLConnection
from mysql.connector.pooling import PooledMySQLConnection

from lib.globals import Cfg, core_logger as log
from lib.utils.settings import DbConfig

__all__ = ["MySQLClient"]


class MySQLClient:
    """
    使用 mysql-connector 内置连接池，支持单次操作、显式事务（多条语句）以及一次性执行多条 SQL 事务，而无需 with 结构。

    简单场景：每次调用自动从连接池获取连接，执行完成后自动提交
        db = MySQLClient(db='videoWdb')
        rows = db.fetch_all("SELECT * FROM task_queue WHERE status=%s", ("Pending",))
        db.update("UPDATE task_queue SET status=%s WHERE id=%s", ("Processing", 1))

    事务场景：with 上下文管理器，支持多次 execute 后一次性提交或回滚
        with MySQLClient(db='videoWdb', autocommit=False) as tx:
            tx.execute("UPDATE a SET x=%s WHERE id=%s", (...,))
            tx.execute("UPDATE b SET y=%s WHERE id=%s", (...,))

    批量事务方法：支持一次性执行多条 SQL（带参数），在单个事务中执行并自动提交或回滚
        db = MySQLClient(db='videoWdb')
        statements = [
            ("UPDATE a SET x=%s WHERE id=%s", (1, 2)),
            ("UPDATE b SET y=%s WHERE id=%s", (3, 4)),
        ]
        db.execute_transaction(statements)
    """

    _POOLS: Dict[str, mysql_pooling.MySQLConnectionPool] = {}

    def __init__(self, db: str = 'videoWdb', autocommit: bool = True) -> None:
        cfg = Cfg.db.get(db)
        if cfg is None:
            log.error("[MySQLClient] 数据库配置不存在: db=%s", db)
            raise ValueError(f"DB config '{db}' not found in settings.db")
        if cfg.db is None:
            log.error("[MySQLClient] 数据库配置缺少 'db' 字段: db=%s", db)
            raise ValueError(f"DB config '{db}' is missing field 'db'")

        self._cfg: DbConfig = cfg
        self._autocommit = autocommit
        self._conn: Optional[MySQLConnection] = None
        log.debug("[MySQLClient] 初始化: db=%s, autocommit=%s", db, autocommit)

    def __enter__(self) -> MySQLClient:
        # 事务模式：保留连接直到 __exit__
        pool = self._get_pool(self._cfg)
        conn = pool.get_connection()
        conn.autocommit = self._autocommit
        self._conn = conn
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # 事务模式：根据异常决定提交或回滚
        if self._conn:
            if not self._autocommit:
                if exc_type:
                    self._conn.rollback()
                else:
                    self._conn.commit()
            self._conn.close()
            self._conn = None

    @classmethod
    def _get_pool(cls, cfg: DbConfig) -> mysql_pooling.MySQLConnectionPool:
        fp = cls._fingerprint(cfg)
        if fp not in cls._POOLS:
            pool_size = max(1, min(cfg.maxConn, 32))
            cls._POOLS[fp] = mysql_pooling.MySQLConnectionPool(
                pool_name=f"pool_{fp[:8]}",
                pool_size=pool_size,
                pool_reset_session=True,
                host=cfg.host,
                port=cfg.port,
                user=cfg.user,
                password=cfg.password,
                database=cfg.db,
                charset=cfg.charset,
            )
        return cls._POOLS[fp]

    @staticmethod
    def _fingerprint(cfg: DbConfig) -> str:
        raw = f"{cfg.host}:{cfg.port}:{cfg.user}:{cfg.db}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_conn(self) -> MySQLConnection | PooledMySQLConnection:
        """
        获取当前连接：事务模式下返回保留连接，否则从连接池获取一个新的。
        """
        if self._conn:
            return self._conn
        pool = self._get_pool(self._cfg)
        conn = pool.get_connection()
        conn.autocommit = True
        return conn

    def _release_conn(self, conn: MySQLConnection) -> None:
        """
        非事务模式下，需要在使用后关闭连接以归还到连接池；事务模式下保留连接直到 __exit__。
        """
        if conn is not self._conn:
            conn.close()

    def execute(
        self,
        sql: str,
        params: Tuple[Any, ...] = (),
        dictionary: bool = False
    ) -> None:
        """
        执行单条 DML/DDL 语句。事务模式下，需要手动 commit，简单模式下自动提交。
        """
        conn = self._get_conn()
        cur = conn.cursor(dictionary=dictionary)
        cur.execute(sql, params)
        cur.close()
        # 简单模式下每次都提交并关闭
        if not self._conn:
            conn.commit()
            conn.close()

    def fetch_one(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        """
        执行查询，返回单行结果或 None。
        """
        log.debug("[MySQLClient.fetch_one] SQL: %s, params: %s", sql[:200], params)
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            row = cur.fetchone()
            log.debug("[MySQLClient.fetch_one] 结果: %s", "找到" if row else "无")
            return row
        except Exception as e:
            log.error("[MySQLClient.fetch_one] 执行失败: %s", e)
            raise
        finally:
            cur.close()
            self._release_conn(conn)

    def fetch_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List:
        """
        执行查询，返回多行结果列表。
        """
        log.debug("[MySQLClient.fetch_all] SQL: %s, params: %s", sql[:200], params)
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            rows = cur.fetchall()
            log.debug("[MySQLClient.fetch_all] 返回 %d 行", len(rows) if rows else 0)
            return rows
        except Exception as e:
            log.error("[MySQLClient.fetch_all] 执行失败: %s", e)
            raise
        finally:
            cur.close()
            self._release_conn(conn)

    def update(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        """
        执行更新/删除/插入，并自动提交（等同 execute）。
        """
        self.execute(sql, params)

    def execute_transaction(
        self,
        statements: List[Tuple[str, Tuple[Any, ...]]]
    ) -> None:
        """
        一次性执行多条 SQL 事务。即使在非 with 模式，也从连接池获取连接，执行所有语句后提交或回滚。

        :param statements: List of (sql, params) tuples
        """
        log.debug("[MySQLClient.execute_transaction] 开始执行事务, 语句数=%d", len(statements))
        pool = self._get_pool(self._cfg)
        conn = pool.get_connection()
        cur = None
        try:
            conn.autocommit = False
            cur = conn.cursor()
            for idx, (sql, params) in enumerate(statements):
                log.debug("[MySQLClient.execute_transaction] 执行语句 #%d: %s", idx, sql[:100])
                cur.execute(sql, params)
            conn.commit()
            log.info("[MySQLClient.execute_transaction] 事务提交成功, 语句数=%d", len(statements))
        except Exception as e:
            log.error("[MySQLClient.execute_transaction] 事务失败，回滚: %s", e)
            conn.rollback()
            raise
        finally:
            if cur:
                cur.close()
            conn.close()
