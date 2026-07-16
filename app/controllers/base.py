import tornado.web

from app.models.user import UserRepository
from app.models.menu import MenuRepository
from app.models.function import FunctionRepository
from app.models.db import get_connection


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        username = self.get_secure_cookie("username")
        if not username:
            return None
        return username.decode("utf-8")

    @staticmethod
    def get_base_stats():
        """提取公共统计查询 - 被 DashboardStatsApiHandler 和 AdminIndexHandler 共用"""
        stats = {}
        try:
            with get_connection() as conn:
                stats["user_count"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
                stats["data_count"] = conn.execute("SELECT COUNT(*) FROM data_warehouse").fetchone()[0] or 0
                stats["task_count"] = conn.execute("SELECT COUNT(*) FROM deep_collect_tasks").fetchone()[0] or 0
                stats["model_count"] = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0] or 0
                stats["watch_count"] = conn.execute("SELECT COUNT(*) FROM watch_sources").fetchone()[0] or 0
                stats["de_count"] = conn.execute("SELECT COUNT(*) FROM digital_employees").fetchone()[0] or 0
                stats["today_task_count"] = conn.execute(
                    "SELECT COUNT(*) FROM deep_collect_tasks WHERE date(started_at)=date('now')"
                ).fetchone()[0] or 0
                stats["deep_count"] = conn.execute(
                    "SELECT COUNT(*) FROM data_warehouse WHERE is_deep_collected=1"
                ).fetchone()[0] or 0
        except Exception:
            stats = {"user_count":0, "data_count":0, "task_count":0, "model_count":0,
                     "watch_count":0, "de_count":0, "today_task_count":0, "deep_count":0}
        return stats

    def get_user_info(self):
        """获取当前登录用户的完整信息（含角色和菜单权限），同次请求结果缓存在 _user_info 中"""
        if hasattr(self, '_user_info'):
            return self._user_info
        username = self.current_user
        if not username:
            self._user_info = None
            return None
        user_row = UserRepository.get_user_by_username(username)
        if not user_row:
            self._user_info = None
            return None
        user_info = dict(user_row)
        # 查询该角色对应的菜单（含功能信息），构建树形结构
        menus = MenuRepository.get_menus_by_role(user_info["role_id"])
        menu_list = [dict(m) for m in menus]

        # 自动补全缺失的父功能：子菜单引用了父功能但父功能不在菜单列表中时，从 functions 表获取
        child_parent_ids = set(m["func_parent_id"] for m in menu_list if m["func_parent_id"] > 0)
        parent_ids_in_menus = set(m["func_id"] for m in menu_list if m["func_parent_id"] == 0)
        missing_parent_ids = child_parent_ids - parent_ids_in_menus
        if missing_parent_ids:
            # 使用已有的 sort_order 最大值，让父功能排在前面
            max_sort = max((m.get("sort_order", 0) or 0) for m in menu_list) if menu_list else 0
            for pid in sorted(missing_parent_ids):
                parent_func = FunctionRepository.get_function_by_id(pid)
                if parent_func:
                    parent_func = dict(parent_func)
                    max_sort += 1
                    virtual_menu = {
                        "id": 0,
                        "role_id": user_info["role_id"],
                        "func_id": parent_func["id"],
                        "sort_order": max_sort,
                        "status": 1,
                        "func_name": parent_func["name"],
                        "func_icon": parent_func["icon"],
                        "func_route": parent_func["route"],
                        "func_parent_id": parent_func["parent_id"],
                    }
                    menu_list.append(virtual_menu)

        user_info["menus"] = menu_list
        user_info["menu_tree"] = MenuRepository.build_menu_tree(menu_list, self.request.path)
        self._user_info = user_info
        return user_info

    def render(self, template_name, **kwargs):
        if "user_info" not in kwargs:
            kwargs["user_info"] = self.get_user_info()
        super().render(template_name, **kwargs)
