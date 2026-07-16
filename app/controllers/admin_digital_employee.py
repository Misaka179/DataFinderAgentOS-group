import json
import os
import tornado.web
import urllib.parse

from app.controllers.base import BaseHandler
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.ai_model import AiModelRepository
from app.models.skill import SkillRepository


class DigitalEmployeeManagementHandler(BaseHandler):
    """数字员工管理页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/digital_employee_management.html", title="数字员工", username=self.current_user)


class DigitalEmployeeListApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 15))
        search = self.get_argument("search", "")
        type_filter = self.get_argument("type", "")
        result = DigitalEmployeeRepository.get_all(page, page_size, search, type_filter)
        self.write(json.dumps(result, ensure_ascii=False))


class DigitalEmployeeGetApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        item_id = self.get_argument("id", "")
        if not item_id:
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        item = DigitalEmployeeRepository.get_by_id(int(item_id))
        if item:
            self.write(json.dumps({"success": True, "data": item}))
        else:
            self.write(json.dumps({"success": False, "message": "数据不存在"}))


class DigitalEmployeeCreateApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        try:
            body = self.request.body
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        
        required = ("name", "type")
        for field in required:
            if not data.get(field):
                self.write(json.dumps({"success": False, "message": f"缺少必填字段: {field}"}))
                return
        
        # 确保 JSON 字符串字段有效
        for json_field in ("skills", "api_headers", "api_params"):
            if data.get(json_field) and not isinstance(data[json_field], str):
                data[json_field] = json.dumps(data[json_field], ensure_ascii=False)
            elif data.get(json_field) is None:
                data[json_field] = "[]" if json_field == "skills" else "{}"
        
        item_id = DigitalEmployeeRepository.create(data)
        if item_id:
            # 创建数字员工专属目录 data/dgUser/{name}/
            emp_name = data.get("name", "")
            if emp_name:
                dg_dir = os.path.join("data", "dgUser", emp_name)
                os.makedirs(dg_dir, exist_ok=True)
            self.write(json.dumps({"success": True, "message": "创建成功", "id": item_id}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "创建失败"}))


class DigitalEmployeeUpdateApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        try:
            body = self.request.body
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        
        item_id = data.get("id", "")
        if not item_id:
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        
        # 确保 JSON 字符串字段有效
        for json_field in ("skills", "api_headers", "api_params"):
            if data.get(json_field) and not isinstance(data[json_field], str):
                data[json_field] = json.dumps(data[json_field], ensure_ascii=False)
        
        if DigitalEmployeeRepository.update(int(item_id), data):
            # 确保数字员工目录存在（可能修改了名称）
            emp_name = data.get("name", "")
            if emp_name:
                dg_dir = os.path.join("data", "dgUser", emp_name)
                os.makedirs(dg_dir, exist_ok=True)
            self.write(json.dumps({"success": True, "message": "更新成功"}))
        else:
            self.set_status(400)
            self.write(json.dumps({"success": False, "message": "更新失败"}))


class DigitalEmployeeDeleteApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        item_id = self.get_argument("id", "")
        if not item_id:
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        
        # 先获取数字员工信息（用于清理文件目录）
        item = DigitalEmployeeRepository.get_by_id(int(item_id))
        
        if DigitalEmployeeRepository.delete(int(item_id)):
            # 清理 data/dgUser/{name}/ 目录下的 .md 文件
            if item and item.get("name"):
                dg_dir = os.path.join("data", "dgUser", item["name"])
                if os.path.exists(dg_dir):
                    import shutil
                    shutil.rmtree(dg_dir, ignore_errors=True)
            self.write(json.dumps({"success": True, "message": "删除成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "删除失败"}))


class DigitalEmployeeUploadMdHandler(BaseHandler):
    """上传 .md 文件并读取内容（XSRF豁免：multipart/form-data与XSRF不兼容）"""
    def check_xsrf_cookie(self):
        pass  # 已有 @authenticated 保护，文件上传绕过 XSRF

    @tornado.web.authenticated
    def post(self):
        try:
            name = self.get_argument("name", "")
            if not name:
                self.set_header("Content-Type", "application/json")
                self.set_status(400)
                self.write(json.dumps({"success": False, "message": "缺少数字员工名称"}))
                self.finish()
                return

            base_dir = os.path.join("data", "dgUser", name)
            os.makedirs(base_dir, exist_ok=True)

            uploaded_files = []
            all_content = ""

            for field_name in self.request.files:
                for file_info in self.request.files[field_name]:
                    filename = file_info.get("filename", "")
                    if not filename.lower().endswith(".md"):
                        continue
                    body = file_info.get("body", b"")
                    filepath = os.path.join(base_dir, filename)
                    # 直接覆盖同名文件，防止重复上传产生 _1 _2 等编号副本
                    with open(filepath, "wb") as f:
                        f.write(body)
                    uploaded_files.append(os.path.basename(filepath))
                    content = body.decode('utf-8', errors='replace')
                    all_content += f"\n\n--- {os.path.basename(filepath)} ---\n{content}"

            if not uploaded_files:
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps({"success": False, "message": "未找到有效的 .md 文件"}))
                self.finish()
                return

            self.set_header("Content-Type", "application/json")
            self.set_status(200)
            self.write(json.dumps({
                "success": True,
                "message": f"成功上传 {len(uploaded_files)} 个 .md 文件",
                "files": uploaded_files,
                "content": all_content.strip()
            }, ensure_ascii=False))
            self.finish()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.set_header("Content-Type", "application/json")
            self.set_status(500)
            self.write(json.dumps({"success": False, "message": f"上传处理异常: {str(e)[:200]}"}))
            self.finish()


class DigitalEmployeeListMdHandler(BaseHandler):
    """列出数字员工已上传的 .md 文件"""
    @tornado.web.authenticated
    def get(self):
        try:
            name = self.get_argument("name", "")
            if not name:
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps({"success": False, "message": "缺少数字员工名称"}))
                self.finish()
                return

            base_dir = os.path.join("data", "dgUser", name)
            if not os.path.exists(base_dir):
                self.set_header("Content-Type", "application/json")
                self.write(json.dumps({"success": True, "files": []}))
                self.finish()
                return

            files = []
            for f in sorted(os.listdir(base_dir)):
                if f.lower().endswith(".md"):
                    filepath = os.path.join(base_dir, f)
                    with open(filepath, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    files.append({"name": f, "size": os.path.getsize(filepath), "content": content})

            self.set_header("Content-Type", "application/json")
            self.write(json.dumps({"success": True, "files": files}, ensure_ascii=False))
            self.finish()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.set_header("Content-Type", "application/json")
            self.set_status(500)
            self.write(json.dumps({"success": False, "message": f"获取文件列表异常: {str(e)[:200]}"}))
            self.finish()


class DigitalEmployeeModelsApiHandler(BaseHandler):
    """获取可用模型列表（用于关联选择）"""
    @tornado.web.authenticated
    def get(self):
        models = DigitalEmployeeRepository.get_all_models()
        self.write(json.dumps({"success": True, "data": models}, ensure_ascii=False))


class DigitalEmployeeSkillsApiHandler(BaseHandler):
    """获取可用技能列表（用于数字员工关联多选）"""
    @tornado.web.authenticated
    def get(self):
        skills = SkillRepository.get_enabled_list()
        self.write(json.dumps({"success": True, "data": skills}, ensure_ascii=False))


class DigitalEmployeeTestApiHandler(BaseHandler):
    """数字员工测试API"""
    @tornado.web.authenticated
    async def post(self):
        try:
            body = self.request.body
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        item_id = data.get("id", "")
        test_message = data.get("test_message", "你好，请回复一条测试消息。")

        if not item_id:
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return

        employee = DigitalEmployeeRepository.get_by_id(int(item_id))
        if not employee:
            self.write(json.dumps({"success": False, "message": "数字员工不存在"}))
            return

        if employee["type"] == "llm":
            result = await self._test_llm(employee, test_message)
            self.write(json.dumps(result, ensure_ascii=False))
        elif employee["type"] == "api":
            result = await self._test_api(employee)
            self.write(json.dumps(result, ensure_ascii=False))
        else:
            self.write(json.dumps({"success": False, "message": "未知的数字员工类型"}))

    async def _test_llm(self, employee, test_message):
        """测试LLM型数字员工"""
        model_id = employee.get("model_id")
        model = None
        if model_id:
            model = AiModelRepository.get_by_id(int(model_id))
        if not model:
            model = AiModelRepository.get_default()
        if not model:
            return {"success": False, "message": "无可用模型，请先配置模型引擎中的模型"}

        api_base = (model.get("api_base_url") or "").rstrip("/")
        api_key = model.get("api_key") or ""
        model_name = model.get("model_name") or ""

        if not api_base or not api_key:
            return {"success": False, "message": "关联模型的API配置不完整（缺少API地址或密钥）"}

        url = f"{api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        system_prompt = employee.get("system_prompt", "")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": test_message})

        request_body = json.dumps({
            "model": model_name,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": 1024
        })

        from tornado.httpclient import AsyncHTTPClient, HTTPRequest
        try:
            client = AsyncHTTPClient()
            request = HTTPRequest(
                url=url, method="POST", headers=headers,
                body=request_body, request_timeout=60, connect_timeout=15
            )
            response = await client.fetch(request)
            resp_data = json.loads(response.body)
            reply = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "reply": reply, "type": "llm", "test_message": test_message}
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                friendly = "API认证失败，请检查模型API密钥"
            elif "timeout" in error_msg.lower():
                friendly = "请求超时，请检查网络连接或API地址"
            else:
                friendly = f"请求失败: {error_msg[:200]}"
            return {"success": False, "message": friendly}

    async def _test_api(self, employee):
        """测试API型数字员工"""
        api_url = employee.get("api_url", "")
        if not api_url:
            return {"success": False, "message": "API地址未配置"}

        api_method = employee.get("api_method", "GET")
        api_headers = employee.get("api_headers", "{}")
        api_params = employee.get("api_params", "{}")

        try:
            headers_dict = json.loads(api_headers) if isinstance(api_headers, str) else (api_headers or {})
        except (json.JSONDecodeError, TypeError):
            headers_dict = {}

        try:
            params_dict = json.loads(api_params) if isinstance(api_params, str) else (api_params or {})
        except (json.JSONDecodeError, TypeError):
            params_dict = {}

        # 替换占位符为测试值
        test_values = {"city": "成都", "date": "2026-07-15", "keyword": "测试"}

        def replace_placeholders(obj):
            if isinstance(obj, str):
                for key, val in test_values.items():
                    obj = obj.replace("{" + key + "}", val)
                return obj
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(v) for v in obj]
            return obj

        params_dict = replace_placeholders(params_dict)
        headers_dict = replace_placeholders(headers_dict)

        from tornado.httpclient import AsyncHTTPClient, HTTPRequest
        try:
            client = AsyncHTTPClient()
            if api_method == "GET":
                query_parts = []
                for k, v in params_dict.items():
                    query_parts.append(f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}")
                if query_parts:
                    separator = "&" if "?" in api_url else "?"
                    api_url = f"{api_url}{separator}{'&'.join(query_parts)}"

                request = HTTPRequest(
                    url=api_url, method="GET", headers=headers_dict,
                    request_timeout=30, connect_timeout=15
                )
            else:
                body_str = json.dumps(params_dict) if isinstance(params_dict, dict) else str(params_dict)
                request = HTTPRequest(
                    url=api_url, method="POST", headers=headers_dict,
                    body=body_str, request_timeout=30, connect_timeout=15
                )

            response = await client.fetch(request)
            try:
                resp_json = json.loads(response.body)
                template = employee.get("api_response_template", "")
                if template:
                    reply = self._apply_template(resp_json, template)
                else:
                    reply = json.dumps(resp_json, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, ValueError):
                reply = response.body.decode("utf-8", errors="replace")[:2000]

            return {"success": True, "reply": reply, "type": "api"}
        except Exception as e:
            error_msg = str(e)
            return {"success": False, "message": f"API请求失败: {error_msg[:200]}"}

    def _apply_template(self, data, template):
        """应用响应模板，从JSON中提取指定路径的值"""
        parts = template.split(",")
        results = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            keys = part.split(".")
            current = data
            try:
                for key in keys:
                    if "[" in key and key.endswith("]"):
                        name = key[:key.index("[")]
                        idx = int(key[key.index("[") + 1:-1])
                        if name:
                            current = current.get(name, [])
                        current = current[idx] if isinstance(current, list) else current
                    else:
                        if isinstance(current, dict):
                            current = current.get(key, "")
                results.append(str(current))
            except Exception:
                results.append(str(data))
        return ", ".join(results)
