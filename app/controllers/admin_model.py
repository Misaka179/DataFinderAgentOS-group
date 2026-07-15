import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.ai_model import AiModelRepository


class ModelEngineHandler(BaseHandler):
    """模型引擎页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/model_engine.html", title="模型引擎", username=self.current_user)


class ModelListApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 6))
        search = self.get_argument("search", "")
        category = self.get_argument("category", "")
        if not search:
            search = None
        if not category:
            category = None
        result = AiModelRepository.get_all(page, page_size, search, category)
        self.write(json.dumps(result, ensure_ascii=False))


class ModelCategoriesApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        cats = AiModelRepository.get_categories()
        # 确保默认分类存在
        all_cats = ["text", "image", "audio", "video", "multimodal", "embedding"]
        for c in all_cats:
            if c not in cats:
                cats.append(c)
        self.write(json.dumps({"success": True, "data": sorted(cats)}))


class ModelGetApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        model_id = self.get_argument("model_id", "")
        if not model_id:
            self.write(json.dumps({"success": False, "message": "模型ID不能为空"}))
            return
        model = AiModelRepository.get_by_id(int(model_id))
        if model:
            self.write(json.dumps({"success": True, "data": model}))
        else:
            self.write(json.dumps({"success": False, "message": "模型不存在"}))


class ModelCreateApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        name = self.get_argument("name", "")
        provider = self.get_argument("provider", "openai")
        model_name = self.get_argument("model_name", "")
        api_base_url = self.get_argument("api_base_url", "")
        api_key = self.get_argument("api_key", "")
        max_tokens = int(self.get_argument("max_tokens", 4096))
        category = self.get_argument("category", "text")
        system_prompt = self.get_argument("system_prompt", "")
        temperature = float(self.get_argument("temperature", 0.7))
        top_p = float(self.get_argument("top_p", 1.0))
        context_length = int(self.get_argument("context_length", 4096))

        if not name or not model_name:
            self.write(json.dumps({"success": False, "message": "名称和模型ID不能为空"}))
            return

        if AiModelRepository.create(name, provider, model_name, api_base_url, api_key,
                                     max_tokens, category, system_prompt, temperature, top_p, context_length):
            self.write(json.dumps({"success": True, "message": "模型创建成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "模型创建失败"}))


class ModelUpdateApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        model_id = self.get_argument("model_id", "")
        updates = {}
        for key in ("name", "provider", "model_name", "api_base_url", "api_key",
                     "max_tokens", "token_count", "status", "category",
                     "system_prompt", "top_p", "context_length"):
            val = self.get_argument(key, "")
            if val:
                if key in ("max_tokens", "token_count", "context_length"):
                    updates[key] = int(val)
                elif key in ("temperature", "top_p"):
                    updates[key] = float(val)
                else:
                    updates[key] = val

        if AiModelRepository.update(int(model_id), **updates):
            self.write(json.dumps({"success": True, "message": "模型更新成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "模型更新失败"}))


class ModelDeleteApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        model_id = self.get_argument("model_id", "")
        if AiModelRepository.delete(int(model_id)):
            self.write(json.dumps({"success": True, "message": "模型删除成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "模型删除失败"}))


class ModelSetDefaultApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        model_id = self.get_argument("model_id", "")
        if AiModelRepository.set_default(int(model_id)):
            self.write(json.dumps({"success": True, "message": "默认模型设置成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "默认模型设置失败"}))


class ModelGetDefaultApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        model = AiModelRepository.get_default()
        if model:
            self.write(json.dumps({"success": True, "data": model}))
        else:
            self.write(json.dumps({"success": False, "message": "未设置默认模型"}))


class ModelChatApiHandler(BaseHandler):
    """SSE流式对话API - 代理请求到真实OpenAI API"""
    @tornado.web.authenticated
    async def post(self):
        model_id = self.get_argument("model_id", "")
        messages = self.get_argument("messages", "")
        system_prompt = self.get_argument("system_prompt", "")
        temperature = float(self.get_argument("temperature", 0.7))
        top_p = float(self.get_argument("top_p", 1.0))
        max_tokens = int(self.get_argument("max_tokens", 4096))

        model = None
        if model_id:
            model = AiModelRepository.get_by_id(int(model_id))
        if not model:
            model = AiModelRepository.get_default()
        if not model:
            self.write(json.dumps({"success": False, "message": "无可用模型"}))
            return

        # 解析消息
        try:
            msg_list = json.loads(messages) if messages else []
        except json.JSONDecodeError:
            msg_list = []

        # 构建消息列表（含系统提示词）
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        elif model.get("system_prompt"):
            api_messages.append({"role": "system", "content": model["system_prompt"]})
        api_messages.extend(msg_list)

        # 检查API配置
        api_base = (model.get("api_base_url") or "").rstrip("/")
        api_key = model.get("api_key") or ""
        model_name = model.get("model_name") or ""

        if not api_base or not api_key:
            self.write(json.dumps({"success": False, "message": "模型API配置不完整（缺少API地址或密钥）"}))
            return

        # 构建API请求
        url = f"{api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        body = json.dumps({
            "model": model_name,
            "messages": api_messages,
            "stream": True,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        })

        # 设置SSE响应头
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        self.set_header("X-Accel-Buffering", "no")
        self.set_header("X-Content-Type-Options", "nosniff")

        from tornado.httpclient import AsyncHTTPClient, HTTPRequest
        from tornado.ioloop import IOLoop
        import sys

        token_count = 0
        buffer = ""

        def streaming_callback(chunk):
            """处理API流式响应的每个chunk（同步回调，由AsyncHTTPClient调用）"""
            nonlocal token_count, buffer
            if not chunk:
                return
            try:
                text = chunk.decode("utf-8", errors="replace")
            except Exception:
                text = str(chunk)

            buffer += text
            # 按行处理SSE内容
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        continue
                    try:
                        data_json = json.loads(data_str)
                        # 累加token数（从usage或增量估算）
                        if "usage" in data_json and data_json["usage"]:
                            token_count = data_json["usage"].get("completion_tokens", 0) or data_json["usage"].get("total_tokens", 0) or 0
                        choices = data_json.get("choices", [])
                        if choices and choices[0].get("delta", {}).get("content"):
                            token_count += 1
                        # 直接转发原始SSE数据
                        self.write(f"data: {data_str}\n\n")
                        IOLoop.current().add_callback(self.flush)
                    except json.JSONDecodeError:
                        # 非JSON内容，透传
                        self.write(f"data: {data_str}\n\n")
                        IOLoop.current().add_callback(self.flush)

        try:
            client = AsyncHTTPClient()
            request = HTTPRequest(
                url=url,
                method="POST",
                headers=headers,
                body=body,
                streaming_callback=streaming_callback,
                request_timeout=120,
                connect_timeout=30
            )
            response = await client.fetch(request)
        except Exception as e:
            # 发送友好错误信息（不暴露API密钥等敏感信息）
            error_msg = str(e)
            # 脱敏处理
            if "401" in error_msg or "Unauthorized" in error_msg:
                friendly_msg = "API认证失败，请检查API密钥是否正确"
            elif "404" in error_msg:
                friendly_msg = "模型端点不存在，请检查API地址或模型ID"
            elif "timeout" in error_msg.lower():
                friendly_msg = "请求超时，请检查网络连接或API地址"
            elif "Connection" in error_msg:
                friendly_msg = "连接失败，请检查API地址是否正确"
            else:
                friendly_msg = f"API请求异常: {error_msg[:100]}"
            error_response = json.dumps({"error": {"message": friendly_msg, "type": "api_error"}})
            self.write(f"data: {error_response}\n\n")

        # 更新token统计
        if token_count > 0:
            current = model.get("token_count", 0) or 0
            AiModelRepository.update(model["id"], token_count=current + token_count)

        self.write("data: [DONE]\n\n")
        self.finish()
