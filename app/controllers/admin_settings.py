import json
import tornado.web

from app.controllers.base import BaseHandler
from app.config import config


class SettingsManagementHandler(BaseHandler):
    """系统设置页面"""
    @tornado.web.authenticated
    def get(self):
        settings = {
            "system_name": config.SYSTEM_NAME,
            "system_short_name": config.SYSTEM_SHORT_NAME,
            "port": config.PORT,
            "debug": config.DEBUG,
            "autoreload": config.AUTORELOAD,
            "db_path": config.DB_PATH,
            "encryption_key": config.ENCRYPTION_KEY[:10] + "****" if config.ENCRYPTION_KEY else "",
            "cookie_secret": config.COOKIE_SECRET[:10] + "****" if config.COOKIE_SECRET else "",
        }
        self.render("admin/settings.html", title="系统设置", username=self.current_user, settings=settings)


class SettingsApiHandler(BaseHandler):
    """系统设置API"""
    @tornado.web.authenticated
    def get(self):
        settings = {
            "system_name": config.SYSTEM_NAME,
            "system_short_name": config.SYSTEM_SHORT_NAME,
            "port": config.PORT,
            "debug": config.DEBUG,
            "autoreload": config.AUTORELOAD,
        }
        self.write(json.dumps({"success": True, "data": settings}))

    @tornado.web.authenticated
    def post(self):
        try:
            data = json.loads(self.request.body)
            
            system_name = data.get("system_name", config.SYSTEM_NAME)
            system_short_name = data.get("system_short_name", config.SYSTEM_SHORT_NAME)
            debug = bool(data.get("debug", False))
            autoreload = bool(data.get("autoreload", False))
            
            if system_name:
                config.SYSTEM_NAME = system_name
            if system_short_name:
                config.SYSTEM_SHORT_NAME = system_short_name
            config.DEBUG = debug
            config.AUTORELOAD = autoreload

            self.write(json.dumps({
                "success": True,
                "message": "设置保存成功（部分设置需要重启服务生效）",
                "data": {
                    "system_name": config.SYSTEM_NAME,
                    "system_short_name": config.SYSTEM_SHORT_NAME,
                    "debug": config.DEBUG,
                    "autoreload": config.AUTORELOAD,
                }
            }))
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"success": False, "message": str(e)}))