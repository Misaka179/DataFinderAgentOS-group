import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.db import get_connection


class IndexHandler(BaseHandler):
    """用户侧首页 - 重定向到智能问数对话页面"""
    @tornado.web.authenticated
    def get(self):
        self.redirect("/chat")


class DashboardStatsApiHandler(BaseHandler):
    """控制台统计数据API（用于前端实时刷新）"""
    @tornado.web.authenticated
    def get(self):
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
        self.write(json.dumps({"success": True, "data": stats}))


class AdminIndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        # 从数据库查询实时统计数据
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

        self.render("admin/index.html", title="后台管理", username=self.current_user, stats=stats)
