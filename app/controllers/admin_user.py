import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository

class UserManagementHandler(BaseHandler):
    """用户管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/user_management.html", title="用户管理", username=self.current_user)

class UserListApiHandler(BaseHandler):
    """用户列表API"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", "")
        role_id = self.get_argument("role_id", "")
        status = self.get_argument("status", "")
        
        # 转换空字符串为None
        if not search: search = None
        if not role_id: role_id = None
        else: role_id = int(role_id)
        if not status: status = None
        else: status = int(status)
        
        result = UserRepository.get_all_users(page, page_size, search, role_id, status)
        self.write(json.dumps(result, ensure_ascii=False))

class UserGetApiHandler(BaseHandler):
    """获取用户详情API"""
    @tornado.web.authenticated
    def get(self):
        user_id = self.get_argument("user_id", "")
        if not user_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "用户ID不能为空"}))
            return
        
        user = UserRepository.get_user_by_id(int(user_id))
        if user:
            self.write(json.dumps({"success": True, "data": user}))
        else:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "用户不存在"}))

class UserCreateApiHandler(BaseHandler):
    """创建用户API"""
    @tornado.web.authenticated
    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        role_id = int(self.get_argument("role_id", 2))
        
        if not username or not password:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "用户名和密码不能为空"}))
            return
        
        if UserRepository.create_user(username, password, role_id):
            self.write(json.dumps({"success": True, "message": "用户创建成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "用户名已存在"}))

class UserUpdateApiHandler(BaseHandler):
    """更新用户API"""
    @tornado.web.authenticated
    def post(self):
        user_id = self.get_argument("user_id", "")
        username = self.get_argument("username", "")
        role_id = self.get_argument("role_id", "")
        status = self.get_argument("status", "")
        password = self.get_argument("password", "")
        
        # 获取被编辑用户的信息
        target_user = UserRepository.get_user_by_id(int(user_id))
        if not target_user:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "用户不存在"}))
            return
        
        is_target_admin = (target_user.get("username") == "admin")
        current_user = self.current_user  # 当前登录用户名
        
        # 超级管理员保护：不允许任何人修改admin的资料（用户名、角色、状态）
        if is_target_admin:
            # 不允许修改admin的用户名、角色、状态
            if (username and username != "admin") or (role_id and str(role_id) != str(target_user.get("role_id"))) or (status and str(status) != str(target_user.get("status"))):
                self.set_status(403)
                self.write(json.dumps({"success": False, "message": "超级管理员信息不允许修改"}))
                return
            # 只有admin自己可以修改自己的密码
            if password:
                if current_user != "admin":
                    self.set_status(403)
                    self.write(json.dumps({"success": False, "message": "只有超级管理员本人可以修改密码"}))
                    return
                UserRepository.update_password(int(user_id), password)
                self.write(json.dumps({"success": True, "message": "密码修改成功"}))
                return
        
        # 非admin用户的正常编辑流程
        updates = {}
        if username:
            updates["username"] = username
        if role_id:
            updates["role_id"] = int(role_id)
        if status:
            updates["status"] = int(status)
        
        # 如果传入了新密码
        if password:
            UserRepository.update_password(int(user_id), password)
        
        if UserRepository.update_user(int(user_id), **updates):
            self.write(json.dumps({"success": True, "message": "用户更新成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "更新失败"}))

class UserDeleteApiHandler(BaseHandler):
    """删除用户API"""
    @tornado.web.authenticated
    def post(self):
        user_id = self.get_argument("user_id", "")
        
        # 超级管理员不允许删除
        user = UserRepository.get_user_by_id(int(user_id))
        if user and user.get("username") == "admin":
            self.set_status(403)
            self.write(json.dumps({"success": False, "message": "超级管理员不允许删除"}))
            return
        
        if UserRepository.delete_user(int(user_id)):
            self.write(json.dumps({"success": True, "message": "用户删除成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "删除失败"}))
