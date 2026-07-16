import json
import tornado.web
import requests

from app.controllers.base import BaseHandler, AdminBaseHandler
from app.models.db import get_connection
from app.models.ai_model import AiModelRepository
from datetime import datetime, timedelta
import time


LLM_REVIEW_PROMPT = """你是一个安全审核专家。根据以下信息判断内容是否属于真实攻击。

【敏感词】{matched_word}
【风险类别】{category}
【内容摘要】{source_content}

请严格按以下 JSON 格式输出，不要额外解释：
{{"classification": "real_attack|false_positive|suspicious", "reason": "判断理由", "risk_score": 0-100}}

分类说明：
- real_attack (风险分 70-100): 明确的安全攻击载荷，如 SQL注入、代码执行、XSS、Prompt注入等
- false_positive (风险分 0-30): 正常文本，敏感词出现在正常语境中，无攻击意图
- suspicious (风险分 31-69): 存在可疑特征但无法明确判断，需人工复核

示例：
输入: 敏感词="SELECT * FROM", 类别="SQL注入", 内容="SELECT * FROM users WHERE id=1"
输出: {{"classification": "real_attack", "reason": "SQL查询语句出现在用户对话中", "risk_score": 85}}

输入: 敏感词="DROP TABLE", 类别="SQL注入", 内容="常见 SQL 命令包括 SELECT、DROP TABLE 等"
输出: {{"classification": "false_positive", "reason": "敏感词出现在教学上下文，非实际攻击", "risk_score": 15}}"""


def llm_classify_warning(source_content, matched_word, category):
    """调用默认大模型对命中敏感词的内容做二次判定，返回分类结果"""
    try:
        model = AiModelRepository.get_default()
        if not model:
            return {"classification": "suspicious", "reason": "无可用模型，保留预警", "risk_score": 50}

        api_base = (model.get("api_base_url") or "").rstrip("/")
        api_key = model.get("api_key") or ""
        model_name = model.get("model_name") or ""

        if not api_base or not api_key:
            return {"classification": "suspicious", "reason": "模型未配置完整，保留预警", "risk_score": 50}

        esc = lambda s: s.replace('{', '{{').replace('}', '}}')
        prompt = LLM_REVIEW_PROMPT.format(
            matched_word=esc(matched_word),
            category=esc(category),
            source_content=esc((source_content or "")[:500])
        )

        resp = requests.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 256
            },
            timeout=15
        )
        resp.raise_for_status()
        result = resp.json()
        content = result["choices"][0]["message"]["content"].strip()

        # 提取 JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(content[start:end])
            return parsed
        return {"classification": "suspicious", "reason": "模型返回格式异常", "risk_score": 50}
    except Exception:
        return {"classification": "suspicious", "reason": "模型调用异常，保留预警", "risk_score": 50}


async def batch_review_pending_warnings():
    """后台批量审核所有待审预警（risk_analysis IS NULL）"""
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, source_content, matched_word, word_category FROM public_opinion_warnings WHERE risk_analysis IS NULL"
            ).fetchall()

            for row in rows:
                result = llm_classify_warning(
                    row["source_content"], row["matched_word"], row["word_category"]
                )
                cls = result.get("classification", "suspicious")
                reason = result.get("reason", "")
                score = result.get("risk_score", 50)

                if cls == "false_positive":
                    conn.execute("DELETE FROM public_opinion_warnings WHERE id=?", (row["id"],))
                else:
                    final_severity = "high" if cls == "real_attack" else "medium"
                    analysis = f"【AI审核{'(模型复核)' if cls == 'suspicious' else ''}】{reason}"
                    conn.execute(
                        "UPDATE public_opinion_warnings SET risk_analysis=?, risk_score=?, severity=? WHERE id=?",
                        (analysis, score, final_severity, row["id"])
                    )
            conn.commit()
    except Exception:
        pass


class IndexHandler(BaseHandler):
    """用户侧首页 - 重定向到智能问数对话页面"""
    @tornado.web.authenticated
    def get(self):
        self.redirect("/chat")

class DashboardStatsApiHandler(BaseHandler):
    """控制台统计数据API（用于前端实时刷新）"""
    @tornado.web.authenticated
    def get(self):
        stats = self.get_base_stats()
        stats.setdefault("task_status_bar", [])
        stats.setdefault("daily_trend", [])
        stats.setdefault("deep_coverage", [])
        stats.setdefault("table_details", {})
        try:
            with get_connection() as conn:
                status_rows = conn.execute("""
                    SELECT COALESCE(NULLIF(status,''), 'unknown') as name, COUNT(*) as value
                    FROM deep_collect_tasks GROUP BY status ORDER BY value DESC
                """).fetchall()
                status_map = {"pending": "待处理", "running": "运行中", "completed": "已完成", "failed": "失败", "unknown": "未知"}
                stats["task_status_bar"] = [
                    {"name": status_map.get(r["name"], r["name"]), "value": r["value"]} for r in status_rows
                ]

                trend_rows = conn.execute("""
                    SELECT date(collected_at) as date, COUNT(*) as count
                    FROM data_warehouse
                    WHERE collected_at >= date('now', '-7 days')
                    GROUP BY date(collected_at) ORDER BY date
                """).fetchall()
                stats["daily_trend"] = [
                    {"date": r["date"], "count": r["count"]} for r in trend_rows
                ]

                deep_total = stats["deep_count"]
                not_deep = max(0, stats["data_count"] - deep_total)
                stats["deep_coverage"] = [
                    {"name": "已深度采集", "value": deep_total},
                    {"name": "未深度采集", "value": not_deep}
                ]

                stats["table_details"] = {
                    "users": stats["user_count"],
                    "data_warehouse": stats["data_count"],
                    "deep_collect_tasks": stats["task_count"],
                    "ai_models": stats["model_count"],
                    "watch_sources": stats["watch_count"],
                    "digital_employees": stats["de_count"],
                }
        except Exception:
            pass
        self.write(json.dumps({"success": True, "data": stats}))


class GestureHandler(BaseHandler):
    """手势交互页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("gesture.html")

class AdminIndexHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        stats = self.get_base_stats()
        self.render("admin/index.html", title="后台管理", username=self.current_user, stats=stats)


class DataScreenHandler(AdminBaseHandler):
    """数智大屏页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/data_screen.html", title="数智大屏", username=self.current_user)


class DataScreenWordcloudApiHandler(AdminBaseHandler):
    """数智大屏词云数据API"""
    @tornado.web.authenticated
    def get(self):
        try:
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT keyword, COUNT(*) as weight
                    FROM data_warehouse
                    WHERE keyword IS NOT NULL AND keyword != ''
                    GROUP BY keyword ORDER BY weight DESC LIMIT 50
                """).fetchall()
                words = [{"name": r["keyword"], "value": r["weight"]} for r in rows]
        except Exception:
            words = []
        self.write(json.dumps({"success": True, "data": words}))


class DataScreenTrendsApiHandler(AdminBaseHandler):
    """数智大屏趋势数据API"""
    @tornado.web.authenticated
    def get(self):
        days = int(self.get_argument("days", 30))
        try:
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT date(collected_at) as date, COUNT(*) as count
                    FROM data_warehouse
                    WHERE collected_at >= date('now', ?)
                    GROUP BY date(collected_at) ORDER BY date
                """, (f'-{days} days',)).fetchall()
                trend = [{"date": r["date"], "count": r["count"]} for r in rows]
        except Exception:
            trend = []
        self.write(json.dumps({"success": True, "data": trend}))


class DataScreenSourceApiHandler(AdminBaseHandler):
    """数智大屏来源分布API"""
    @tornado.web.authenticated
    def get(self):
        try:
            with get_connection() as conn:
                rows = conn.execute("""
                    SELECT COALESCE(NULLIF(source_name,''), '未知来源') as name, COUNT(*) as value
                    FROM data_warehouse GROUP BY source_name ORDER BY value DESC LIMIT 10
                """).fetchall()
                data = [{"name": r["name"], "value": r["value"]} for r in rows]
        except Exception:
            data = []
        self.write(json.dumps({"success": True, "data": data}))


class DataScreenSankeyApiHandler(AdminBaseHandler):
    """数智大屏桑基图数据API — 数据流水线"""
    @tornado.web.authenticated
    def get(self):
        try:
            with get_connection() as conn:
                source_rows = conn.execute("""
                    SELECT COALESCE(NULLIF(source_name,''), '未知来源') as name, COUNT(*) as value
                    FROM data_warehouse GROUP BY source_name ORDER BY value DESC LIMIT 10
                """).fetchall()
                total = conn.execute("SELECT COUNT(*) FROM data_warehouse").fetchone()[0] or 0
                deep = conn.execute("SELECT COUNT(*) FROM data_warehouse WHERE is_deep_collected=1").fetchone()[0] or 0
                not_deep = total - deep
                status_rows = conn.execute("""
                    SELECT status, COUNT(*) as value FROM deep_collect_tasks GROUP BY status
                """).fetchall()
                sink = {"completed": "任务已完成", "running": "任务运行中", "pending": "任务待处理", "failed": "任务失败"}
                nodes = [{"name": "数据仓库"}]
                links = []
                for r in source_rows:
                    nodes.append({"name": r["name"]})
                    links.append({"source": r["name"], "target": "数据仓库", "value": r["value"]})
                if deep > 0:
                    nodes.append({"name": "已深度采集"})
                    links.append({"source": "数据仓库", "target": "已深度采集", "value": deep})
                    for r in status_rows:
                        label = sink.get(r["status"], r["status"])
                        nodes.append({"name": label})
                        links.append({"source": "已深度采集", "target": label, "value": r["value"]})
                if not_deep > 0:
                    nodes.append({"name": "未深度采集"})
                    links.append({"source": "数据仓库", "target": "未深度采集", "value": not_deep})
                self.write(json.dumps({"success": True, "data": {"nodes": nodes, "links": links}}))
        except Exception:
            self.write(json.dumps({"success": True, "data": {"nodes": [], "links": []}}))


class OpinionScreenHandler(AdminBaseHandler):
    """舆情大屏页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/opinion_screen.html", title="舆情大屏", username=self.current_user)


class OpinionWarningsApiHandler(AdminBaseHandler):
    """舆情警告列表API"""
    @tornado.web.authenticated
    def get(self):
        try:
            status = self.get_argument("status", "")
            page = int(self.get_argument("page", 1))
            page_size = int(self.get_argument("page_size", 20))
            offset = (page - 1) * page_size

            with get_connection() as conn:
                where = ""
                params = []
                if status:
                    where = " WHERE status = ?"
                    params.append(status)

                total = conn.execute(
                    "SELECT COUNT(*) FROM public_opinion_warnings" + where, params
                ).fetchone()[0] or 0
                unread_count = conn.execute(
                    "SELECT COUNT(*) FROM public_opinion_warnings WHERE status = 'unread'"
                ).fetchone()[0] or 0

                rows = conn.execute(
                    "SELECT * FROM public_opinion_warnings" + where + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    params + [page_size, offset]
                ).fetchall()
                data = [dict(r) for r in rows]

            self.write(json.dumps({"success": True, "data": data, "total": total, "unread_count": unread_count}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionStatsApiHandler(AdminBaseHandler):
    """舆情统计数据API"""
    @tornado.web.authenticated
    def get(self):
        try:
            with get_connection() as conn:
                total_warnings = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings").fetchone()[0] or 0
                unread_count = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings WHERE status='unread'").fetchone()[0] or 0
                high_count = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings WHERE severity='high'").fetchone()[0] or 0
                pending_count = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings WHERE risk_analysis IS NULL").fetchone()[0] or 0

                by_category_rows = conn.execute(
                    "SELECT word_category, COUNT(*) as value FROM public_opinion_warnings GROUP BY word_category"
                ).fetchall()
                by_category = [{"name": r["word_category"], "value": r["value"]} for r in by_category_rows]

                trend_rows = conn.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM public_opinion_warnings
                    WHERE created_at >= date('now', '-30 days')
                    GROUP BY DATE(created_at) ORDER BY date
                """).fetchall()
                trend = [{"date": r["date"], "count": r["count"]} for r in trend_rows]

            self.write(json.dumps({
                "success": True,
                "data": {
                    "total_warnings": total_warnings,
                    "unread_count": unread_count,
                    "high_count": high_count,
                    "pending_count": pending_count,
                    "by_category": by_category,
                    "trend": trend
                }
            }))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionAIAnalyzeApiHandler(AdminBaseHandler):
    """AI分析告警（调用大模型做语义判定）"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            warning_id = body.get("id")
            if not warning_id:
                self.write(json.dumps({"success": False, "message": "缺少id参数"}))
                return

            with get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM public_opinion_warnings WHERE id=?", (warning_id,)
                ).fetchone()
                if not row:
                    self.write(json.dumps({"success": False, "message": "记录不存在"}))
                    return

                content = row["source_content"] or ""
                word = row["matched_word"]
                category = row["word_category"]

                result = llm_classify_warning(content, word, category)
                cls = result.get("classification", "suspicious")
                reason = result.get("reason", "")
                score = result.get("risk_score", 50)

                if cls == "false_positive":
                    conn.execute("DELETE FROM public_opinion_warnings WHERE id=?", (warning_id,))
                    conn.commit()
                    self.write(json.dumps({"success": True, "data": {"deleted": True, "reason": reason}}))
                    return

                final_severity = "high" if cls == "real_attack" else "medium"
                analysis = f"【AI审核{'(模型复核)' if cls == 'suspicious' else ''}】{reason}"
                conn.execute(
                    "UPDATE public_opinion_warnings SET risk_analysis=?, risk_score=?, severity=? WHERE id=?",
                    (analysis, score, final_severity, warning_id)
                )
                conn.commit()

            self.write(json.dumps({
                "success": True,
                "data": {"risk_analysis": analysis, "risk_score": score, "severity": final_severity}
            }))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionAcknowledgeApiHandler(AdminBaseHandler):
    """确认/已读告警 / 更改预警级别"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            warning_id = body.get("id")
            if not warning_id:
                self.write(json.dumps({"success": False, "message": "缺少id参数"}))
                return

            with get_connection() as conn:
                if body.get("action") == "false_positive":
                    conn.execute("DELETE FROM public_opinion_warnings WHERE id=?", (warning_id,))
                    conn.commit()
                    self.write(json.dumps({"success": True}))
                    return

            fields = {}
            if "status" in body:
                fields["status"] = body["status"]
            if "severity" in body:
                fields["severity"] = body["severity"]
            if "user_feedback" in body:
                fields["user_feedback"] = body["user_feedback"]

            if not fields:
                self.write(json.dumps({"success": False, "message": "没有要更新的字段"}))
                return

            set_clause = ", ".join(f"{k}=?" for k in fields)
            values = list(fields.values()) + [warning_id]

            with get_connection() as conn:
                conn.execute(
                    f"UPDATE public_opinion_warnings SET {set_clause} WHERE id=?",
                    values
                )
                conn.commit()

            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionFeedbackApiHandler(AdminBaseHandler):
    """用户反馈（模拟回传）"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            warning_id = body.get("warning_id")
            feedback = body.get("feedback", "")

            if not warning_id:
                self.write(json.dumps({"success": False, "message": "缺少warning_id参数"}))
                return

            with get_connection() as conn:
                conn.execute(
                    "UPDATE public_opinion_warnings SET user_feedback=? WHERE id=?",
                    (feedback, warning_id)
                )
                conn.commit()

            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionScanApiHandler(AdminBaseHandler):
    """扫描采集数据+用户对话中的攻击性敏感词"""
    @tornado.web.authenticated
    def post(self):
        try:
            limit = int(self.get_argument("limit", 50))
            with get_connection() as conn:
                words = conn.execute(
                    "SELECT id, word, category, severity FROM sensitive_words WHERE is_active=1 ORDER BY id LIMIT ?",
                    (limit,)
                ).fetchall()

                pure_symbols = {"%", "&", "{{", "{%", "${", "}"}

                def has_code_context(text, symbol):
                    """纯符号匹配时检查周围是否有代码表达式上下文"""
                    if symbol not in pure_symbols:
                        return True
                    idx = text.find(symbol)
                    if idx < 0:
                        return False
                    before = text[max(0, idx - 10):idx]
                    after = text[idx + len(symbol):idx + len(symbol) + 10]
                    code_hints = {"=", "(", ")", ";", "'", '"', "select", "drop", "exec", "eval",
                                  "system", "import", "os.", "subprocess", "__", "config", "request",
                                  "union", "1=1", "or", "and", ":", " "}
                    for h in code_hints:
                        if h in before or h in after:
                            return True
                    return False

                new_count = 0
                for w in words:
                    word_text = w["word"]
                    cat = w["category"]
                    sev = w["severity"]

                    # 扫描 data_warehouse
                    dw_rows = conn.execute("""
                        SELECT id, title, COALESCE(summary, '') as summary
                        FROM data_warehouse
                        WHERE title LIKE ? OR summary LIKE ?
                    """, (f'%{word_text}%', f'%{word_text}%')).fetchall()
                    for dw in dw_rows:
                        content_text = (dw["title"] or "") + " " + (dw["summary"] or "")
                        if not has_code_context(content_text, word_text):
                            continue
                        exists = conn.execute(
                            "SELECT id FROM public_opinion_warnings WHERE source_type='data_warehouse' AND source_id=? AND matched_word=?",
                            (str(dw["id"]), word_text)
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                """INSERT INTO public_opinion_warnings
                                   (source_type, source_id, source_content, matched_word, word_category, severity)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                ("data_warehouse", str(dw["id"]), content_text[:500], word_text, cat, sev)
                            )
                            new_count += 1

                    # 扫描 conversations（使用 SQL LIKE 避免全表加载到内存）
                    conv_rows = conn.execute(
                        "SELECT id, messages, title FROM conversations WHERE messages LIKE ? OR title LIKE ?",
                        (f'%{word_text}%', f'%{word_text}%')
                    ).fetchall()
                    for conv in conv_rows:
                        msg_text = (conv["messages"] or "") + " " + (conv["title"] or "")
                        if not has_code_context(msg_text, word_text):
                            continue
                        exists = conn.execute(
                            "SELECT id FROM public_opinion_warnings WHERE source_type='user_chat' AND source_id=? AND matched_word=?",
                            (str(conv["id"]), word_text)
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                """INSERT INTO public_opinion_warnings
                                   (source_type, source_id, source_content, matched_word, word_category, severity)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                ("user_chat", str(conv["id"]), msg_text[:500], word_text, cat, sev)
                            )
                            new_count += 1
                conn.commit()

            self.write(json.dumps({"success": True, "new_count": new_count}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionBatchReviewApiHandler(AdminBaseHandler):
    """批量 AI 审核所有待审预警"""
    @tornado.web.authenticated
    async def post(self):
        try:
            before = 0
            with get_connection() as conn:
                before = conn.execute(
                    "SELECT COUNT(*) FROM public_opinion_warnings WHERE risk_analysis IS NULL"
                ).fetchone()[0] or 0

            await batch_review_pending_warnings()

            after = 0
            with get_connection() as conn:
                after = conn.execute(
                    "SELECT COUNT(*) FROM public_opinion_warnings WHERE risk_analysis IS NULL"
                ).fetchone()[0] or 0

            reviewed = before - after
            self.write(json.dumps({
                "success": True,
                "data": {"total": before, "reviewed": reviewed, "remaining": after}
            }))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class SensitiveWordsApiHandler(AdminBaseHandler):
    """敏感词列表/详情（支持分页）"""
    @tornado.web.authenticated
    def get(self):
        try:
            word_id = self.get_argument("id", "")
            with get_connection() as conn:
                if word_id:
                    row = conn.execute("SELECT * FROM sensitive_words WHERE id=?", (int(word_id),)).fetchone()
                    self.write(json.dumps({"success": True, "data": dict(row) if row else None}))
                else:
                    page = int(self.get_argument("page", 1))
                    page_size = int(self.get_argument("page_size", 50))
                    offset = (page - 1) * page_size
                    total = conn.execute("SELECT COUNT(*) FROM sensitive_words").fetchone()[0] or 0
                    rows = conn.execute(
                        "SELECT * FROM sensitive_words ORDER BY id LIMIT ? OFFSET ?",
                        (page_size, offset)
                    ).fetchall()
                    self.write(json.dumps({
                        "success": True,
                        "data": [dict(r) for r in rows],
                        "total": total,
                        "page": page,
                        "page_size": page_size
                    }))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class SensitiveWordsCreateApiHandler(AdminBaseHandler):
    """新增敏感词"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            word = body.get("word", "").strip()
            category = body.get("category", "攻击防护")
            severity = body.get("severity", "high")
            if not word:
                self.write(json.dumps({"success": False, "message": "词不能为空"}))
                return
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO sensitive_words (word, category, severity) VALUES (?, ?, ?)",
                    (word, category, severity)
                )
                conn.commit()
            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class SensitiveWordsUpdateApiHandler(AdminBaseHandler):
    """更新敏感词"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            wid = body.get("id")
            word = body.get("word", "").strip()
            category = body.get("category", "攻击防护")
            severity = body.get("severity", "high")
            if not wid or not word:
                self.write(json.dumps({"success": False, "message": "参数不完整"}))
                return
            with get_connection() as conn:
                conn.execute(
                    "UPDATE sensitive_words SET word=?, category=?, severity=? WHERE id=?",
                    (word, category, severity, wid)
                )
                conn.commit()
            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class SensitiveWordsDeleteApiHandler(AdminBaseHandler):
    """删除敏感词"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            wid = body.get("id")
            if not wid:
                self.write(json.dumps({"success": False, "message": "缺少id"}))
                return
            with get_connection() as conn:
                conn.execute("DELETE FROM sensitive_words WHERE id=?", (wid,))
                conn.commit()
            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))
