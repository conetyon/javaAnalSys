# src/db_manager/database.py
import mysql.connector
from lib.globals import Cfg
from lib.client.db import MySQLClient
from .base import BaseManager, DEFAULT_DB_NAME

class DatabaseInitializer(BaseManager):
    def init_db(self):
        """
        执行完整的数据库初始化流程：检查数据库是否存在 -> 创建数据库 -> 创建表。
        """
        self._ensure_database_exists()
        self._init_tables()

    def _ensure_database_exists(self):
        """连接 MySQL Server（无 DB 上下文）以创建数据库。"""
        db_cfg = Cfg.db.get(self.db_name)
        if not db_cfg:
            raise ValueError(f"数据库配置 '{self.db_name}' 未在 config.yaml 中找到！")

        try:
            # 这里的关键是不指定 database 参数进行连接
            conn = mysql.connector.connect(
                host=db_cfg.host,
                port=db_cfg.port,
                user=db_cfg.user,
                password=db_cfg.password
            )
            with conn.cursor() as c:
                c.execute(f"CREATE DATABASE IF NOT EXISTS `{db_cfg.db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.close()
            print(f"[DB Init] 数据库 '{db_cfg.db}' 已确保存在。")
        except Exception as e:
            print(f"[DB Init-Warning] 检查/创建数据库时出现问题: {e}")

    def _init_tables(self):
        """在指定数据库中创建所有必要的数据表。"""
        print(f"[DB Init] 开始初始化数据表 ({self.db_name})...")
        statements = [
            ('''CREATE TABLE IF NOT EXISTS knowledge_points
                (
                    id           INT PRIMARY KEY AUTO_INCREMENT,
                    name         TEXT NOT NULL,
                    parent_id    INTEGER,
                    level        INTEGER,
                    ast_template TEXT,
                    keywords     TEXT,
                    semantic_vec BLOB
                )''', ()),

            ('''CREATE TABLE IF NOT EXISTS code_files
                (
                    id       INT PRIMARY KEY AUTO_INCREMENT,
                    filename TEXT,
                    filepath TEXT,
                    content  LONGTEXT
                )''', ()),

            ('''CREATE TABLE IF NOT EXISTS code_snippets
                (
                    id               INT PRIMARY KEY AUTO_INCREMENT,
                    file_id          INTEGER,
                    start_line       INTEGER,
                    end_line         INTEGER,
                    content          LONGTEXT,
                    complexity_score REAL,
                    ast_features     TEXT,
                    keywords         TEXT,
                    semantic_vec     BLOB,
                    FOREIGN KEY (file_id) REFERENCES code_files (id)
                )''', ())
        ]

        try:
            # 使用基类方法获取客户端
            client = self._get_client()
            client.execute_transaction(statements)
            print("[DB Init] 所有数据表结构已初始化/验证。")
        except Exception as e:
            print(f"[DB Init-Error] 创建数据表时失败: {e}")
            raise

# 方便外部直接调用（保持向后兼容）
def init_db(db_name=None):
    initializer = DatabaseInitializer(db_name)
    initializer.init_db()
