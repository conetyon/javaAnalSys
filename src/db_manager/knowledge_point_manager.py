# db_manager/knowledge_point_manager.py
from .base import BaseManager

class KnowledgePointManager(BaseManager):
    """
    负责知识点(knowledge_points)的数据库操作。
    """

    def insert_baseline_data(self):
        """插入预置知识点（从外部 SQL DML 文件执行）。"""
        # 使用 db util 执行 SQL 文件：D:\bupt-codes\graduation-design\java-ana-mvp\kp_dml.sql
        sql_file = r"D:\bupt-codes\graduation-design\java-ana-mvp\kp_dml.sql"

        try:
            # 兼容 UTF-8 BOM
            with open(sql_file, "r", encoding="utf-8-sig") as f:
                script = f.read()
        except FileNotFoundError:
            print(f"[Knowledge Manager] 未找到 SQL 文件: {sql_file}")
            return
        except Exception as e:
            print(f"[Knowledge Manager] 读取 SQL 文件失败: {e}")
            return

        # 清理注释并拆分语句（避免 multi=True 不可用的问题）
        import re
        # 去掉块注释 /* ... */
        script = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
        # 去掉行注释 --
        lines = []
        for line in script.splitlines():
            s = line.strip()
            if not s or s.startswith("--"):
                continue
            lines.append(line)
        cleaned = "\n".join(lines)

        # 以分号拆分为独立语句
        statements = [stmt.strip() for stmt in cleaned.split(";") if stmt.strip()]
        if not statements:
            print("[Knowledge Manager] SQL 文件为空或仅包含注释。")
            return

        # 事务执行所有语句
        with self._get_client(autocommit=False) as tx:
            try:
                for stmt in statements:
                    tx.execute(stmt)
            except Exception as e:
                # 出错后由 __exit__ 自动回滚
                print(f"[Knowledge Manager] 执行 SQL 脚本失败，将回滚。错误: {e}")
                raise

        print("[Knowledge Manager] 预置知识点 SQL 脚本执行成功并已提交。")

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