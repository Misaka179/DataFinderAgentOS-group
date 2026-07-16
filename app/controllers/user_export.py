"""用户侧-前台控制器：对话 PDF 导出"""
import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.user import UserRepository
from app.models.conversation import ConversationRepository
from app.services.pdf_export import generate_conversations_pdf


class UserExportPdfApiHandler(BaseHandler):
    """对话记录导出为 PDF"""

    @tornado.web.authenticated
    def post(self):
        if not self.current_user:
            self.write(json.dumps({"success": False, "message": "未登录"}))
            return

        user = UserRepository.get_user_by_username(self.current_user)
        if not user:
            self.write(json.dumps({"success": False, "message": "用户不存在"}))
            return

        # 解析请求体
        try:
            data = json.loads(self.request.body or "{}")
        except (json.JSONDecodeError, TypeError):
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "请求数据格式错误"}))
            return

        conv_ids = data.get("conversation_ids", [])

        if not conv_ids:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "请选择要导出的对话"}))
            return

        # 按 user_id 隔离查询（确保不能导出他人对话）
        conversations = []
        for cid in conv_ids:
            try:
                conv = ConversationRepository.get_by_id(int(cid), user["id"])
            except (ValueError, TypeError):
                continue
            if conv:
                conversations.append(conv)

        if not conversations:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "没有可导出的对话（可能已被删除或无权限）"}))
            return

        # 生成 PDF
        try:
            pdf_bytes = generate_conversations_pdf(conversations, user["username"])
        except Exception as e:
            self.set_status(500)
            self.write(json.dumps({"success": False, "message": f"PDF 生成失败: {str(e)[:200]}"}))
            return

        # 返回 PDF 文件下载
        import datetime
        from urllib.parse import quote
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_cn = f"对话导出_{timestamp}.pdf"

        # 使用 filename*=UTF-8 编码支持中文文件名（RFC 5987）
        self.set_header("Content-Type", "application/pdf")
        encoded_filename = quote(filename_cn)
        self.set_header("Content-Disposition",
                        f'attachment; filename="chat_export_{timestamp}.pdf"; filename*=UTF-8\'\'{encoded_filename}')
        self.set_header("Content-Length", str(len(pdf_bytes)))
        self.write(pdf_bytes)
        self.finish()
