"""技能管理 — 管理侧控制器"""
import json
import tornado.web
from app.controllers.base import BaseHandler
from app.models.skill import SkillRepository


class SkillManagementHandler(BaseHandler):
    """技能管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/skill_management.html", title="技能管理", username=self.current_user)


class SkillListApiHandler(BaseHandler):
    """技能列表API（分页+搜索）"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        size = int(self.get_argument("size", 20))
        keyword = self.get_argument("keyword", "").strip()
        status = self.get_argument("status", "")

        total, rows = SkillRepository.get_all(page, size, keyword, status)
        self.write_json({"success": True, "data": rows, "total": total, "page": page, "size": size})


class SkillGetApiHandler(BaseHandler):
    """获取单个技能详情"""
    @tornado.web.authenticated
    def get(self):
        skill_id = self.get_argument("id", "")
        if not skill_id:
            self.write_json({"success": False, "error": "缺少id"})
            return
        skill = SkillRepository.get_by_id(int(skill_id))
        if not skill:
            self.write_json({"success": False, "error": "技能不存在"})
            return
        self.write_json({"success": True, "data": skill})


class SkillEnabledListApiHandler(BaseHandler):
    """获取启用状态的技能列表（供数字员工关联选择）"""
    @tornado.web.authenticated
    def get(self):
        skills = SkillRepository.get_enabled_list()
        self.write_json({"success": True, "data": skills})


class SkillCreateApiHandler(BaseHandler):
    """创建技能"""
    @tornado.web.authenticated
    def post(self):
        data = self._get_form_data()
        existing = SkillRepository.get_by_code(data["code"])
        if existing:
            self.write_json({"success": False, "error": "编码已存在"})
            return
        try:
            SkillRepository.create(data)
            self.write_json({"success": True})
        except Exception as e:
            self.write_json({"success": False, "error": str(e)})

    def _get_form_data(self):
        data = {
            "name": self.get_argument("name", "").strip(),
            "code": self.get_argument("code", "").strip(),
            "type": self.get_argument("type", "custom"),
            "impl_type": self.get_argument("impl_type", "prompt"),
            "status": int(self.get_argument("status", 1)),
            "description": self.get_argument("description", "").strip(),
            "impl_config": self._parse_json("impl_config"),
            "input_schema": self._parse_json("input_schema"),
            "output_schema": self._parse_json("output_schema"),
        }
        return data

    def _parse_json(self, field):
        val = self.get_argument(field, "{}")
        try:
            return json.loads(val) if isinstance(val, str) else val
        except Exception:
            return {}


class SkillUpdateApiHandler(SkillCreateApiHandler):
    """更新技能"""
    @tornado.web.authenticated
    def post(self):
        data = self._get_form_data()
        data["id"] = int(self.get_argument("id"))
        existing = SkillRepository.get_by_id(data["id"])
        if not existing:
            self.write_json({"success": False, "error": "技能不存在"})
            return
        try:
            SkillRepository.update(data)
            self.write_json({"success": True})
        except Exception as e:
            self.write_json({"success": False, "error": str(e)})


class SkillDeleteApiHandler(BaseHandler):
    """删除技能（仅自定义类型）"""
    @tornado.web.authenticated
    def post(self):
        skill_id = int(self.get_argument("id", 0))
        if not skill_id:
            self.write_json({"success": False, "error": "缺少id"})
            return
        try:
            SkillRepository.delete(skill_id)
            self.write_json({"success": True})
        except Exception as e:
            self.write_json({"success": False, "error": str(e)})


class SkillToggleApiHandler(BaseHandler):
    """启用/禁用技能"""
    @tornado.web.authenticated
    def post(self):
        skill_id = int(self.get_argument("id", 0))
        new_status = SkillRepository.toggle_status(skill_id)
        if new_status is not None:
            self.write_json({"success": True, "status": new_status})
        else:
            self.write_json({"success": False, "error": "技能不存在"})
