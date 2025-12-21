# lib/client/sql.py
from __future__ import annotations

import hashlib
from typing import Dict, Optional, Any, List, Tuple
from mysql.connector import pooling as mysql_pooling, MySQLConnection
from mysql.connector.pooling import PooledMySQLConnection

from lib.globals import Cfg
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
            raise ValueError(f"DB config '{db}' not found in settings.db")
        if cfg.db is None:
            raise ValueError(f"DB config '{db}' is missing field 'db'")

        self._cfg: DbConfig = cfg
        self._autocommit = autocommit
        self._conn: Optional[MySQLConnection] = None

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
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        self._release_conn(conn)
        return row

    def fetch_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List:
        """
        执行查询，返回多行结果列表。
        """
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        self._release_conn(conn)
        return rows

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
        pool = self._get_pool(self._cfg)
        conn = pool.get_connection()
        cur = None
        try:
            conn.autocommit = False
            cur = conn.cursor()
            for sql, params in statements:
                cur.execute(sql, params)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if cur:
                cur.close()
            conn.close()
