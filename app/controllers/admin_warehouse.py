import json
import datetime
import tornado.web

from app.controllers.base import BaseHandler
from app.models.data_warehouse import DataWarehouseRepository
from app.models.deep_collect import DeepCollectRepository
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.ai_model import AiModelRepository


class WarehouseManagementHandler(BaseHandler):
    """数据仓库页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/warehouse_management.html", title="数据仓库", username=self.current_user)


class WarehouseListApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        page = int(self.get_argument("page", 1))
        page_size = int(self.get_argument("page_size", 20))
        search = self.get_argument("search", "")
        result = DataWarehouseRepository.get_all(page, page_size, search if search else None)
        # 批量查询运行中的任务状态
        if result.get("data"):
            warehouse_ids = [item["id"] for item in result["data"]]
            task_map = DeepCollectRepository.get_latest_by_warehouse_ids(warehouse_ids)
            for item in result["data"]:
                wid = item["id"]
                if wid in task_map:
                    item["task_status"] = task_map[wid].get("status")
                    item["task_id"] = task_map[wid].get("task_id")
        self.write(json.dumps(result, ensure_ascii=False))


class WarehouseGetApiHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        item_id = self.get_argument("id", "")
        if not item_id:
            self.write(json.dumps({"success": False, "message": "ID不能为空"}))
            return
        item = DataWarehouseRepository.get_by_id(int(item_id))
        if item:
            self.write(json.dumps({"success": True, "data": item}))
        else:
            self.write(json.dumps({"success": False, "message": "数据不存在"}))


class WarehouseDeleteApiHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        item_id = self.get_argument("id", "")
        if DataWarehouseRepository.delete(int(item_id)):
            self.write(json.dumps({"success": True, "message": "删除成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "删除失败"}))


class WarehouseBatchDeleteApiHandler(BaseHandler):
    """批量删除"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = self.request.body
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        ids = data.get("ids", [])
        if not ids:
            self.write(json.dumps({"success": False, "message": "请选择要删除的数据"}))
            return
        ids = [int(x) for x in ids]
        if DataWarehouseRepository.batch_delete(ids):
            self.write(json.dumps({"success": True, "message": f"已删除 {len(ids)} 条数据"}))
        else:
            self.write(json.dumps({"success": False, "message": "批量删除失败"}))


# ========== 深度采集核心逻辑（模块级函数，可被多个Handler复用） ==========

def _find_deep_collect_employee():
    """查找用于深度采集的数字员工（优先采集专员）"""
    employees = DigitalEmployeeRepository.get_all(page=1, page_size=100, search="", type_filter="llm")
    for emp in employees.get("data", []):
        if "采集专员" in emp.get("name", ""):
            return emp
    for emp in employees.get("data", []):
        if emp.get("status") == 1:
            return emp
    return None


async def _start_single_deep_collect(warehouse_id, employee=None):
    """为单条数据启动深度采集（employee 可预传入以优化批量查询）"""
    if employee is None:
        employee = _find_deep_collect_employee()
    employee_id = employee["id"] if employee else None
    employee_name = employee["name"] if employee else "未知"

    task_id = DeepCollectRepository.create_task(warehouse_id, employee_id, employee_name)
    if not task_id:
        return None

    warehouse_item = DataWarehouseRepository.get_by_id(warehouse_id)
    if not warehouse_item:
        DeepCollectRepository.update_task(task_id, {
            "status": "failed",
            "error_message": "数据仓库记录不存在"
        })
        return task_id

    # 启动后台异步采集
    from tornado.ioloop import IOLoop
    IOLoop.current().add_callback(
        _execute_deep_collect, task_id, warehouse_item, employee
    )

    return task_id


async def _crawl_with_crawl4ai(url):
    """使用crawl4ai爬取网页内容"""
    if not url:
        return None
    try:
        from crawl4ai import AsyncWebCrawler
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result and result.success:
                return {
                    "markdown": result.markdown,
                    "success": True
                }
            return {"success": False, "message": "爬取失败"}
    except Exception as e:
        return {"success": False, "message": str(e)[:200]}


async def _execute_deep_collect(task_id, warehouse_item, employee):
    """后台执行深度采集（使用crawl4ai抓取网页 + 数字员工分析）"""
    try:
        # 步骤1: 初始化
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DeepCollectRepository.update_task(task_id, {
            "status": "running",
            "progress": 5,
            "started_at": now,
            "steps": json.dumps([
                {"name": "初始化任务", "status": "completed", "time": ""},
                {"name": "获取数字员工", "status": "running", "time": ""},
                {"name": "爬取网页内容", "status": "pending", "time": ""},
                {"name": "调用模型分析", "status": "pending", "time": ""},
                {"name": "生成采集结果", "status": "pending", "time": ""}
            ]),
            "logs": json.dumps([
                {"level": "info", "msg": f"深度采集任务 #{task_id} 已启动", "time": ""}
            ])
        })

        # 步骤2: 检查数字员工
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not employee:
            DeepCollectRepository.update_task(task_id, {
                "status": "failed",
                "progress": 10,
                "error_message": "未找到可用的数字员工（采集专员）",
                "logs": json.dumps([{"level": "error", "msg": "未找到可用的数字员工，请在数字员工管理中创建或启用", "time": now}])
            })
            return

        steps = [
            {"name": "初始化任务", "status": "completed", "time": now},
            {"name": "获取数字员工", "status": "completed", "time": now},
            {"name": "爬取网页内容", "status": "running", "time": ""},
            {"name": "调用模型分析", "status": "pending", "time": ""},
            {"name": "生成采集结果", "status": "pending", "time": ""}
        ]
        logs = [
            {"level": "info", "msg": f"使用数字员工: {employee.get('name', '未知')}", "time": now},
            {"level": "info", "msg": f"正在处理: {warehouse_item.get('title', '未知')}", "time": now}
        ]
        DeepCollectRepository.update_task(task_id, {
            "progress": 15,
            "steps": json.dumps(steps),
            "logs": json.dumps(logs)
        })

        # 步骤3: 使用crawl4ai爬取网页（如果员工启用且数据有URL）
        crawled_content = ""
        url = warehouse_item.get("url", "")
        crawl4ai_enabled = employee.get("crawl4ai_enabled", 0)
        should_crawl = bool(url) and (crawl4ai_enabled == 1 or employee.get("type") == "llm")

        if should_crawl:
            logs.append({"level": "info", "msg": f"正在爬取网页: {url}", "time": now})
            DeepCollectRepository.update_task(task_id, {
                "progress": 30,
                "logs": json.dumps(logs)
            })
            crawl_result = await _crawl_with_crawl4ai(url)
            if crawl_result and crawl_result.get("success"):
                crawled_content = crawl_result.get("markdown", "")
                logs.append({"level": "success", "msg": f"网页爬取成功，获取到 {len(crawled_content)} 字符内容", "time": now})
            else:
                logs.append({"level": "warning", "msg": f"网页爬取失败: {crawl_result.get('message', '未知错误')}，将使用已有摘要", "time": now})
        else:
            reason = "无URL" if not url else "数字员工未启用crawl4ai"
            logs.append({"level": "info", "msg": f"跳过网页爬取（{reason}），使用已有摘要", "time": now})

        now2 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps[2]["status"] = "completed"
        steps[2]["time"] = now2

        # 步骤4: 调用模型分析
        steps[3]["status"] = "running"
        steps[3]["time"] = now2
        DeepCollectRepository.update_task(task_id, {
            "progress": 50,
            "steps": json.dumps(steps),
            "logs": json.dumps(logs)
        })

        if employee.get("type") == "llm":
            result = await _call_llm(employee, warehouse_item, crawled_content)
        else:
            result = await _call_api_employee(employee, warehouse_item, crawled_content)

        now3 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps[3]["status"] = "completed"
        steps[3]["time"] = now3

        if result.get("success"):
            steps[4]["status"] = "completed"
            steps[4]["time"] = now3

            # 构建完整结果（爬取内容 + 分析结果）
            full_result = ""
            if crawled_content:
                full_result += "=== 网页原始内容（爬取）===\n"
                full_result += crawled_content[:10000]  # 限制长度
                full_result += "\n\n=== AI分析结果 ===\n"
            full_result += result.get("reply", "")

            DeepCollectRepository.update_task(task_id, {
                "status": "completed",
                "progress": 100,
                "steps": json.dumps(steps),
                "result_data": full_result,
                "completed_at": now3,
                "logs": json.dumps(logs + [
                    {"level": "info", "msg": "模型分析完成", "time": now3},
                    {"level": "success", "msg": "深度采集任务完成", "time": now3}
                ])
            })
            # 更新数据仓库状态
            DataWarehouseRepository._update_deep_collected(warehouse_item["id"], 1)

            # 保存采集详细数据到 deep_collect_data 表（持久化）
            DeepCollectRepository.save_collected_data(
                warehouse_id=warehouse_item["id"],
                task_id=task_id,
                crawled_title=warehouse_item.get("title", ""),
                crawled_content=crawled_content[:20000] if crawled_content else "",
                analysis_result=result.get("reply", ""),
                extra_data={
                    "url": warehouse_item.get("url", ""),
                    "source": warehouse_item.get("source_name", ""),
                    "keyword": warehouse_item.get("keyword", ""),
                    "employee_name": employee.get("name", "") if employee else "",
                    "summary": warehouse_item.get("summary", "")
                }
            )
        else:
            steps[4]["status"] = "failed"
            steps[4]["time"] = now3
            DeepCollectRepository.update_task(task_id, {
                "status": "failed",
                "progress": 60,
                "steps": json.dumps(steps),
                "error_message": result.get("message", "采集分析失败"),
                "logs": json.dumps(logs + [
                    {"level": "error", "msg": f"模型分析失败: {result.get('message', '未知错误')}", "time": now3}
                ])
            })

    except Exception as e:
        err_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import traceback
        DeepCollectRepository.update_task(task_id, {
            "status": "failed",
            "progress": 0,
            "error_message": str(e)[:500],
            "logs": json.dumps([{"level": "error", "msg": f"任务异常: {str(e)[:200]}", "time": err_time}])
        })


async def _call_llm(employee, warehouse_item, crawled_content=""):
    """调用LLM型数字员工进行分析（使用爬取的网页内容）"""
    model_id = employee.get("model_id")
    model = None
    if model_id:
        model = AiModelRepository.get_by_id(int(model_id))
    if not model:
        model = AiModelRepository.get_default()
    if not model:
        return {"success": False, "message": "关联模型不可用"}

    api_base = (model.get("api_base_url") or "").rstrip("/")
    api_key = model.get("api_key") or ""
    model_name = model.get("model_name") or ""
    if not api_base or not api_key:
        return {"success": False, "message": "模型API配置不完整"}

    system_prompt = employee.get("system_prompt", "") or "你是一个专业的数据采集分析专员，请对给定的数据进行深度分析。"

    title = warehouse_item.get("title", "")
    summary = warehouse_item.get("summary", "")
    source = warehouse_item.get("source_name", "")
    keyword = warehouse_item.get("keyword", "")

    # 构建用户提示词（包含爬取内容）
    user_prompt_parts = [f"请对以下数据进行深度采集分析：\n\n标题：{title}\n来源：{source}\n关键词：{keyword}\n摘要：{summary}"]

    if crawled_content:
        # 截取合理长度（避免超出token限制）
        content_preview = crawled_content[:8000]
        user_prompt_parts.append(f"\n\n以下是通过网页爬虫获取的页面正文内容（Markdown格式）：\n\n{content_preview}")

    user_prompt_parts.append("""
请提供：
1. 内容摘要（200字以内）
2. 关键信息提取
3. 数据分析与洞察
4. 相关建议""")

    user_prompt = "\n".join(user_prompt_parts)

    from tornado.httpclient import AsyncHTTPClient, HTTPRequest
    url = f"{api_base}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = json.dumps({
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 2048
    })

    try:
        client = AsyncHTTPClient()
        request = HTTPRequest(url=url, method="POST", headers=headers, body=body,
                              request_timeout=180, connect_timeout=30)
        response = await client.fetch(request)
        resp_data = json.loads(response.body)
        reply = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "message": str(e)[:200]}


async def _call_api_employee(employee, warehouse_item, crawled_content=""):
    """调用API型数字员工（支持爬取内容作为参数传入）"""
    api_url = employee.get("api_url", "")
    if not api_url:
        return {"success": False, "message": "API地址未配置"}
    api_method = employee.get("api_method", "GET")

    try:
        headers_dict = json.loads(employee.get("api_headers", "{}") or "{}")
    except Exception:
        headers_dict = {}
    try:
        params_template = json.loads(employee.get("api_params", "{}") or "{}")
    except Exception:
        params_template = {}

    def replace(obj):
        if isinstance(obj, str):
            s = obj.replace("{title}", warehouse_item.get("title", "")) \
                   .replace("{summary}", warehouse_item.get("summary", "")) \
                   .replace("{keyword}", warehouse_item.get("keyword", ""))
            if "{crawled_content}" in s:
                clip = crawled_content[:5000] if crawled_content else ""
                s = s.replace("{crawled_content}", clip)
            return s
        elif isinstance(obj, dict):
            return {k: replace(v) for k, v in obj.items()}
        return obj

    params_dict = replace(params_template)
    headers_dict = replace(headers_dict)

    from tornado.httpclient import AsyncHTTPClient, HTTPRequest
    try:
        client = AsyncHTTPClient()
        if api_method == "GET":
            import urllib.parse
            query = "&".join(f"{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}" for k, v in params_dict.items())
            if query:
                sep = "&" if "?" in api_url else "?"
                api_url = f"{api_url}{sep}{query}"
            request = HTTPRequest(url=api_url, method="GET", headers=headers_dict,
                                  request_timeout=60, connect_timeout=15)
        else:
            body_str = json.dumps(params_dict)
            request = HTTPRequest(url=api_url, method="POST", headers=headers_dict, body=body_str,
                                  request_timeout=60, connect_timeout=15)

        response = await client.fetch(request)
        try:
            reply = json.dumps(json.loads(response.body), ensure_ascii=False, indent=2)
        except Exception:
            reply = response.body.decode("utf-8", errors="replace")[:5000]
        return {"success": True, "reply": reply}
    except Exception as e:
        return {"success": False, "message": f"API请求失败: {str(e)[:200]}"}


# ========== API Handlers ==========

class WarehouseBatchDeepCollectApiHandler(BaseHandler):
    """批量启动深度采集"""
    @tornado.web.authenticated
    async def post(self):
        try:
            body = self.request.body
            data = json.loads(body) if body else {}
        except Exception:
            data = {}
        ids = data.get("ids", [])
        if not ids:
            self.write(json.dumps({"success": False, "message": "请选择要深度采集的数据"}))
            return

        ids = [int(x) for x in ids]
        task_ids = []

        # 只查一次员工，所有任务复用
        employee = _find_deep_collect_employee()
        for wid in ids:
            task_id = await _start_single_deep_collect(wid, employee=employee)
            if task_id:
                task_ids.append(task_id)

        self.write(json.dumps({
            "success": True,
            "message": f"已提交 {len(task_ids)} 条数据到深度采集队列",
            "task_ids": task_ids
        }))


class DeepCollectTaskApiHandler(BaseHandler):
    """获取深度采集任务状态"""
    @tornado.web.authenticated
    def get(self):
        task_id = self.get_argument("task_id", "")
        warehouse_id = self.get_argument("warehouse_id", "")

        if task_id:
            task = DeepCollectRepository.get_task(int(task_id))
        elif warehouse_id:
            task = DeepCollectRepository.get_task_by_warehouse(int(warehouse_id))
        else:
            self.write(json.dumps({"success": False, "message": "请提供task_id或warehouse_id"}))
            return

        if task:
            for f in ("steps", "logs"):
                if isinstance(task.get(f), str):
                    try:
                        task[f] = json.loads(task[f])
                    except (json.JSONDecodeError, TypeError):
                        task[f] = []
            self.write(json.dumps({"success": True, "data": task}, ensure_ascii=False))
        else:
            self.write(json.dumps({"success": False, "message": "任务不存在"}))


class DeepCollectResultApiHandler(BaseHandler):
    """获取深度采集结果详情（从deep_collect_data表读取）"""
    @tornado.web.authenticated
    def get(self):
        task_id = self.get_argument("task_id", "")
        warehouse_id = self.get_argument("warehouse_id", "")

        if task_id:
            data = DeepCollectRepository.get_collected_data_by_task(int(task_id))
        elif warehouse_id:
            data = DeepCollectRepository.get_collected_data(int(warehouse_id))
        else:
            self.write(json.dumps({"success": False, "message": "请提供task_id或warehouse_id"}))
            return

        if data:
            result = {
                "id": data["id"],
                "warehouse_id": data["warehouse_id"],
                "task_id": data["task_id"],
                "warehouse_title": data.get("warehouse_title", ""),
                "warehouse_url": data.get("warehouse_url", ""),
                "employee_name": data.get("employee_name", ""),
                "task_status": data.get("task_status", ""),
                "crawled_title": data.get("crawled_title", ""),
                "crawled_content": data.get("crawled_content", ""),
                "analysis_result": data.get("analysis_result", ""),
                "extra_data": data.get("extra_data", {}),
                "completed_at": data.get("completed_at", ""),
                "created_at": data.get("created_at", ""),
            }
            # 兼容旧数据：如果deep_collect_data有内容就用，否则回退到task的result_data
            if not result["analysis_result"] and not result["crawled_content"]:
                task = DeepCollectRepository.get_task(int(result["task_id"])) if result["task_id"] else None
                if task:
                    result["analysis_result"] = task.get("result_data", "")
                    result["task_status"] = task.get("status", "")
                    result["employee_name"] = task.get("employee_name", "")
                    result["completed_at"] = task.get("completed_at", "")
            self.write(json.dumps({"success": True, "data": result}, ensure_ascii=False))
        else:
            # 回退：尝试从deep_collect_tasks读取
            wid = warehouse_id or (DeepCollectRepository.get_task(int(task_id)) if task_id else None)
            if task_id and not warehouse_id:
                task = DeepCollectRepository.get_task(int(task_id))
                wid = task["warehouse_id"] if task else None
            if wid:
                task = DeepCollectRepository.get_task_by_warehouse(int(wid))
                if task:
                    result = {
                        "warehouse_id": task["warehouse_id"],
                        "task_id": task["id"],
                        "warehouse_title": "",
                        "warehouse_url": "",
                        "employee_name": task.get("employee_name", ""),
                        "task_status": task["status"],
                        "analysis_result": task.get("result_data", ""),
                        "completed_at": task.get("completed_at", ""),
                        "crawled_content": "",
                        "crawled_title": "",
                    }
                    wh = DataWarehouseRepository.get_by_id(task["warehouse_id"])
                    if wh:
                        result["warehouse_title"] = wh.get("title", "")
                        result["warehouse_url"] = wh.get("url", "")
                    self.write(json.dumps({"success": True, "data": result}, ensure_ascii=False))
                    return
            self.write(json.dumps({"success": False, "message": "深度采集数据不存在"}))


class DeepCollectStartSingleApiHandler(BaseHandler):
    """单条数据启动深度采集"""
    @tornado.web.authenticated
    async def post(self):
        warehouse_id = self.get_argument("warehouse_id", "")
        if not warehouse_id:
            self.write(json.dumps({"success": False, "message": "warehouse_id不能为空"}))
            return

        task_id = await _start_single_deep_collect(int(warehouse_id))
        if task_id:
            self.write(json.dumps({"success": True, "task_id": task_id, "message": "深度采集任务已启动"}))
        else:
            self.write(json.dumps({"success": False, "message": "启动深度采集失败"}))
