import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.role import RoleRepository
from app.models.function import FunctionRepository
from app.models.role_function import RoleFunctionRepository
from app.models.menu import MenuRepository

class RoleManagementHandler(BaseHandler):
    """角色管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/role_management.html", title="角色管理", username=self.current_user)

class RoleListApiHandler(BaseHandler):
    """角色列表API"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        
        roles = RoleRepository.get_all_roles()
        self.write(json.dumps({
            "data": [dict(role) for role in roles],
            "total": len(roles),
            "page": page,
            "page_size": page_size
        }))

class RoleCreateApiHandler(BaseHandler):
    """创建角色API"""
    @tornado.web.authenticated
    def post(self):
        name = self.get_argument("name", "")
        code = self.get_argument("code", "")
        description = self.get_argument("description", "")
        
        if not name or not code:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "角色名称和编码不能为空"}))
            return
        
        if RoleRepository.create_role(name, code, description):
            self.write(json.dumps({"success": True, "message": "角色创建成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "角色编码已存在"}))

class RoleUpdateApiHandler(BaseHandler):
    """更新角色API"""
    @tornado.web.authenticated
    def post(self):
        role_id = self.get_argument("role_id", "")
        name = self.get_argument("name", "")
        code = self.get_argument("code", "")
        description = self.get_argument("description", "")
        status = self.get_argument("status", "")
        
        # 系统管理员角色不允许编辑
        role = RoleRepository.get_role_by_id(int(role_id))
        if role and role.get("code") == "admin":
            self.set_status(403)
            self.write(json.dumps({"success": False, "message": "系统管理员角色不允许修改"}))
            return
        
        updates = {}
        if name:
            updates["name"] = name
        if code:
            updates["code"] = code
        if description:
            updates["description"] = description
        if status:
            updates["status"] = int(status)
        
        if RoleRepository.update_role(int(role_id), **updates):
            self.write(json.dumps({"success": True, "message": "角色更新成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "更新失败"}))


class RoleGetApiHandler(BaseHandler):
    """获取单个角色API（用于编辑弹窗回填）"""
    @tornado.web.authenticated
    def get(self):
        role_id = self.get_argument("role_id", "")
        if not role_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "角色ID不能为空"}))
            return
        
        role = RoleRepository.get_role_by_id(int(role_id))
        if not role:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "角色不存在"}))
            return
        
        self.write(json.dumps({"success": True, "data": dict(role)}))

class RoleDeleteApiHandler(BaseHandler):
    """删除角色API"""
    @tornado.web.authenticated
    def post(self):
        role_id = self.get_argument("role_id", "")
        
        # 系统管理员角色不允许删除
        role = RoleRepository.get_role_by_id(int(role_id))
        if role and role.get("code") == "admin":
            self.set_status(403)
            self.write(json.dumps({"success": False, "message": "系统管理员角色不允许删除"}))
            return
        
        if RoleRepository.delete_role(int(role_id)):
            self.write(json.dumps({"success": True, "message": "角色删除成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "删除失败"}))

class RoleFunctionsApiHandler(BaseHandler):
    """获取角色已分配的功能ID列表API"""
    @tornado.web.authenticated
    def get(self):
        role_id = self.get_argument("role_id", "")
        if not role_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "角色ID不能为空"}))
            return
        
        func_ids = RoleFunctionRepository.get_functions_by_role(int(role_id))
        self.write(json.dumps({
            "success": True,
            "data": func_ids
        }))


class RoleFunctionsSaveApiHandler(BaseHandler):
    """保存角色功能分配API（自动同步菜单）"""
    @tornado.web.authenticated
    def post(self):
        role_id = self.get_argument("role_id", "")
        func_ids_str = self.get_argument("func_ids", "")
        
        if not role_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "角色ID不能为空"}))
            return
        
        role_id = int(role_id)
        func_ids = [int(x) for x in func_ids_str.split(",") if x.strip()]
        
        # 保存角色-功能关联
        RoleFunctionRepository.set_role_functions(role_id, func_ids)
        
        # 自动同步菜单：为当前角色已分配的功能自动创建菜单（如不存在）
        existing_menus = MenuRepository.get_menus_by_role(role_id)
        existing_func_ids = set(m["func_id"] for m in existing_menus)
        
        for i, func_id in enumerate(func_ids):
            if func_id not in existing_func_ids:
                MenuRepository.create_menu(role_id, func_id, (i + 1) * 10)
        
        self.write(json.dumps({"success": True, "message": "功能分配保存成功，菜单已自动同步"}))
