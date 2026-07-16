"""用户侧-前台控制器：对话、模型、数字员工、注册等API"""
import json
import random
import urllib.parse
import time
import tornado.web
from app.controllers.base import BaseHandler
from app.models.user import UserRepository
from app.models.ai_model import AiModelRepository
from app.models.digital_employee import DigitalEmployeeRepository
from app.models.conversation import ConversationRepository
from app.controllers.data_query import DataQueryTool
from app.utils.logger import get_logger

logger = get_logger('user_chat')


class UserChatHandler(BaseHandler):
    """用户侧主页渲染"""
    def get(self):
        if not self.current_user:
            self.redirect("/login")
            return
        user_info = self.get_user_info()
        role_code = user_info.get("role_code", "") if user_info else ""
        self.render("chat.html", title="智能问数", username=self.current_user, role_code=role_code)


class UserRegisterApiHandler(BaseHandler):
    """用户注册API"""
    def post(self):
        username = self.get_body_argument("username", "").strip()
        password = self.get_body_argument("password", "").strip()
        confirm = self.get_body_argument("confirm_password", "").strip()

        if not username or not password:
            self.write(json.dumps({"success": False, "message": "用户名和密码不能为空"}))
            return
        if len(username) < 2 or len(username) > 50:
            self.write(json.dumps({"success": False, "message": "用户名长度2-50个字符"}))
            return
        if len(password) < 6:
            self.write(json.dumps({"success": False, "message": "密码长度不能少于6位"}))
            return
        if password != confirm:
            self.write(json.dumps({"success": False, "message": "两次密码输入不一致"}))
            return

        # 检查用户名是否已存在
        existing = UserRepository.get_user_by_username(username)
        if existing:
            self.write(json.dumps({"success": False, "message": "用户名已存在"}))
            return

        # 创建用户（默认role_id=2 普通用户）
        ok = UserRepository.create_user(username, password, role_id=2)
        if ok:
            self.write(json.dumps({"success": True, "message": "注册成功"}))
        else:
            self.write(json.dumps({"success": False, "message": "注册失败，请稍后重试"}))


class UserModelsApiHandler(BaseHandler):
    """获取用户可用的模型列表"""
    def get(self):
        models = AiModelRepository.get_all(page=1, page_size=100, search=None, category=None)
        data = models.get("data", [])
        # 精简返回字段
        result = []
        for m in data:
            result.append({
                "id": m["id"],
                "name": m["name"],
                "model_name": m["model_name"],
                "provider": m["provider"],
                "is_default": m["is_default"],
                "category": m["category"]
            })
        self.write(json.dumps({"success": True, "data": result}))


class UserDigitalEmployeesApiHandler(BaseHandler):
    """获取用户可调用的数字员工列表（供@菜单使用）"""
    def get(self):
        result = DigitalEmployeeRepository.get_all(page=1, page_size=100)
        employees = result.get("data", [])
        data = []
        for e in employees:
            data.append({
                "id": e["id"],
                "name": e["name"],
                "type": e["type"],
                "description": e["description"],
                "model_id": e["model_id"],
                "system_prompt": e.get("system_prompt", ""),
                "api_url": e.get("api_url", ""),
                "api_method": e.get("api_method", "GET"),
                "api_headers": e.get("api_headers", "{}"),
                "api_params": e.get("api_params", "{}"),
                "api_response_template": e.get("api_response_template", ""),
                "card_config": e.get("card_config", ""),
                "status": e["status"]
            })
        self.write(json.dumps({"success": True, "data": data}))


class UserConversationsApiHandler(BaseHandler):
    """用户对话CRUD API - 实现数据隔离"""
    def get(self):
        """获取当前用户的所有对话"""
        if not self.current_user:
            self.write(json.dumps({"success": False, "message": "未登录"}))
            return
        user = UserRepository.get_user_by_username(self.current_user)
        if not user:
            self.write(json.dumps({"success": False, "message": "用户不存在"}))
            return
        page = int(self.get_argument("page", "1"))
        result = ConversationRepository.get_by_user(user["id"], page=page)
        self.write(json.dumps({"success": True, "data": result["data"], "total": result["total"]}))

    def post(self):
        """创建新对话"""
        if not self.current_user:
            self.write(json.dumps({"success": False, "message": "未登录"}))
            return
        user = UserRepository.get_user_by_username(self.current_user)
        if not user:
            self.write(json.dumps({"success": False, "message": "用户不存在"}))
            return
        data = json.loads(self.request.body or "{}")
        title = data.get("title", "新对话")
        messages = data.get("messages", [])
        conv_id = ConversationRepository.create(user["id"], title=title, messages=messages)
        conv = ConversationRepository.get_by_id(conv_id, user["id"])
        self.write(json.dumps({"success": True, "data": conv}))

    def put(self):
        """更新对话"""
        if not self.current_user:
            self.write(json.dumps({"success": False, "message": "未登录"}))
            return
        user = UserRepository.get_user_by_username(self.current_user)
        if not user:
            self.write(json.dumps({"success": False, "message": "用户不存在"}))
            return
        data = json.loads(self.request.body or "{}")
        conv_id = data.get("id")
        if not conv_id:
            self.write(json.dumps({"success": False, "message": "缺少对话ID"}))
            return
        kwargs = {}
        if "title" in data:
            kwargs["title"] = data["title"]
        if "messages" in data:
            kwargs["messages"] = data["messages"]
        ConversationRepository.update(conv_id, user["id"], **kwargs)
        conv = ConversationRepository.get_by_id(conv_id, user["id"])
        self.write(json.dumps({"success": True, "data": conv}))

    def delete(self):
        """删除对话"""
        if not self.current_user:
            self.write(json.dumps({"success": False, "message": "未登录"}))
            return
        user = UserRepository.get_user_by_username(self.current_user)
        if not user:
            self.write(json.dumps({"success": False, "message": "用户不存在"}))
            return
        conv_id = int(self.get_argument("id", "0"))
        ConversationRepository.delete(conv_id, user["id"])
        self.write(json.dumps({"success": True}))


class UserChatApiHandler(BaseHandler):
    """用户侧SSE流式对话API - 支持@数字员工、默认模型、意图识别和数据查询"""

    # 英文字段名 → 中文显示名映射
    CN_COLUMN_NAMES = {
        "total_records": "总记录数",
        "deep_collected_count": "深度采集数",
        "earliest_collection": "最早采集时间",
        "latest_collection": "最晚采集时间",
        "id": "编号",
        "title": "标题",
        "url": "链接",
        "summary": "摘要",
        "source_name": "来源",
        "keyword": "关键词",
        "collected_at": "采集时间",
        "updated_at": "更新时间",
        "created_at": "创建时间",
        "name": "名称",
        "type": "类型",
        "description": "描述",
        "status": "状态",
        "username": "用户名",
        "role_id": "角色编号",
        "sort_order": "排序",
        "count": "数量",
        "data": "数据量",
    }

    DATA_INTENT_KEYWORDS = [
        "数据", "查询", "统计", "总数", "多少", "几个", "列表", "记录",
        "仓库", "采集", "数据量", "数据概况", "分析", "趋势", "分布"
    ]

    CHART_INTENT_KEYWORDS = [
        "图表", "chart", "统计图", "柱状", "饼图", "折线", "趋势图",
        "分布图", "echart", "可视化", "柱形", "扇形"
    ]

    ANALYSIS_INTENT_KEYWORDS = [
        "分析", "统计", "趋势", "分布", "占比", "变化", "增长",
        "减少", "对比", "比较", "占比", "比例", "汇总", "最高",
        "最低", "平均", "总和"
    ]

    RELATIONSHIP_INTENT_KEYWORDS = [
        "关系", "关联", "关联分析", "数据图谱", "关系挖掘", "关联度",
        "覆盖", "交集", "映射", "关系图"
    ]

    REPORT_INTENT_KEYWORDS = [
        "报告", "报表", "报告生成", "分析报告", "数据报告", "汇报"
    ]

    def _detect_intent(self, text):
        """检测用户意图：data_query, chart_request, analysis, relationship, report, general_chat"""
        if not text:
            return "general_chat"
        text_lower = text.lower()
        # 优先级：relationship > report > chart > analysis > data_query
        for kw in self.RELATIONSHIP_INTENT_KEYWORDS:
            if kw in text_lower:
                return "relationship"
        for kw in self.REPORT_INTENT_KEYWORDS:
            if kw in text_lower:
                return "report"
        for kw in self.CHART_INTENT_KEYWORDS:
            if kw in text_lower:
                return "chart_request"
        for kw in self.ANALYSIS_INTENT_KEYWORDS:
            if kw in text_lower:
                return "analysis"
        for kw in self.DATA_INTENT_KEYWORDS:
            if kw in text_lower:
                return "data_query"
        return "general_chat"

    async def _handle_data_query(self, msg_list, model, employee_name=None):
        """处理数据查询意图：生成SQL→执行→LLM分析→返回结果"""
        last_user_msg = ""
        for msg in reversed(msg_list):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        if not last_user_msg:
            return None

        # 检测子意图
        intent = self._detect_intent(last_user_msg)
        if intent in ("analysis", "relationship"):
            query_type = intent
        elif intent == "report":
            query_type = "analysis"
        else:
            query_type = "data_query"

        # 使用LLM生成SQL
        sql = await DataQueryTool.generate_sql_with_llm(last_user_msg, model, query_type=query_type)
        if not sql:
            return {"success": False, "error": "无法理解您的数据查询需求，请换个方式描述"}

        # 执行安全查询
        result = DataQueryTool.execute_safe_query(sql)
        if not result["success"]:
            return {"success": False, "error": result.get("error", "数据查询失败")}

        data = result["data"]
        columns = result["columns"]
        row_count = result["row_count"]

        if row_count == 0:
            result_text = "查询完成，没有找到符合条件的数据。"
            return {"success": True, "data": result_text, "data_rows": [], "row_count": 0, "columns": []}

        # 构造数据概览文本（基本显示）
        lines = [f"**数据查询结果**（共 {row_count} 条记录）"]
        for i, row in enumerate(data[:10]):
            row_parts = []
            for col in columns[:5]:
                val = row.get(col, "")
                if val:
                    cn_name = self.CN_COLUMN_NAMES.get(col, col)
                    row_parts.append(f"**{cn_name}**: {val}")
            if row_parts:
                lines.append(f"\n{i+1}. {' | '.join(row_parts)}")
        if row_count > 10:
            lines.append(f"\n... 共 {row_count} 条记录（仅展示前10条）")

        basic_text = "\n".join(lines)

        # LLM分析结果（针对analysis/relationship/report 和返回数据量合适的情况）
        analysis_text = None
        if intent in ("analysis", "relationship", "report") and row_count > 0 and row_count <= 50:
            analysis_result = await DataQueryTool.analyze_results_with_llm(
                last_user_msg, sql, data, columns, model
            )
            if analysis_result:
                analysis_text = analysis_result

        # 检测是否需要图表 — 始终尝试，_prepare_chart_data 内部判断数据是否适合做图
        chart_data = None
        if data:
            chart_data = self._prepare_chart_data(data, columns)
            print(f"[PREPARE_CHART] data_rows={len(data)} columns={columns} chart={chart_data is not None} type={chart_data.get('chart_type') if chart_data else 'N/A'}")

        # 最终输出：如果LLM分析成功，用分析结果 + 数据表格
        if analysis_text:
            result_text = analysis_text
        else:
            result_text = basic_text

        # 准备表格数据（始终生成）
        table_data = self._prepare_table_data(data, columns)

        return {
            "success": True,
            "data": result_text,
            "data_rows": data,
            "chart_data": chart_data,
            "table_data": table_data,
            "analysis_text": analysis_text or basic_text,
            "basic_text": basic_text,
            "row_count": row_count,
            "columns": columns,
            "intent": intent,
            "sql": sql
        }

    # 时间字段关键词（用于检测时间序列）
    TIME_COLUMN_KEYWORDS = ["time", "date", "datetime", "created", "updated", "collected",
                            "时间", "日期", "创建", "更新", "采集"]
    # 分类字段关键词
    CATEGORY_COLUMN_KEYWORDS = ["name", "source", "category", "type", "status", "title",
                                "名称", "来源", "分类", "类型", "状态", "标题"]
    # 数值字段关键词
    NUMERIC_COLUMN_KEYWORDS = ["count", "total", "sum", "amount", "num", "size", "avg",
                               "数量", "总数", "合计", "平均", "计数", "统计"]

    def _prepare_chart_data(self, data, columns):
        """根据数据准备图表配置 — 支持 line/pie/bar 三种图表类型"""
        if not data or not columns:
            return None

        # 分类列：时间列 vs 普通分类列 vs 数值列
        time_cols = []
        numeric_cols = []
        category_cols = []

        for col in columns:
            col_lower = col.lower()
            # 检测时间字段
            is_time = any(kw in col_lower for kw in self.TIME_COLUMN_KEYWORDS)
            if is_time:
                time_cols.append(col)
                continue

            # 检测数值字段
            has_number = any(
                isinstance(row.get(col), (int, float)) or
                (isinstance(row.get(col), str) and row[col].replace('.', '').replace('-', '').isdigit())
                for row in data[:5]
            )
            if has_number:
                numeric_cols.append(col)
            else:
                category_cols.append(col)

        if not numeric_cols:
            return None

        num_col = numeric_cols[0]  # 首选数值列

        # 决策图表类型
        if time_cols:
            # 有时间字段 → 折线图
            return self._build_line_chart(data, time_cols[0], num_col, columns)
        elif category_cols and len(set(str(r.get(category_cols[0], "")) for r in data[:20])) <= 6:
            # 分类 ≤ 6 → 饼图
            return self._build_pie_chart(data, category_cols[0], num_col)
        elif category_cols:
            # 分类多 → 柱状图
            return self._build_bar_chart(data, category_cols[0], num_col)
        elif time_cols:
            return self._build_line_chart(data, time_cols[0], num_col, columns)
        else:
            # 只有数值列，无分类 → 柱状图
            return self._build_bar_chart(data, columns[0], num_col)

    def _build_line_chart(self, data, time_col, num_col, all_columns):
        """构建折线图配置（时间序列）"""
        x_data = []
        values = []
        for row in data[:30]:
            t_val = str(row.get(time_col, ""))
            # 截取日期部分 (YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS → YYYY-MM-DD)
            if len(t_val) >= 10:
                t_val = t_val[:10]
            elif len(t_val) > 16:
                t_val = t_val[:16]
            n_val = self._to_number(row.get(num_col, 0))
            x_data.append(t_val)
            values.append(n_val)

        return {
            "chart_type": "line",
            "title": f"{num_col} 趋势",
            "x_data": x_data,
            "series": [{"name": num_col, "data": values}],
            "category_label": time_col,
            "value_label": num_col
        }

    def _build_pie_chart(self, data, cat_col, num_col):
        """构建饼图配置"""
        categories = []
        values = []
        for row in data[:20]:
            cat_val = str(row.get(cat_col, ""))[:20]
            n_val = self._to_number(row.get(num_col, 0))
            categories.append(cat_val)
            values.append(n_val)

        if len(categories) == 0:
            return None

        return {
            "chart_type": "pie",
            "title": f"{cat_col} 分布",
            "categories": categories,
            "values": values,
            "category_label": cat_col,
            "value_label": num_col
        }

    def _build_bar_chart(self, data, cat_col, num_col):
        """构建柱状图配置"""
        categories = []
        values = []
        for row in data[:20]:
            cat_val = str(row.get(cat_col, ""))[:20]
            n_val = self._to_number(row.get(num_col, 0))
            categories.append(cat_val)
            values.append(n_val)

        if len(categories) == 0:
            return None

        return {
            "chart_type": "bar",
            "title": f"{cat_col} - {num_col}",
            "categories": categories,
            "values": values,
            "category_label": cat_col,
            "value_label": num_col
        }

    @staticmethod
    def _to_number(val):
        """将值转换为数字，失败返回0"""
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            try:
                return float(val.replace('%', '').replace(',', '').strip())
            except (ValueError, TypeError):
                return 0
        return 0

    @staticmethod
    def _prepare_table_data(data, columns, max_rows=100):
        """将查询结果格式化为前端表格数据"""
        return {
            "columns": columns,
            "rows": data[:max_rows],
            "total_rows": len(data),
            "display_rows": min(len(data), max_rows)
        }
    async def post(self):
        if not self.current_user:
            self.write(json.dumps({"success": False, "message": "未登录"}))
            return

        start_time = time.time()
        messages = self.get_argument("messages", "")
        model_id = self.get_argument("model_id", "")
        employee_id = self.get_argument("employee_id", "")
        system_prompt = self.get_argument("system_prompt", "")

        # 解析消息
        try:
            msg_list = json.loads(messages) if messages else []
        except json.JSONDecodeError:
            msg_list = []

        # 确定使用的模型
        model = None
        final_system_prompt = system_prompt

        # 如果指定了数字员工，优先使用数字员工的模型
        if employee_id:
            employee = DigitalEmployeeRepository.get_by_id(int(employee_id))
            if employee and employee.get("status") == 1:
                if employee["type"] == "llm":
                    # LLM型：使用关联模型
                    if employee.get("model_id"):
                        model = AiModelRepository.get_by_id(employee["model_id"])
                    # 使用数字员工的系统提示词
                    if employee.get("system_prompt"):
                        final_system_prompt = employee["system_prompt"]

                    # 如果启用了crawl4ai，检测用户消息中的URL并爬取
                    if employee.get("crawl4ai_enabled") == 1:
                        import re
                        last_user_content = None
                        for msg in reversed(msg_list):
                            if msg.get("role") == "user":
                                last_user_content = msg.get("content", "")
                                break
                        if last_user_content:
                            urls = re.findall(r'https?://[^\s<>"\')]+', last_user_content)
                            if urls:
                                try:
                                    from crawl4ai import AsyncWebCrawler
                                    async with AsyncWebCrawler() as crawler:
                                        result = await crawler.arun(url=urls[0])
                                        if result and result.success and result.markdown:
                                            crawled = result.markdown[:5000]
                                            msg_list.append({
                                                "role": "user",
                                                "content": f"以下是从用户提供的URL {urls[0]} 中爬取到的网页内容，请基于此内容回答用户问题：\n\n{crawled}"
                                            })
                                except Exception as e:
                                    logger.error(f"Crawl4AI爬取失败: {e}")
                elif employee["type"] == "api":
                    # API型：直接调用API端点，不经过模型
                    await self._call_api_employee(employee, msg_list, start_time=start_time)
                    return

        # 意图识别：无指定数字员工时，检测是否为数据查询/图表/分析/关系请求
        if not employee_id:
            last_msg = ""
            for msg in reversed(msg_list):
                if msg.get("role") == "user":
                    last_msg = msg.get("content", "")
                    break
            if last_msg:
                intent = self._detect_intent(last_msg)
                if intent in ("data_query", "chart_request", "analysis", "relationship", "report"):
                    # 数据查询模型获取：优先用户选择的 model_id，再 fallback 到默认模型
                    if not model:
                        if model_id:
                            model = AiModelRepository.get_by_id(int(model_id))
                        if not model:
                            model = AiModelRepository.get_default()
                    if model:
                        data_result = await self._handle_data_query(msg_list, model)
                        if data_result and data_result.get("success"):
                            result_text = data_result["data"]
                            chart_data = data_result.get("chart_data")
                            table_data = data_result.get("table_data")
                            data_intent = data_result.get("intent", "data_query")
                            # DEBUG
                            print(f"[DATA_QUERY] intent={data_intent} chart={chart_data is not None} chart_type={chart_data.get('chart_type') if chart_data else 'N/A'} table_rows={table_data.get('total_rows') if table_data else 0} row_count={data_result.get('row_count')}")
                            # 通过SSE返回数据查询结果
                            self.set_header("Content-Type", "text/event-stream")
                            self.set_header("Cache-Control", "no-cache")
                            self.set_header("Connection", "keep-alive")
                            self.set_header("X-Accel-Buffering", "no")

                            # 如果有数据结果，同时生成卡片数据（中文字段名）
                            extra_data = {}
                            card_fields = []
                            if chart_data:
                                extra_data["chart"] = chart_data
                            if table_data:
                                extra_data["table"] = table_data
                            if data_result.get("row_count", 0) > 0 and data_result.get("columns"):
                                card_fields = []
                                data_rows = data_result.get("data_rows", [])
                                if data_result.get("row_count") == 1 and data_rows:
                                    # 单条记录显示为卡片字段
                                    row = data_rows[0]
                                    for col in data_result["columns"][:8]:
                                        val = row.get(col, "")
                                        if val:
                                            cn_name = self.CN_COLUMN_NAMES.get(col, col)
                                            card_fields.append({"key": col, "label": cn_name, "value": str(val)})
                                if card_fields:
                                    extra_data["cardFields"] = card_fields
                                    extra_data["cardTitle"] = "数据概览"

                            # 决定响应格式：chart > table > data_card > text
                            if chart_data:
                                response_format = "chart_card"
                            elif table_data and table_data.get("display_rows", 0) > 0:
                                response_format = "table"
                            elif card_fields:
                                response_format = "data_card"
                            else:
                                response_format = "text"

                            response_data = json.dumps({
                                "choices": [{"delta": {"content": result_text}, "index": 0}],
                                "employee_name": "数据分析",
                                "employee_response_format": response_format,
                                "extra_data": extra_data,
                                "intent": data_intent,
                                "row_count": data_result.get("row_count", 0)
                            })
                            self.write(f"data: {response_data}\n\n")
                            self.write(f"data: {json.dumps({'usage': {'completion_tokens': 0, 'total_time_ms': int((time.time() - start_time) * 1000)}})}\n\n")
                            self.write("data: [DONE]\n\n")
                            self.finish()
                            return
                        # 查询失败则回退到普通AI对话

        # 如果数字员工没有关联模型，或没有指定数字员工，使用传入model_id或默认模型
        if not model and model_id:
            model = AiModelRepository.get_by_id(int(model_id))
        if not model:
            model = AiModelRepository.get_default()

        if not model:
            self.write(json.dumps({"success": False, "message": "无可用模型，请联系管理员配置"}))
            return

        # 构建消息列表
        api_messages = []
        if final_system_prompt:
            api_messages.append({"role": "system", "content": final_system_prompt})
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
        temperature = float(model.get("temperature", 0.7))
        top_p = float(model.get("top_p", 1.0))
        max_tokens = int(model.get("max_tokens", 4096))
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

        token_count = 0
        buffer = ""

        def streaming_callback(chunk):
            nonlocal token_count, buffer
            if not chunk:
                return
            try:
                text = chunk.decode("utf-8", errors="replace")
            except Exception:
                text = str(chunk)

            buffer += text
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
                        if "usage" in data_json and data_json["usage"]:
                            token_count = data_json["usage"].get("completion_tokens", 0) or data_json["usage"].get("total_tokens", 0) or 0
                        # 直接转发原始SSE数据
                        self.write(f"data: {data_str}\n\n")
                        IOLoop.current().add_callback(self.flush)
                    except json.JSONDecodeError:
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
            await client.fetch(request)
        except Exception as e:
            error_msg = str(e)
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
        if token_count > 0 and model:
            current = model.get("token_count", 0) or 0
            AiModelRepository.update(model["id"], token_count=current + token_count)

        # 发送响应时间 + token用量元数据
        elapsed = time.time() - start_time
        usage_meta = json.dumps({
            "usage": {
                "completion_tokens": token_count,
                "total_time_ms": int(elapsed * 1000)
            }
        })
        self.write(f"data: {usage_meta}\n\n")
        self.write("data: [DONE]\n\n")
        self.finish()

    async def _call_api_employee(self, employee, msg_list, start_time=None):
        """调用API型数字员工

        架构说明：
          - 使用 Tornado AsyncHTTPClient 异步调用，不阻塞事件循环
          - 内置 Mock API（新闻/音乐/电影）直接调用本地函数，避免 HTTP 递归
          - 外部 API 通过 HTTP 异步调用，支持 GET/POST
          - 若需新增内置 API，在 _call_builtin_api() 中注册即可
        """
        from tornado.ioloop import IOLoop
        from tornado.httpclient import AsyncHTTPClient, HTTPRequest

        if start_time is None:
            start_time = time.time()

        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        self.set_header("X-Accel-Buffering", "no")

        try:
            api_url = employee.get("api_url", "")
            api_method = employee.get("api_method", "GET").upper()
            api_headers = json.loads(employee.get("api_headers", "{}") or "{}")
            api_params = json.loads(employee.get("api_params", "{}") or "{}")
            template = employee.get("api_response_template", "")

            # 如果有最后一条用户消息，提取内容填充参数
            user_content = ""
            if msg_list and msg_list[-1].get("role") == "user":
                user_content = msg_list[-1].get("content", "")

            # 在URL中替换占位符（始终替换，空值时清空占位符避免残余）
            query_val = urllib.parse.quote(user_content) if user_content else ""
            city_val = urllib.parse.quote(user_content) if user_content else ""
            api_url = api_url.replace("{query}", query_val)
            api_url = api_url.replace("{city}", city_val)

            # 填充参数模板，手动拼接避免urlencode二次编码（如%C→%25C）
            filled_params = {}
            raw_query_parts = []
            for k, v in api_params.items():
                if isinstance(v, str) and "{city}" in v and user_content:
                    v = v.replace("{city}", user_content)
                elif isinstance(v, str) and "{query}" in v and user_content:
                    v = v.replace("{query}", user_content)
                raw_query_parts.append(f"{k}={v}")
            raw_query = "&".join(raw_query_parts)
            if raw_query:
                api_url = api_url + "?" + raw_query

            # ---- 优先：本地内置 API 直调（零网络开销、无死锁风险） ----
            if "/api/mock/" in api_url or "/mock/" in api_url:
                body_text = _call_builtin_mock_api(api_url)
            else:
                # ---- 外部 HTTP API：异步调用 ----
                http_client = AsyncHTTPClient()
                if api_method == "GET":
                    resp = await http_client.fetch(api_url, headers=api_headers,
                                                   request_timeout=15, raise_error=False)
                else:
                    body = urllib.parse.urlencode(filled_params) if filled_params else None
                    req = HTTPRequest(url=api_url, method="POST", headers=api_headers,
                                      body=body, request_timeout=15)
                    resp = await http_client.fetch(req, raise_error=False)
                body_text = (resp.body or b"").decode("utf-8", errors="replace")

            result_text = body_text
            employee_name = employee.get("name", "")
            response_format = "text"
            extra_data = {}

            # 解析 JSON 响应体
            try:
                resp_json = json.loads(body_text)
            except (json.JSONDecodeError, ValueError):
                resp_json = None

            # 检查外部 HTTP 错误（仅当不是内置API返回的JSON时检查 resp.code）
            if resp_json is None and "/api/mock/" not in api_url and "/mock/" not in api_url:
                result_text = f"【服务暂不可用】{employee_name}返回了无法解析的响应"

            # 模板提取模式（有 api_response_template 配置）
            if resp_json and template:
                try:
                    if "天气" in employee_name:
                        cc = resp_json.get("current_condition", [{}])[0]
                        weather_desc = ""
                        lang_zh = cc.get("lang_zh", [])
                        if lang_zh and lang_zh[0].get("value"):
                            weather_desc = lang_zh[0]["value"]
                        else:
                            weather_desc = cc.get("weatherDesc", [{}])[0].get("value", "")
                        temp = cc.get("temp_C", "?")
                        humidity = cc.get("humidity", "?")
                        wind = cc.get("windspeedKmph", "?")
                        wind_dir = cc.get("winddir16Point", "?")
                        pressure = cc.get("pressure", "?")
                        visibility = cc.get("visibility", "?")
                        city_name = user_content if user_content else "当前城市"
                        result_text = (
                            f"【{city_name}天气】\n"
                            f"天气：{weather_desc}\n"
                            f"温度：{temp}°C\n"
                            f"湿度：{humidity}%\n"
                            f"风速：{wind} km/h（{wind_dir}）\n"
                            f"能见度：{visibility} km\n"
                            f"气压：{pressure} hPa"
                        )
                        response_format = "weather_card"
                        extra_data = {
                            "city": city_name, "weather": weather_desc,
                            "temperature": temp, "humidity": humidity,
                            "wind_speed": wind, "wind_dir": wind_dir,
                            "pressure": pressure, "visibility": visibility
                        }
                    else:
                        keys = template.split(",")
                        extracted = []
                        for key in keys:
                            key = key.strip()
                            parts = key.split(".")
                            val = resp_json
                            for p in parts:
                                if isinstance(val, dict):
                                    val = val.get(p, "")
                                elif isinstance(val, list) and p.isdigit():
                                    idx = int(p)
                                    val = val[idx] if idx < len(val) else ""
                                else:
                                    val = ""
                                    break
                            if val:
                                extracted.append(f"{parts[-1]}: {val}")
                        if extracted:
                            result_text = "\n".join(extracted)

                    card_config = employee.get("card_config", "{}")
                    if card_config and response_format == "text":
                        try:
                            card_cfg = json.loads(card_config) if isinstance(card_config, str) else card_config
                            if card_cfg.get("enabled"):
                                card_fields = []
                                for field in card_cfg.get("fields", []):
                                    key = field.get("key", "")
                                    label = field.get("label", key)
                                    val = resp_json
                                    for p in key.split("."):
                                        if isinstance(val, dict):
                                            val = val.get(p, "")
                                        elif isinstance(val, list) and p.isdigit():
                                            idx = int(p)
                                            val = val[idx] if idx < len(val) else ""
                                        else:
                                            val = ""
                                            break
                                    unit = field.get("unit", "")
                                    display_val = f"{val}{unit}" if val and unit else (str(val) if val else "-")
                                    card_fields.append({"key": key, "label": label, "value": display_val})
                                if card_fields:
                                    response_format = "data_card"
                                    extra_data = {
                                        "cardTitle": card_cfg.get("title", "数据卡片"),
                                        "cardFields": card_fields,
                                        "cardConfig": card_cfg
                                    }
                        except Exception:
                            pass
                except Exception:
                    pass
            elif resp_json:
                # 无 template：检查是否内置 Mock API 或第三方 API 的自描述格式
                if resp_json.get("success") and "data" in resp_json:
                    data = resp_json["data"]
                    if data.get("responseFormat"):
                        response_format = data["responseFormat"]
                        extra_data = data.get("extraData", {})
                        txt = data.get("content", "")
                        if txt:
                            result_text = txt

            elapsed = time.time() - start_time
            response_data = json.dumps({
                "choices": [{
                    "delta": {"content": result_text},
                    "index": 0
                }],
                "employee_name": employee_name,
                "employee_response_format": response_format,
                "extra_data": extra_data
            }, ensure_ascii=False)
            self.write(f"data: {response_data}\n\n")
            IOLoop.current().add_callback(self.flush)

            usage_meta = json.dumps({
                "usage": {
                    "completion_tokens": 0,
                    "total_time_ms": int(elapsed * 1000)
                }
            })
            self.write(f"data: {usage_meta}\n\n")
        except Exception as e:
            error_response = json.dumps({"error": {"message": f"数字员工调用失败: {str(e)[:100]}", "type": "employee_error"}})
            self.write(f"data: {error_response}\n\n")
            IOLoop.current().add_callback(self.flush)

        self.write("data: [DONE]\n\n")
        self.finish()


# ============================================================
#  内置 Mock API 直调函数（注册点：新增内置API在此添加）
# ============================================================

# 延迟导入避免循环依赖（运行时导入 mock_apis 模块的处理函数）
def _call_builtin_mock_api(api_url):
    """处理内置 Mock API 的直接调用（不走 HTTP，零网络开销）

    注册方式：在此函数中添加 elif 分支，匹配 api_url 特征即可
    返回: JSON 字符串
    """
    import urllib.parse as url_parse

    parsed = url_parse.urlparse(api_url)
    path = parsed.path
    query = url_parse.parse_qs(parsed.query)

    # 新闻 Mock API
    if "mock/news" in path:
        from app.controllers.mock_apis import _get_live_news
        items, fetch_time = _get_live_news()
        text_lines = [f"📰 **热门新闻速递**（{fetch_time}）\n"]
        for i, item in enumerate(items, 1):
            text_lines.append(
                f"{i}. **[{item['title']}]({item['link']})**\n"
                f"   📍 {item['source']}{'  🕐 ' + item['time'] if item.get('time') else ''}\n"
                f"   {item['summary']}"
            )
        return json.dumps({
            "success": True,
            "data": {
                "content": "\n\n".join(text_lines),
                "responseFormat": "news_list",
                "extraData": {"list": items}
            }
        }, ensure_ascii=False)

    # 音乐 Mock API
    if "mock/music" in path:
        from app.controllers.mock_apis import _get_random_music_song
        song = _get_random_music_song()
        return json.dumps({
            "success": True,
            "data": {
                "content": f"🎵 **{song['song']}** — {song['artist']}",
                "responseFormat": "music_player",
                "extraData": {
                    "song": song["song"],
                    "artist": song["artist"],
                    "cover": song["cover"],
                    "url": song["url"]
                }
            }
        }, ensure_ascii=False)

    # 电影 Mock API
    if "mock/movie" in path:
        from app.controllers.mock_apis import _search_movie, _get_random_movie
        keyword = (query.get("keyword", [""])[0]).strip()
        if keyword:
            results = _search_movie(keyword)
            if results:
                movie = random.choice(results)
            else:
                return json.dumps({
                    "success": True,
                    "data": {
                        "content": f"😅 未找到与「{keyword}」相关的电影，试试其他关键词吧！",
                        "responseFormat": "text",
                        "extraData": {}
                    }
                }, ensure_ascii=False)
        else:
            movie = _get_random_movie()
        return json.dumps({
            "success": True,
            "data": {
                "content": (f"🎬 **{movie['title']}**（{movie['year']}）\n\n"
                           f"🎥 导演：{movie['director']}\n"
                           f"👥 演员：{' / '.join(movie['actors'][:5])}\n"
                           f"⭐ 评分：{movie['rating']}\n\n{movie['summary']}"),
                "responseFormat": "movie_detail",
                "extraData": movie
            }
        }, ensure_ascii=False)

    # 天气 Mock API
    if "mock/weather" in path:
        city = (query.get("city", ["成都"])[0]).strip() or "成都"
        weather_map = {
            "成都": {"desc": "多云转晴", "temp": 32, "humidity": 55, "wind": "东北风 3级", "aqi": 72},
            "北京": {"desc": "晴", "temp": 28, "humidity": 35, "wind": "北风 4级", "aqi": 45},
            "上海": {"desc": "小雨", "temp": 26, "humidity": 78, "wind": "东南风 2级", "aqi": 58},
            "广州": {"desc": "雷阵雨", "temp": 33, "humidity": 82, "wind": "南风 3级", "aqi": 40},
            "深圳": {"desc": "多云", "temp": 31, "humidity": 68, "wind": "西南风 2级", "aqi": 35},
            "杭州": {"desc": "阴转多云", "temp": 29, "humidity": 62, "wind": "东风 2级", "aqi": 55},
            "武汉": {"desc": "晴", "temp": 34, "humidity": 45, "wind": "南风 3级", "aqi": 60},
            "西安": {"desc": "多云", "temp": 30, "humidity": 40, "wind": "东北风 2级", "aqi": 68},
            "重庆": {"desc": "阴", "temp": 35, "humidity": 70, "wind": "北风 1级", "aqi": 80},
        }
        data = weather_map.get(city, weather_map["成都"])
        text = (
            f"【{city}天气】\n"
            f"天气：{data['desc']}\n"
            f"温度：{data['temp']}°C\n"
            f"湿度：{data['humidity']}%\n"
            f"风力：{data['wind']}\n"
            f"空气质量指数(AQI)：{data['aqi']}"
        )
        return json.dumps({
            "success": True,
            "data": {
                "content": text,
                "responseFormat": "weather_card",
                "extraData": dict(data, city=city)
            }
        }, ensure_ascii=False)

    # 默认：原样返回（未知的内置 API）
    return json.dumps({"success": False, "message": f"未知的内置 API: {path}"}, ensure_ascii=False)
