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
        """在指定数据库中创建所有必要的数据表和索引。"""
        print(f"[DB Init] 开始初始化数据表 ({self.db_name})...")
        statements = [
            ('''CREATE TABLE IF NOT EXISTS knowledge_points
                (
                    id           INT PRIMARY KEY AUTO_INCREMENT,
                    name         VARCHAR(255) NOT NULL,
                    name_zh      VARCHAR(255),
                    parent_id    INTEGER,
                    level        INTEGER,
                    ast_template TEXT,
                    keywords     TEXT,
                    semantic_vec BLOB
                )''', ()),

            ('''CREATE TABLE IF NOT EXISTS code_files
                (
                    id        INT PRIMARY KEY AUTO_INCREMENT,
                    filename  VARCHAR(255),
                    filepath  TEXT,
                    source    VARCHAR(50) DEFAULT 'manual',
                    repo_name VARCHAR(255) DEFAULT '',
                    language  VARCHAR(20) DEFAULT 'java'
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
                    file_path        VARCHAR(512),
                    content_hash     VARCHAR(64) UNIQUE,
                    FOREIGN KEY (file_id) REFERENCES code_files (id)
                )''', ()),

            ('''CREATE TABLE IF NOT EXISTS experiment_runs
                (
                    id           INT PRIMARY KEY AUTO_INCREMENT,
                    run_name     VARCHAR(255) UNIQUE NOT NULL,
                    dataset_name VARCHAR(100),
                    config       JSON,
                    metrics      JSON,
                    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_dataset (dataset_name)
                )''', ()),

            # users 表：用户认证（迭代 2）
            ('''CREATE TABLE IF NOT EXISTS users
                (
                    id            INT PRIMARY KEY AUTO_INCREMENT,
                    username      VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(128) NOT NULL,
                    email         VARCHAR(100) UNIQUE,
                    role          ENUM('user', 'admin') DEFAULT 'user',
                    last_login_at TIMESTAMP NULL,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )''', ()),

            # match_history 表：匹配历史记录（迭代 3）
            ('''CREATE TABLE IF NOT EXISTS match_history
                (
                    id         INT PRIMARY KEY AUTO_INCREMENT,
                    user_id    INT NOT NULL,
                    kp_ids     JSON NOT NULL,
                    kp_names   JSON NOT NULL,
                    params     JSON NOT NULL,
                    mode       VARCHAR(20) DEFAULT 'list',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )''', ()),

            # favorites 表：用户收藏（迭代 3）
            ('''CREATE TABLE IF NOT EXISTS favorites
                (
                    id         INT PRIMARY KEY AUTO_INCREMENT,
                    user_id    INT NOT NULL,
                    snippet_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (snippet_id) REFERENCES code_snippets(id) ON DELETE CASCADE,
                    UNIQUE KEY uk_user_snippet (user_id, snippet_id)
                )''', ())
        ]

        # 索引创建语句（性能优化）
        # 注意：使用单独的 ALTER TABLE 语句，避免重复索引错误
        index_statements = [
            # FULLTEXT 索引：用于 keywords 字段的全文搜索
            # 注意：FULLTEXT 索引需要 InnoDB 引擎（MySQL 5.6+）
            ('''CREATE FULLTEXT INDEX idx_snippets_keywords
                ON code_snippets(keywords)''', 'idx_snippets_keywords'),

            # 普通索引：file_id 外键索引（虽然外键自带索引，但显式定义更清晰）
            ('''CREATE INDEX idx_snippets_file_id
                ON code_snippets(file_id)''', 'idx_snippets_file_id'),

            # 复合索引：file_id + complexity_score（用于按文件和难度筛选）
            ('''CREATE INDEX idx_snippets_file_complexity
                ON code_snippets(file_id, complexity_score)''', 'idx_snippets_file_complexity'),

            # match_history: 用户+时间复合索引（历史记录分页查询）
            ('''CREATE INDEX idx_match_history_user_created
                ON match_history(user_id, created_at DESC)''', 'idx_match_history_user_created'),

            # favorites: 用户+时间复合索引（收藏列表分页查询）
            ('''CREATE INDEX idx_favorites_user_created
                ON favorites(user_id, created_at DESC)''', 'idx_favorites_user_created'),

            # 哈希索引：用于幂等导入检查（已在表定义中定义为 UNIQUE，此处可选）
            # ('''CREATE INDEX idx_content_hash
            #     ON code_snippets(content_hash)''', 'idx_content_hash'),
        ]

        try:
            # 使用基类方法获取客户端
            client = self._get_client()
            client.execute_transaction(statements)
            print("[DB Init] 所有数据表结构已初始化/验证。")

            # 创建索引（跳过已存在的索引）
            print("[DB Init] 开始创建/验证索引...")
            for idx_sql, idx_name in index_statements:
                try:
                    client.execute(idx_sql)
                    print(f"[DB Init] 索引 '{idx_name}' 已创建/验证。")
                except Exception as e:
                    # MySQL 错误 1061: Duplicate key name (索引已存在)
                    if "Duplicate key name" in str(e) or "1061" in str(e):
                        print(f"[DB Init] 索引 '{idx_name}' 已存在，跳过。")
                    else:
                        print(f"[DB Init-Warning] 创建索引 '{idx_name}' 时出现问题: {e}")
                        # 不抛出异常，索引创建失败不应阻止系统启动

            print("[DB Init] 数据库初始化完成（表+索引）。")
        except Exception as e:
            print(f"[DB Init-Error] 创建数据表时失败: {e}")
            raise

# 方便外部直接调用（保持向后兼容）
def init_db(db_name=None):
    initializer = DatabaseInitializer(db_name)
    initializer.init_db()
