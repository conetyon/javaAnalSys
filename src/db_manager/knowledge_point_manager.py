# db_manager/knowledge_point_manager.py
from .base import BaseManager

class KnowledgePointManager(BaseManager):
    """
    负责知识点(knowledge_points)的数据库操作。
    """

    def insert_baseline_data(self):
        """插入预置知识点。"""
        points = [
            (1, "Java", None, 0, '{}', '["java"]'),
            (10, "Java 基础", 1, 1, '{}', '["basics"]'),
            (20, "集合框架", 1, 1, '{}', '["jcf", "java collection framework", "data structures"]'),
            (101, "数据类型", 10, 2, '{"template": "PrimitiveType", "details": ["int", "double", "boolean"]}',
             '["primitive types", "variables", "int", "char"]'),
            (102, "流程控制", 10, 2, '{}', '["control flow", "if", "else", "switch"]'),
            (1021, "条件语句", 102, 3, '{"template": "IfStatement"}', '["if-else", "conditional"]'),
            (1022, "循环语句", 102, 3, '{"template": "ForStatement"}', '["for", "while", "loop", "iteration"]'),
            (201, "List", 20, 2, '{"template": "Declare<List>"}', '["list", "arraylist", "linkedlist", "ordered"]'),
            (202, "Set", 20, 2, '{"template": "Declare<Set>"}', '["set"]')
        ]
        sql = "INSERT IGNORE INTO knowledge_points (id, name, parent_id, level, ast_template, keywords) VALUES (%s, %s, %s, %s, %s, %s)"

        with self._get_client(autocommit=False) as tx:
            cursor = tx._conn.cursor()
            cursor.executemany(sql, points)
            cursor.close()
        print("[Knowledge Manager] 预置知识点数据已插入。")

    def get_tree_structure(self) -> list:
        """
        获取知识点树状结构数据。
        :return: 包含 depth, sort_path 等信息的字典列表
        """
        recursive_query = """
            WITH RECURSIVE KnowledgeHierarchy AS (
                SELECT id, name, parent_id, level, 0 AS depth, CAST(id AS CHAR(1000)) AS sort_path 
                FROM knowledge_points WHERE parent_id IS NULL 
                UNION ALL 
                SELECT kp.id, kp.name, kp.parent_id, kp.level, kh.depth + 1, CONCAT(kh.sort_path, '/', kp.id) 
                FROM knowledge_points AS kp JOIN KnowledgeHierarchy AS kh ON kp.parent_id = kh.id
            )
            SELECT id, name, parent_id, level, depth FROM KnowledgeHierarchy ORDER BY sort_path;
        """
        client = self._get_client()
        return client.fetch_all(recursive_query)

    def print_tree(self):
        """在控制台打印知识点树（辅助功能）。"""
        nodes = self.get_tree_structure()
        if not nodes:
            print("数据库中没有知识点数据。")
            return

        print("\n--- 知识点层级结构 ---")
        for node in nodes:
            indent = "    " * node['depth']
            print(f"{indent}- {node['name']} (ID: {node['id']}, Level: {node['level']})")

    def get_by_id(self, kp_id: int):
        """
        根据 ID 获取单个知识点详情
        供 Matcher 使用
        """
        sql = "SELECT * FROM knowledge_points WHERE id=%s"
        client = self._get_client()
        # client.fetch_one 返回字典
        return client.fetch_one(sql, (kp_id,))

    def display_tree(self):
        # 辅助打印方法
        nodes = self.get_tree_structure()
        if not nodes:
            print("数据库中没有知识点数据。")
            return
        print("\n--- 知识点层级结构 ---")
        for node in nodes:
            indent = "    " * node['depth']
            print(f"{indent}- {node['name']} (ID: {node['id']})")