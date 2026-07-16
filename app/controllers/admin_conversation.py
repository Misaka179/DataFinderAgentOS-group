"""管理侧：会话管理 & 对话管理"""
import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.conversation import ConversationRepository


class ConversationManagementHandler(BaseHandler):
    """会话管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/conversation_management.html", title="会话管理", username=self.current_user)


class MessageManagementHandler(BaseHandler):
    """对话管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/message_management.html", title="对话管理", username=self.current_user)


class ConversationListApiHandler(BaseHandler):
    """会话列表API（跨用户）"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", "")
        if not search:
            search = None
        result = ConversationRepository.get_all_admin(page, page_size, search)
        self.write(json.dumps(result, ensure_ascii=False))


class ConversationMessagesApiHandler(BaseHandler):
    """获取指定会话的完整消息列表"""
    @tornado.web.authenticated
    def get(self):
        conv_id = self.get_argument("id", "")
        if not conv_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "会话ID不能为空"}, ensure_ascii=False))
            return
        item = ConversationRepository.get_by_id_admin(int(conv_id))
        if item:
            self.write(json.dumps({"success": True, "data": item}, ensure_ascii=False))
        else:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "会话不存在"}, ensure_ascii=False))


class ConversationDeleteApiHandler(BaseHandler):
    """删除会话"""
    @tornado.web.authenticated
    def post(self):
        conv_id = self.get_argument("id", "")
        if not conv_id:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "会话ID不能为空"}, ensure_ascii=False))
            return
        ConversationRepository.delete_admin(int(conv_id))
        self.write(json.dumps({"success": True, "message": "会话已删除"}, ensure_ascii=False))


class ConversationDeleteMessageApiHandler(BaseHandler):
    """删除单条消息"""
    @tornado.web.authenticated
    def post(self):
        conv_id = self.get_argument("conv_id", "")
        msg_index = self.get_argument("msg_index", "")
        if not conv_id or msg_index == "":
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "参数不完整"}, ensure_ascii=False))
            return
        ok = ConversationRepository.delete_message(int(conv_id), int(msg_index))
        if ok:
            self.write(json.dumps({"success": True, "message": "消息已删除"}, ensure_ascii=False))
        else:
            self.set_status(404)
            self.write(json.dumps({"success": False, "message": "消息不存在"}, ensure_ascii=False))


class ConversationMessagesAllApiHandler(BaseHandler):
    """获取所有消息（展平，跨会话），用于对话管理页面"""
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", "")
        if not search:
            search = None
        result = ConversationRepository.get_all_messages_admin(page, page_size, search)
        self.write(json.dumps(result, ensure_ascii=False))
