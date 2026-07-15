import tornado.web

from app.controllers.base import BaseHandler

class IndexHandler(BaseHandler):
    """用户侧首页 - 重定向到智能问数对话页面"""
    @tornado.web.authenticated
    def get(self):
        self.redirect("/chat")

class AdminIndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("admin/index.html", title="后台管理", username=self.current_user)
