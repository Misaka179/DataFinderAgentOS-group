"""数据查询分析API - 安全地与数据库对话，不暴露SQL"""
import json
import re
import sqlite3
from app.models.db import get_connection
from app.models.ai_model import AiModelRepository


class DataQueryTool:
    """安全的数据查询工具，仅允许SELECT操作，支持多维度分析"""

    # 允许查询的表名白名单（优先排序：采集数据优先）
    ALLOWED_TABLES = {
        "data_warehouse", "deep_collect_data", "deep_collect_tasks", "watch_sources",
        "watch_collected_data", "users", "digital_employees", "ai_models", "conversations"
    }

    # 表结构描述（含关系信息，采集数据表排前面）
    TABLE_SCHEMAS = {
        "data_warehouse": {
            "description": "数据仓库——存储采集到的网页数据（核心分析表）",
            "columns": "id, title(标题), url(链接), summary(摘要), source_name(来源名称), keyword(采集关键词), source_id, is_deep_collected(是否已深度采集:1是0否), collected_at(采集时间), updated_at",
            "relationships": "source_id → watch_sources.id, id → deep_collect_data.warehouse_id, id → deep_collect_tasks.warehouse_id"
        },
        "deep_collect_data": {
            "description": "深度采集数据——存储深度采集的详细内容和AI分析结果",
            "columns": "id, warehouse_id(关联数据仓库ID), task_id, crawled_title(采集标题), crawled_content(正文内容), analysis_result(AI分析结果), extra_data(额外数据JSON), created_at",
            "relationships": "warehouse_id → data_warehouse.id, task_id → deep_collect_tasks.id"
        },
        "deep_collect_tasks": {
            "description": "深度采集任务——记录深度采集的任务状态和进度",
            "columns": "id, warehouse_id(关联数据仓库ID), employee_id, employee_name(执行员工), status(状态pending/running/completed/failed), progress(进度0-100), steps, logs, result_data, error_message, started_at, completed_at, created_at",
            "relationships": "warehouse_id → data_warehouse.id"
        },
        "watch_sources": {
            "description": "瞭望源——配置的数据采集来源",
            "columns": "id, name(名称), url_template(URL模板), method(请求方法GET/POST), headers(请求头), keyword_param(关键词参数名), page_param(页码参数), page_step(每页步长), status(状态1启用0停用), created_at, updated_at"
        },
        "watch_collected_data": {
            "description": "瞭望采集数据——瞭望采集到的原始数据",
            "columns": "id, source_id(来源ID), keyword(关键词), title(标题), url(链接), summary(摘要), source_name(来源名称), collected_at(采集时间)",
            "relationships": "source_id → watch_sources.id"
        },
        "users": {
            "description": "系统用户",
            "columns": "id, username(用户名), role_id(角色), status(状态1启用0停用), created_at"
        },
        "digital_employees": {
            "description": "数字员工配置",
            "columns": "id, name(名称), type(类型llm/api), description(描述), status(状态), crawl4ai_enabled(是否启用爬虫)"
        },
        "conversations": {
            "description": "用户对话记录",
            "columns": "id, user_id, title(标题), created_at, updated_at"
        }
    }

    @staticmethod
    def get_schema_context(is_analysis=False):
        """获取表结构描述文本（供AI参考）
        is_analysis=True时包含更详细的分析提示
        """
        parts = []
        # 优先展示采集数据表
        priority_tables = ["data_warehouse", "deep_collect_data", "deep_collect_tasks", "watch_sources"]
        other_tables = [t for t in DataQueryTool.TABLE_SCHEMAS if t not in priority_tables]

        for table in priority_tables + other_tables:
            if table in DataQueryTool.ALLOWED_TABLES:
                info = DataQueryTool.TABLE_SCHEMAS[table]
                desc = info["description"]
                cols = info["columns"]
                rel = info.get("relationships", "")
                part = f"表 {table} ({desc}): 列={cols}"
                if rel:
                    part += f" | 关联={rel}"
                parts.append(part)

        schema_text = "\n".join(parts)

        if is_analysis:
            schema_text += """

分析注意事项：
1. 优先使用 data_warehouse（数据仓库）进行统计分析，这是最核心的数据表
2. 分析数据量时，使用 COUNT(*) 统计记录数
3. 分析时间趋势时，使用 collected_at / created_at 字段进行时间分组
4. 分析来源分布时，使用 source_name 字段分组
5. 分析深度采集覆盖时，使用 is_deep_collected 字段（1=已深度采集, 0=未深度采集）
6. 关联查询时利用表关系（如 data_warehouse JOIN deep_collect_data）
7. 时间范围过滤时使用 datetime 函数"""
        return schema_text

    @staticmethod
    def is_safe_sql(sql):
        """检查SQL是否安全（仅允许SELECT查询）"""
        sql_trimmed = sql.strip().upper()
        if not sql_trimmed.startswith("SELECT"):
            return False
        # 禁止危险关键字
        dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE",
                     "EXEC", "EXECUTE", "ATTACH", "DETACH", "REINDEX", "REPLACE",
                     "PRAGMA", "--", "/*"]
        for kw in dangerous:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, sql_trimmed):
                return False
        return True

    @staticmethod
    def execute_safe_query(sql, params=None):
        """安全执行SQL查询并返回结果"""
        if not DataQueryTool.is_safe_sql(sql):
            return {"success": False, "error": "不安全的查询操作"}
        try:
            with get_connection() as conn:
                conn.row_factory = sqlite3.Row
                if params:
                    cursor = conn.execute(sql, params)
                else:
                    cursor = conn.execute(sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(row) for row in rows]
                return {
                    "success": True,
                    "data": data,
                    "columns": columns,
                    "row_count": len(data),
                    "sql_summary": f"查询了{len(data)}条记录"
                }
        except Exception as e:
            return {"success": False, "error": f"查询执行失败: {str(e)[:200]}"}

    @staticmethod
    async def generate_sql_with_llm(question, model, query_type="data_query"):
        """使用LLM将自然语言转换为SQL
        query_type: data_query(普通查询), analysis(统计分析), relationship(关系挖掘)
        """
        import tornado.httpclient

        api_base = (model.get("api_base_url") or "").rstrip("/")
        api_key = model.get("api_key") or ""
        model_name = model.get("model_name") or ""

        is_analysis = query_type in ("analysis", "relationship")
        schema = DataQueryTool.get_schema_context(is_analysis=is_analysis)

        if query_type == "analysis":
            task_desc = """你是一个数据分析师。根据用户的问题，生成SQLite SQL分析查询语句。
数据库表结构如下：
{schema}

生成SQL的规则：
1. 只生成SELECT查询语句，可以使用聚合函数(COUNT, SUM, AVG, MAX, MIN)
2. 可以使用GROUP BY进行分组统计，ORDER BY排序
3. 可以使用JOIN关联多个表
4. 可以在SELECT中为字段起别名（如 COUNT(*) as total_count）
5. 不要在SQL中包含注释
6. 直接返回SQL语句，不要用markdown代码块包裹
7. 如果用户要分析趋势，按时间字段(如 collected_at, created_at)分组"""
        elif query_type == "relationship":
            task_desc = """你是一个数据关系分析师。根据用户的问题，生成SQLite SQL关联查询语句，挖掘数据之间的关系。
数据库表结构如下：
{schema}

生成SQL的规则：
1. 使用JOIN关联相关表（如 data_warehouse ←→ deep_collect_data）
2. 使用聚合函数分析关联数据的数量、比例等
3. 不要在SQL中包含注释
4. 直接返回SQL语句，不要用markdown代码块包裹
5. 重点分析数据之间的关联关系和覆盖程度"""
        else:
            task_desc = f"""你是一个数据库查询助手。根据用户的问题，生成SQLite SQL查询语句。
数据库表结构如下：
{schema}

规则：
1. 只生成SELECT查询语句
2. 不要在SQL中包含注释（不要用--和/*）
3. 直接返回SQL语句，不要用markdown代码块包裹
4. 如果问题不明确，生成最合理的查询
5. 只返回SQL语句本身，不要有任何额外文字"""

        system_prompt = task_desc.format(schema=schema)

        url = f"{api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        body = json.dumps({
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            "stream": False,
            "temperature": 0.1
        })

        try:
            client = tornado.httpclient.AsyncHTTPClient()
            request = tornado.httpclient.HTTPRequest(
                url=url, method="POST", headers=headers, body=body,
                request_timeout=30, connect_timeout=10
            )
            response = await client.fetch(request)
            result = json.loads(response.body)
            sql = result["choices"][0]["message"]["content"].strip()
            # 清理可能存在的markdown代码标记
            sql = re.sub(r'^```(?:sql)?\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()
            return sql
        except Exception as e:
            return None

    @staticmethod
    async def analyze_results_with_llm(question, sql, data, columns, model):
        """使用LLM对查询结果进行分析和解读，生成自然语言分析报告"""
        import tornado.httpclient

        api_base = (model.get("api_base_url") or "").rstrip("/")
        api_key = model.get("api_key") or ""
        model_name = model.get("model_name") or ""

        # 格式化数据摘要供LLM分析
        data_preview = json.dumps(data[:10], ensure_ascii=False, indent=2)
        col_names = ", ".join(columns)
        row_count = len(data)

        system_prompt = f"""你是一个专业的数据分析师。根据用户的问题、执行的SQL、以及查询结果，给出深入的数据分析解读。

请从以下角度进行分析：
1. **数据概览**: 简要说明查询到了什么数据
2. **关键发现**: 指出数据中最重要的发现和趋势
3. **数据洞察**: 深入分析数据背后的含义
4. **建议**: 基于数据给出 actionable 的建议

要求：
- 用中文回答，语言专业但通俗易懂
- 使用markdown格式组织内容（标题、列表、重点标记）
- 如果数据包含时间信息，分析时间趋势
- 如果数据包含分类信息，分析分布特征
- 如果数据包含数值指标，指出最大值、最小值、平均值等
- 不要暴露具体的SQL语句
"""

        url = f"{api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        user_prompt = f"""## 用户问题
{question}

## 执行的SQL
{sql}

## 查询结果（共{row_count}条记录）
字段: {col_names}

数据预览:
{data_preview}"""

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
            client = tornado.httpclient.AsyncHTTPClient()
            request = tornado.httpclient.HTTPRequest(
                url=url, method="POST", headers=headers, body=body,
                request_timeout=60, connect_timeout=15
            )
            response = await client.fetch(request)
            result = json.loads(response.body)
            analysis = result["choices"][0]["message"]["content"].strip()
            return analysis
        except Exception as e:
            return None
