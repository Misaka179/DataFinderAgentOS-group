"""API 接口管理 — 控制器"""

import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.api_interface import ApiInterfaceRepository


class ApiInterfaceManagementHandler(BaseHandler):
    """接口管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/api_interface.html", title="接口管理", username=self.current_user)


class ApiInterfaceListApiHandler(BaseHandler):
    """接口列表API"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", "")
        status = self.get_argument("status", "")

        status = int(status) if status else None
        result = ApiInterfaceRepository.get_all(page, page_size, search if search else None, status)
        self.write(json.dumps(result, ensure_ascii=False))


class ApiInterfaceGetApiHandler(BaseHandler):
    """获取接口详情API"""
    @tornado.web.authenticated
    def get(self):
        interface_id = self.get_argument("id", "")
        if not interface_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        item = ApiInterfaceRepository.get_by_id(int(interface_id))
        if item:
            self.write(json.dumps({"success": True, "data": item}))
        else:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "接口不存在"}))


class ApiInterfaceEnabledListApiHandler(BaseHandler):
    """获取启用接口列表（供数字员工选择用）"""
    @tornado.web.authenticated
    def get(self):
        items = ApiInterfaceRepository.get_enabled_list()
        self.write(json.dumps({"success": True, "data": items}))


class ApiInterfaceCreateApiHandler(BaseHandler):
    """创建接口API"""
    @tornado.web.authenticated
    def post(self):
        name = self.get_argument("name", "").strip()
        code = self.get_argument("code", "").strip()
        description = self.get_argument("description", "").strip()
        method = self.get_argument("method", "GET").strip().upper()
        url = self.get_argument("url", "").strip()
        headers = self.get_argument("headers", "{}")
        params = self.get_argument("params", "{}")
        status = int(self.get_argument("status", 1))

        if not name or not code:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "名称和编码不能为空"}))
            return

        # 校验 JSON
        for field_name, val in [("headers", headers), ("params", params)]:
            try:
                if isinstance(val, str):
                    json.loads(val)
            except json.JSONDecodeError:
                self.set_status(400)
                self.write(json.dumps({"success": False, "message": f"{field_name} 格式错误，需为JSON"}))
                return

        item_id, err = ApiInterfaceRepository.create(name, code, description, method, url, headers, params, status)
        if item_id:
            self.write(json.dumps({"success": True, "message": "创建成功", "id": item_id}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": err or "创建失败"}))


class ApiInterfaceUpdateApiHandler(BaseHandler):
    """更新接口API"""
    @tornado.web.authenticated
    def post(self):
        interface_id = self.get_argument("id", "")
        name = self.get_argument("name", "").strip()
        code = self.get_argument("code", "").strip()
        description = self.get_argument("description", "").strip()
        method = self.get_argument("method", "GET").strip().upper()
        url = self.get_argument("url", "").strip()
        headers = self.get_argument("headers", "{}")
        params = self.get_argument("params", "{}")
        status = int(self.get_argument("status", 1))

        if not interface_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return

        # 校验 JSON
        for field_name, val in [("headers", headers), ("params", params)]:
            try:
                if isinstance(val, str) and val.strip():
                    json.loads(val)
            except json.JSONDecodeError:
                self.set_status(400)
                self.write(json.dumps({"success": False, "message": f"{field_name} 格式错误，需为JSON"}))
                return

        ok, err = ApiInterfaceRepository.update(
            int(interface_id), name, code, description, method, url, headers, params, status
        )
        if ok:
            self.write(json.dumps({"success": True, "message": "更新成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": err or "更新失败"}))


class ApiInterfaceDeleteApiHandler(BaseHandler):
    """删除接口API"""
    @tornado.web.authenticated
    def post(self):
        interface_id = self.get_argument("id", "")
        if not interface_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        if ApiInterfaceRepository.delete(int(interface_id)):
            self.write(json.dumps({"success": True, "message": "删除成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "删除失败"}))


class ApiInterfaceToggleApiHandler(BaseHandler):
    """切换接口状态API"""
    @tornado.web.authenticated
    def post(self):
        interface_id = self.get_argument("id", "")
        if not interface_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        new_status = ApiInterfaceRepository.toggle_status(int(interface_id))
        if new_status is not None:
            self.write(json.dumps({"success": True, "message": "状态已更新", "status": new_status}))
        else:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "接口不存在"}))
