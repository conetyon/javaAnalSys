# src/services/knowledge_service.py
"""
知识点服务层
封装知识点相关的业务逻辑，供 API 和离线任务共用
"""
from typing import List, Dict, Any, Optional

from src.db_manager import KnowledgePointManager
from lib.client.db import MySQLClient
import config


class KnowledgeService:
    """知识点业务服务"""

    def __init__(self, db_name: str = None):
        self.db_name = db_name or config.DB_NAME
        self.kp_mgr = KnowledgePointManager(self.db_name)

    def get_tree(self) -> List[Dict[str, Any]]:
        """
        获取知识点树状结构
        :return: 树状结构列表
        """
        # 使用递归 CTE 查询获取层级数据
        sql = """
            WITH RECURSIVE KnowledgeHierarchy AS (
                SELECT id, name, parent_id, level, CAST(id AS CHAR(1000)) AS sort_path
                FROM knowledge_points
                WHERE parent_id IS NULL
                UNION ALL
                SELECT kp.id, kp.name, kp.parent_id, kp.level, CONCAT(kh.sort_path, '/', kp.id)
                FROM knowledge_points AS kp
                JOIN KnowledgeHierarchy AS kh ON kp.parent_id = kh.id
            )
            SELECT id, name, parent_id, level
            FROM KnowledgeHierarchy
            ORDER BY sort_path;
        """

        with MySQLClient(db=self.db_name) as client:
            cursor = client._conn.cursor()
            cursor.execute(sql)

            # 获取列名
            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchall()

            # 转换为字典列表
            flat_list = []
            for row in raw_rows:
                if isinstance(row, dict):
                    flat_list.append(row)
                else:
                    flat_list.append(dict(zip(columns, row)))

            cursor.close()

        # 转换为树状结构
        return self._list_to_tree(flat_list)

    def get_flat_list(self) -> List[Dict[str, Any]]:
        """
        获取知识点扁平列表
        :return: 扁平列表
        """
        sql = """
            SELECT id, name, parent_id, level, keywords, ast_template
            FROM knowledge_points
            ORDER BY id;
        """

        with MySQLClient(db=self.db_name) as client:
            cursor = client._conn.cursor()
            cursor.execute(sql)

            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchall()

            result = []
            for row in raw_rows:
                if isinstance(row, dict):
                    result.append(row)
                else:
                    result.append(dict(zip(columns, row)))

            cursor.close()

        return result

    def get_by_id(self, kp_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取单个知识点
        :param kp_id: 知识点 ID
        :return: 知识点详情或 None
        """
        return self.kp_mgr.get_by_id(kp_id)

    def get_children(self, parent_id: int) -> List[Dict[str, Any]]:
        """
        获取指定知识点的子节点
        :param parent_id: 父节点 ID
        :return: 子节点列表
        """
        sql = """
            SELECT id, name, parent_id, level, keywords
            FROM knowledge_points
            WHERE parent_id = %s
            ORDER BY id;
        """

        with MySQLClient(db=self.db_name) as client:
            cursor = client._conn.cursor()
            cursor.execute(sql, (parent_id,))

            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchall()

            result = []
            for row in raw_rows:
                if isinstance(row, dict):
                    result.append(row)
                else:
                    result.append(dict(zip(columns, row)))

            cursor.close()

        return result

    @staticmethod
    def _list_to_tree(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将扁平列表转换为树状结构
        :param data: 扁平列表
        :return: 树状结构
        """
        if not data:
            return []

        # 建立 id -> node 的映射
        node_map = {item['id']: item for item in data}

        for node in node_map.values():
            node['children'] = []
            # 前端组件适配字段
            node['title'] = node['name']
            node['key'] = node['id']

        tree = []
        for node in node_map.values():
            parent_id = node['parent_id']
            if parent_id is not None and parent_id in node_map:
                parent_node = node_map[parent_id]
                parent_node['children'].append(node)
            else:
                tree.append(node)

        return tree
