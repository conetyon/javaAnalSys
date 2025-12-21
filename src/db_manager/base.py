# db_manager/base.py
from lib.client.db import MySQLClient
import config

DEFAULT_DB_NAME = config.DB_NAME

class BaseManager:
    """
    所有数据库管理类的基类。
    负责管理数据库名称配置和客户端实例化。
    """
    def __init__(self, db_name: str = None):
        # 允许外部注入 db_name，如果未注入则使用默认值
        self.db_name = db_name or DEFAULT_DB_NAME

    def _get_client(self, autocommit: bool = True) -> MySQLClient:
        """
        获取一个配置好的 MySQLClient 实例。
        :param autocommit: 是否自动提交事务
        """
        return MySQLClient(db=self.db_name, autocommit=autocommit)
