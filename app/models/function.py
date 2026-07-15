import sqlite3
from app.models.db import get_connection

class FunctionRepository:
    """功能数据访问类"""
    
    @staticmethod
    def get_all_functions():
        """获取所有功能（一级在前，按排序）"""
        with get_connection() as conn:
            return conn.execute("SELECT * FROM functions ORDER BY parent_id, sort_order, id").fetchall()
    
    @staticmethod
    def get_parent_functions():
        """获取所有一级功能（parent_id=0）"""
        with get_connection() as conn:
            return conn.execute("SELECT * FROM functions WHERE parent_id=0 ORDER BY sort_order").fetchall()
    
    @staticmethod
    def get_child_functions(parent_id):
        """获取指定父功能下的所有子功能"""
        with get_connection() as conn:
            return conn.execute("SELECT * FROM functions WHERE parent_id=? ORDER BY sort_order", (parent_id,)).fetchall()
    
    @staticmethod
    def get_function_by_id(func_id):
        """根据ID获取功能"""
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM functions WHERE id=?", (func_id,)).fetchone()
            return row
    
    @staticmethod
    def create_function(name, code, icon, route, sort_order, parent_id=0, status=1):
        """创建功能"""
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, code, icon, route, sort_order, parent_id, status)
                )
                return True
        except sqlite3.IntegrityError:
            return False
    
    @staticmethod
    def update_function(func_id, name, code, icon, route, sort_order, parent_id, status):
        """更新功能"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE functions SET name=?, code=?, icon=?, route=?, sort_order=?, parent_id=?, status=?, updated_at=datetime('now', 'localtime') WHERE id=?",
                (name, code, icon, route, sort_order, parent_id, status, func_id)
            )
            return True
    
    @staticmethod
    def delete_function(func_id):
        """删除功能"""
        with get_connection() as conn:
            conn.execute("DELETE FROM functions WHERE id=?", (func_id,))
            # 同时删除其子功能
            conn.execute("DELETE FROM functions WHERE parent_id=?", (func_id,))
            return True
    
    @staticmethod
    def disable_function(func_id):
        """禁用功能"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE functions SET status=0, updated_at=datetime('now', 'localtime') WHERE id=?",
                (func_id,)
            )
            return True
    
    @staticmethod
    def enable_function(func_id):
        """启用功能"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE functions SET status=1, updated_at=datetime('now', 'localtime') WHERE id=?",
                (func_id,)
            )
            return True
    
    @staticmethod
    def get_enabled_functions():
        """获取所有启用的功能"""
        with get_connection() as conn:
            return conn.execute("SELECT * FROM functions WHERE status=1 ORDER BY sort_order, id").fetchall()
