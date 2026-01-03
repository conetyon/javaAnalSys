# db_manager/knowledge_point_manager.py
from .base import BaseManager
from lib.globals import core_logger as log

class KnowledgePointManager(BaseManager):
    """
    负责知识点(knowledge_points)的数据库操作与模板解析。
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
            log.error(f"未找到 SQL 文件: {sql_file}")
            return
        except Exception as e:
            log.error(f"读取 SQL 文件失败: {e}")
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
            log.warning("SQL 文件为空或仅包含注释")
            return

        # 事务执行所有语句
        with self._get_client(autocommit=False) as tx:
            try:
                for stmt in statements:
                    tx.execute(stmt)
            except Exception as e:
                # 出错后由 __exit__ 自动回滚
                log.error(f"执行 SQL 脚本失败，将回滚。错误: {e}")
                raise

        log.info("预置知识点 SQL 脚本执行成功并已提交")

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
            log.info("数据库中没有知识点数据")
            return

        log.info("--- 知识点层级结构 ---")
        for node in nodes:
            indent = "    " * node['depth']
            log.info(f"{indent}- {node['name']} (ID: {node['id']}, Level: {node['level']})")

    def get_by_id(self, kp_id: int):
        """
        根据 ID 获取单个知识点详情
        供 Matcher 使用
        """
        log.debug("[KnowledgePointManager.get_by_id] 查询知识点: kp_id=%d", kp_id)
        sql = "SELECT * FROM knowledge_points WHERE id=%s"
        client = self._get_client()
        result = client.fetch_one(sql, (kp_id,))
        if result:
            log.debug("[KnowledgePointManager.get_by_id] 找到知识点: id=%d, name=%s", 
                      kp_id, result.get("name", "N/A"))
        else:
            log.warning("[KnowledgePointManager.get_by_id] 知识点不存在: kp_id=%d", kp_id)
        return result

    def display_tree(self):
        """辅助打印方法"""
        nodes = self.get_tree_structure()
        if not nodes:
            log.info("数据库中没有知识点数据")
            return
        log.info("--- 知识点层级结构 ---")
        for node in nodes:
            indent = "    " * node['depth']
            log.info(f"{indent}- {node['name']} (ID: {node['id']})")

    # === 新增：解析知识点配置（安全读取 JSON 字段） ===
    def parse_kp_config(self, kp_row: dict) -> dict:
        """
        将 knowledge_points 数据行解析为匹配需要的配置结构。

        预期字段：
            - name: 知识点名称
            - ast_template: JSON 字符串，包含 { template, required_nodes, details }
            - keywords: JSON 字符串或逗号/空格分隔字符串
            - difficulty 或 target_difficulty: 目标难度（可选）

        返回：
            {
                "name": str,
                "ast": dict,               # 原始 AST 模板字典
                "required_nodes": list,    # 解析后的 AST 节点（小写）
                "details": list,           # 解析后的补充节点（小写）
                "keywords": list,          # 解析后的关键词（小写）
                "target_difficulty": float 或 None,
            }
        """
        from src.matching.utils import safe_read_json
        import re

        kp_id = (kp_row or {}).get("id", "N/A")
        name = (kp_row or {}).get("name") or ""
        
        log.debug("[KnowledgePointManager.parse_kp_config] 开始解析知识点配置: id=%s, name=%s", kp_id, name)

        # 解析 ast_template
        raw_ast = (kp_row or {}).get("ast_template")
        log.debug("[KnowledgePointManager.parse_kp_config] 原始 ast_template: %s", raw_ast)
        ast_tpl = safe_read_json(raw_ast, default={})
        required_nodes = ast_tpl.get("required_nodes") or ast_tpl.get("template_nodes") or []
        details = ast_tpl.get("details") or []

        # 解析 keywords（支持 JSON 或简单字符串）
        raw_kws = (kp_row or {}).get("keywords")
        log.debug("[KnowledgePointManager.parse_kp_config] 原始 keywords: %s", raw_kws)
        kws = []
        parsed_kws = safe_read_json(raw_kws, default=None) if isinstance(raw_kws, (str, bytes, bytearray)) else None
        if isinstance(parsed_kws, list):
            kws = parsed_kws
        elif isinstance(raw_kws, str):
            # 尝试按非字母数字分隔符切分
            kws = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", raw_kws)
        elif isinstance(raw_kws, (list, set, tuple)):
            kws = list(raw_kws)

        # 解析难度（可选列名兼容）
        target_diff = kp_row.get("target_difficulty")
        if target_diff is None:
            target_diff = kp_row.get("difficulty")

        # 统一为小写、去重
        def _norm_list(x):
            return sorted({str(t).strip().lower() for t in (x or []) if str(t).strip()})

        result = {
            "name": name,
            "ast": ast_tpl,
            "required_nodes": _norm_list(required_nodes),
            "details": _norm_list(details),
            "keywords": _norm_list(kws),
            "target_difficulty": float(target_diff) if target_diff is not None else None,
        }
        
        log.info("[KnowledgePointManager.parse_kp_config] 解析完成: name=%s, required_nodes=%s, keywords=%s, target_diff=%s",
                 name, result["required_nodes"], result["keywords"], result["target_difficulty"])
        
        return result
