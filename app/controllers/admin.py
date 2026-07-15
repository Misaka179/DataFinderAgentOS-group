import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository
from app.models.role import RoleRepository
from app.models.function import FunctionRepository
from app.models.menu import MenuRepository

class AdminUserController(BaseHandler):
    """用户管理控制器"""
    
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", None)
        role_id = self.get_argument("role_id", None)
        status = self.get_argument("status", None)
        
        if role_id:
            role_id = int(role_id)
        if status:
            status = int(status)
        
        result = UserRepository.get_all_users(page=page, page_size=page_size, search=search, role_id=role_id, status=status)
        self.write({"code": 0, "msg": "success", "data": result})
    
    @tornado.web.authenticated
    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        role_id = int(self.get_argument("role_id", 2))
        status = int(self.get_argument("status", 1))
        
        if UserRepository.create_user(username, password, role_id, status):
            self.write({"code": 0, "msg": "用户创建成功"})
        else:
            self.write({"code": 1, "msg": "用户创建失败，用户名可能已存在"})
    
    @tornado.web.authenticated
    def put(self):
        user_id = int(self.get_argument("user_id"))
        username = self.get_argument("username", None)
        role_id = self.get_argument("role_id", None)
        status = self.get_argument("status", None)
        
        update_data = {}
        if username:
            update_data["username"] = username
        if role_id:
            update_data["role_id"] = int(role_id)
        if status is not None:
            update_data["status"] = int(status)
        
        if UserRepository.update_user(user_id, **update_data):
            self.write({"code": 0, "msg": "用户更新成功"})
        else:
            self.write({"code": 1, "msg": "用户更新失败"})
    
    @tornado.web.authenticated
    def delete(self):
        user_id = int(self.get_argument("user_id"))
        if UserRepository.delete_user(user_id):
            self.write({"code": 0, "msg": "用户删除成功"})
        else:
            self.write({"code": 1, "msg": "用户删除失败"})

class AdminRoleController(BaseHandler):
    """角色管理控制器"""
    
    @tornado.web.authenticated
    def get(self):
        status = self.get_argument("status", None)
        if status:
            status = int(status)
        
        roles = RoleRepository.get_all(status=status if status is not None else None)
        self.write({"code": 0, "msg": "success", "data": roles})
    
    @tornado.web.authenticated
    def post(self):
        name = self.get_argument("name")
        code = self.get_argument("code")
        description = self.get_argument("description", "")
        status = int(self.get_argument("status", 1))
        
        if RoleRepository.create(name, code, description, status):
            self.write({"code": 0, "msg": "角色创建成功"})
        else:
            self.write({"code": 1, "msg": "角色创建失败，代码可能已存在"})
    
    @tornado.web.authenticated
    def put(self):
        role_id = int(self.get_argument("role_id"))
        name = self.get_argument("name", None)
        description = self.get_argument("description", None)
        status = self.get_argument("status", None)
        
        update_data = {}
        if name:
            update_data["name"] = name
        if description:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = int(status)
        
        if RoleRepository.update(role_id, **update_data):
            self.write({"code": 0, "msg": "角色更新成功"})
        else:
            self.write({"code": 1, "msg": "角色更新失败"})
    
    @tornado.web.authenticated
    def delete(self):
        role_id = int(self.get_argument("role_id"))
        if RoleRepository.delete(role_id):
            self.write({"code": 0, "msg": "角色删除成功"})
        else:
            self.write({"code": 1, "msg": "角色删除失败"})

class AdminFunctionController(BaseHandler):
    """功能管理控制器"""
    
    @tornado.web.authenticated
    def get(self):
        status = self.get_argument("status", None)
        if status:
            status = int(status)
        
        functions = FunctionRepository.get_all(status=status if status is not None else None)
        self.write({"code": 0, "msg": "success", "data": functions})
    
    @tornado.web.authenticated
    def post(self):
        parent_id = int(self.get_argument("parent_id", 0))
        name = self.get_argument("name")
        code = self.get_argument("code")
        icon = self.get_argument("icon", None)
        route = self.get_argument("route", None)
        sort_order = int(self.get_argument("sort_order", 0))
        status = int(self.get_argument("status", 1))
        
        if FunctionRepository.create(parent_id, name, code, icon, route, sort_order, status):
            self.write({"code": 0, "msg": "功能创建成功"})
        else:
            self.write({"code": 1, "msg": "功能创建失败"})
    
    @tornado.web.authenticated
    def put(self):
        func_id = int(self.get_argument("func_id"))
        parent_id = self.get_argument("parent_id", None)
        name = self.get_argument("name", None)
        code = self.get_argument("code", None)
        icon = self.get_argument("icon", None)
        route = self.get_argument("route", None)
        sort_order = self.get_argument("sort_order", None)
        status = self.get_argument("status", None)
        
        update_data = {}
        if parent_id is not None:
            update_data["parent_id"] = int(parent_id)
        if name:
            update_data["name"] = name
        if code:
            update_data["code"] = code
        if icon:
            update_data["icon"] = icon
        if route:
            update_data["route"] = route
        if sort_order is not None:
            update_data["sort_order"] = int(sort_order)
        if status is not None:
            update_data["status"] = int(status)
        
        if FunctionRepository.update(func_id, **update_data):
            self.write({"code": 0, "msg": "功能更新成功"})
        else:
            self.write({"code": 1, "msg": "功能更新失败"})
    
    @tornado.web.authenticated
    def delete(self):
        func_id = int(self.get_argument("func_id"))
        if FunctionRepository.delete(func_id):
            self.write({"code": 0, "msg": "功能删除成功"})
        else:
            self.write({"code": 1, "msg": "功能删除失败"})

class AdminMenuController(BaseHandler):
    """菜单管理控制器"""
    
    @tornado.web.authenticated
    def get(self):
        role_id = self.get_argument("role_id", None)
        if role_id:
            role_id = int(role_id)
            menus = MenuRepository.get_by_role_id(role_id)
        else:
            menus = MenuRepository.get_all()
        
        self.write({"code": 0, "msg": "success", "data": menus})
    
    @tornado.web.authenticated
    def post(self):
        role_id = int(self.get_argument("role_id"))
        func_id = int(self.get_argument("func_id"))
        sort_order = int(self.get_argument("sort_order", 0))
        status = int(self.get_argument("status", 1))
        
        if MenuRepository.create(role_id, func_id, sort_order, status):
            self.write({"code": 0, "msg": "菜单创建成功"})
        else:
            self.write({"code": 1, "msg": "菜单创建失败"})
    
    @tornado.web.authenticated
    def put(self):
        menu_id = int(self.get_argument("menu_id"))
        sort_order = self.get_argument("sort_order", None)
        status = self.get_argument("status", None)
        
        update_data = {}
        if sort_order is not None:
            update_data["sort_order"] = int(sort_order)
        if status is not None:
            update_data["status"] = int(status)
        
        if MenuRepository.update(menu_id, **update_data):
            self.write({"code": 0, "msg": "菜单更新成功"})
        else:
            self.write({"code": 1, "msg": "菜单更新失败"})
    
    @tornado.web.authenticated
    def delete(self):
        menu_id = int(self.get_argument("menu_id"))
        if MenuRepository.delete(menu_id):
            self.write({"code": 0, "msg": "菜单删除成功"})
        else:
            self.write({"code": 1, "msg": "菜单删除失败"})
