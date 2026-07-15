import sqlite3
from app.models.db import get_connection

class MenuRepository:
    """菜单数据访问类"""
    
    @staticmethod
    def get_menus_by_role(role_id):
        """根据角色ID获取菜单（含功能信息）"""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.*, f.name as func_name, f.icon as func_icon,
                       f.route as func_route, f.parent_id as func_parent_id
                FROM menus m
                JOIN functions f ON m.func_id = f.id
                WHERE m.role_id = ? AND f.status = 1
                ORDER BY f.parent_id, m.sort_order
                """,
                (role_id,)
            ).fetchall()
            return rows
    
    @staticmethod
    def get_all_menus():
        """获取所有菜单"""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.*, r.name as role_name, f.name as func_name,
                       f.parent_id as func_parent_id
                FROM menus m
                JOIN roles r ON m.role_id = r.id
                JOIN functions f ON m.func_id = f.id
                ORDER BY m.role_id, f.parent_id, m.sort_order
                """
            ).fetchall()
            return rows
    
    @staticmethod
    def get_menu_by_id(menu_id):
        """根据ID获取菜单"""
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT m.*, r.name as role_name, f.name as func_name
                FROM menus m
                JOIN roles r ON m.role_id = r.id
                JOIN functions f ON m.func_id = f.id
                WHERE m.id = ?
                """,
                (menu_id,)
            ).fetchone()
            return row
    
    @staticmethod
    def create_menu(role_id, func_id, sort_order):
        """创建菜单"""
        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                    (role_id, func_id, sort_order)
                )
                return True
        except sqlite3.IntegrityError:
            return False
    
    @staticmethod
    def update_menu(menu_id, sort_order):
        """更新菜单排序"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE menus SET sort_order=?, updated_at=datetime('now', 'localtime') WHERE id=?",
                (sort_order, menu_id)
            )
            return True
    
    @staticmethod
    def delete_menu(menu_id):
        """删除菜单"""
        with get_connection() as conn:
            conn.execute("DELETE FROM menus WHERE id=?", (menu_id,))
            return True
    
    @staticmethod
    def disable_menu(menu_id):
        """禁用菜单"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE menus SET status=0, updated_at=datetime('now', 'localtime') WHERE id=?",
                (menu_id,)
            )
            return True
    
    @staticmethod
    def enable_menu(menu_id):
        """启用菜单"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE menus SET status=1, updated_at=datetime('now', 'localtime') WHERE id=?",
                (menu_id,)
            )
            return True
    
    @staticmethod
    def delete_menus_by_role(role_id):
        """删除角色的所有菜单"""
        with get_connection() as conn:
            conn.execute("DELETE FROM menus WHERE role_id=?", (role_id,))
            return True

    @staticmethod
    def build_menu_tree(menus, current_path=None):
        """将扁平的菜单列表构建为树形结构（parent→children）
        
        Args:
            menus: 菜单列表（含 func_parent_id, func_route 等字段）
            current_path: 当前请求路径，用于标记激活状态
        """
        parents = [m for m in menus if m.get("func_parent_id") == 0]
        tree = []
        for parent in parents:
            item = dict(parent)
            children = [m for m in menus if m.get("func_parent_id") == parent["func_id"]]
            item["children"] = children
            # 标记是否有子菜单匹配当前路径（用于展开父菜单）
            item["has_active_child"] = bool(
                current_path and any(c.get("func_route") == current_path for c in children)
            )
            tree.append(item)
        return tree
