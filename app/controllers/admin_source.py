import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.watch_source import WatchSourceRepository


class SourceManagementHandler(BaseHandler):
    """瞭源管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/source_management.html", title="瞭源管理", username=self.current_user)


class SourceListApiHandler(BaseHandler):
    """瞭源列表API"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", "")
        status = self.get_argument("status", "")

        if not search:
            search = None
        if not status:
            status = None
        else:
            status = int(status)

        result = WatchSourceRepository.get_all(page, page_size, search, status)
        self.write(json.dumps(result, ensure_ascii=False))


class SourceGetApiHandler(BaseHandler):
    """获取瞭源详情API"""
    @tornado.web.authenticated
    def get(self):
        source_id = self.get_argument("source_id", "")
        if not source_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "瞭源ID不能为空"}))
            return

        source = WatchSourceRepository.get_by_id(int(source_id))
        if source:
            self.write(json.dumps({"success": True, "data": source}))
        else:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "瞭源不存在"}))


class SourceCreateApiHandler(BaseHandler):
    """创建瞭源API"""
    @tornado.web.authenticated
    def post(self):
        name = self.get_argument("name", "")
        url_template = self.get_argument("url_template", "")
        method = self.get_argument("method", "GET")
        headers = self.get_argument("headers", "{}")
        keyword_param = self.get_argument("keyword_param", "word")
        page_param = self.get_argument("page_param", "pn")
        page_step = int(self.get_argument("page_step", 10))
        source_type = self.get_argument("source_type", "baidu_news")

        if not name or not url_template:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "名称和URL模板不能为空"}))
            return

        # URL模板合法性校验
        if "://" not in url_template:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "URL模板格式无效，需包含协议头（如 https://）"}))
            return

        # 尝试解析headers为JSON
        try:
            if isinstance(headers, str):
                json.loads(headers)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "Headers格式错误，需为JSON格式"}))
            return

        if WatchSourceRepository.create(name, url_template, method, headers, keyword_param, page_param, page_step, source_type):
            self.write(json.dumps({"success": True, "message": "瞭源创建成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "瞭源创建失败"}))


class SourceUpdateApiHandler(BaseHandler):
    """更新瞭源API"""
    @tornado.web.authenticated
    def post(self):
        source_id = self.get_argument("source_id", "")
        name = self.get_argument("name", "")
        url_template = self.get_argument("url_template", "")
        method = self.get_argument("method", "")
        headers = self.get_argument("headers", "")
        keyword_param = self.get_argument("keyword_param", "")
        page_param = self.get_argument("page_param", "")
        page_step = self.get_argument("page_step", "")
        status = self.get_argument("status", "")
        source_type = self.get_argument("source_type", "")

        updates = {}
        if name:
            updates["name"] = name
        if url_template:
            updates["url_template"] = url_template
        if method:
            updates["method"] = method
        if headers:
            try:
                if isinstance(headers, str):
                    json.loads(headers)
            except json.JSONDecodeError:
                self.set_status(400)
                self.write(json.dumps({"success": False, "message": "Headers格式错误"}))
                return
            updates["headers"] = headers
        if keyword_param:
            updates["keyword_param"] = keyword_param
        if page_param:
            updates["page_param"] = page_param
        if page_step:
            updates["page_step"] = int(page_step)
        if status:
            updates["status"] = int(status)
        if source_type:
            updates["source_type"] = source_type

        if WatchSourceRepository.update(int(source_id), **updates):
            self.write(json.dumps({"success": True, "message": "瞭源更新成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "瞭源更新失败"}))


class SourceDeleteApiHandler(BaseHandler):
    """删除瞭源API"""
    @tornado.web.authenticated
    def post(self):
        source_id = self.get_argument("source_id", "")
        if WatchSourceRepository.delete(int(source_id)):
            self.write(json.dumps({"success": True, "message": "瞭源删除成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "瞭源删除失败"}))


class SourceActiveListApiHandler(BaseHandler):
    """获取所有启用的瞭源列表（供瞭望管理使用）"""
    @tornado.web.authenticated
    def get(self):
        sources = WatchSourceRepository.get_all_active()
        self.write(json.dumps({"success": True, "data": sources}))
