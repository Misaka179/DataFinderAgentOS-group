import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository

class LoginHandler(BaseHandler):
    def get(self):
        # 如果已登录，直接跳转到首页
        if self.current_user:
            self.redirect("/index")
            return
        self.render("login.html",title="登录页面",error=None)

    def post(self):
        username = self.get_body_argument("username")
        password = self.get_body_argument("password")
        if not username or not password:
            self.set_status(400)
            return self.render("login.html",title="登录页面",error="用户名或密码不能为空")
        
        if not UserRepository.verify_user(username,password):
            self.set_status(401)
            return self.render("login.html",title="登录页面",error="用户名或密码错误")
        
        self.set_secure_cookie("username", username)
        self.redirect("/index")

class LogoutHandler(BaseHandler):
    def post(self):
        self.clear_cookie("username")
        self.redirect("/")

class RegisterHandler(BaseHandler):
    """用户侧注册页面"""
    def get(self):
        if self.current_user:
            self.redirect("/index")
            return
        self.render("register.html", title="用户注册")

class FaceLoginHandler(BaseHandler):
    """人脸识别登录页面 + 人脸登录验证"""
    def get(self):
        if self.current_user:
            self.redirect("/index")
            return
        # 触发 XSRF cookie 下发，前端 POST 时需要
        self.xsrf_token
        self.render("face_login.html")

    def post(self):
        username = self.get_body_argument("username", "").strip()
        face_login = self.get_body_argument("face_login", "0")
        if face_login == "1" and username:
            user = UserRepository.get_user_by_username(username)
            if user and user["status"] == 1:
                self.set_secure_cookie("username", username)
                self.redirect("/index")
                return
        self.set_status(403)
        self.write({"ok": False, "msg": "人脸验证失败"})

class AdminLoginHandler(BaseHandler):
    def get(self):
        self.render("admin/login.html",title="后台登录",error=None)

    def post(self):
        username = self.get_body_argument("username")
        password = self.get_body_argument("password")
        if not username or not password:
            self.set_status(400)
            return self.render("admin/login.html",title="后台登录",error="用户名或密码不能为空")
        
        if not UserRepository.verify_user(username,password):
            self.set_status(401)
            return self.render("admin/login.html",title="后台登录",error="用户名或密码错误")
        
        self.set_secure_cookie("username", username)
        self.redirect("/admin/index")

class AdminLogoutHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        self.clear_cookie("username")
        self.redirect("/admin/")
