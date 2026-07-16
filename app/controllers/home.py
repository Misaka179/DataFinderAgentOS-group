import json
import tornado.web

from app.controllers.base import BaseHandler
from app.models.db import get_connection
from datetime import datetime, timedelta


class IndexHandler(BaseHandler):
    """用户侧首页 - 重定向到智能问数对话页面"""
    @tornado.web.authenticated
    def get(self):
        self.redirect("/chat")


class DashboardStatsApiHandler(BaseHandler):
    """控制台统计数据API（用于前端实时刷新）"""
    @tornado.web.authenticated
    def get(self):
        stats = {}
        try:
            with get_connection() as conn:
                stats["user_count"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
                stats["data_count"] = conn.execute("SELECT COUNT(*) FROM data_warehouse").fetchone()[0] or 0
                stats["task_count"] = conn.execute("SELECT COUNT(*) FROM deep_collect_tasks").fetchone()[0] or 0
                stats["model_count"] = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0] or 0
                stats["watch_count"] = conn.execute("SELECT COUNT(*) FROM watch_sources").fetchone()[0] or 0
                stats["de_count"] = conn.execute("SELECT COUNT(*) FROM digital_employees").fetchone()[0] or 0
                stats["today_task_count"] = conn.execute(
                    "SELECT COUNT(*) FROM deep_collect_tasks WHERE date(started_at)=date('now')"
                ).fetchone()[0] or 0
                stats["deep_count"] = conn.execute(
                    "SELECT COUNT(*) FROM data_warehouse WHERE is_deep_collected=1"
                ).fetchone()[0] or 0

                # 图表数据：采集任务状态分布（柱状图）
                status_rows = conn.execute("""
                    SELECT COALESCE(NULLIF(status,''), 'unknown') as name, COUNT(*) as value
                    FROM deep_collect_tasks GROUP BY status ORDER BY value DESC
                """).fetchall()
                status_map = {"pending": "待处理", "running": "运行中", "completed": "已完成", "failed": "失败", "unknown": "未知"}
                stats["task_status_bar"] = [
                    {"name": status_map.get(r["name"], r["name"]), "value": r["value"]} for r in status_rows
                ]

                # 图表数据：近7天数据入库趋势（折线图）
                trend_rows = conn.execute("""
                    SELECT date(collected_at) as date, COUNT(*) as count
                    FROM data_warehouse
                    WHERE collected_at >= date('now', '-7 days')
                    GROUP BY date(collected_at) ORDER BY date
                """).fetchall()
                stats["daily_trend"] = [
                    {"date": r["date"], "count": r["count"]} for r in trend_rows
                ]

                # 图表数据：深度采集覆盖率（环形图）
                deep_total = stats["deep_count"]
                not_deep = max(0, stats["data_count"] - deep_total)
                stats["deep_coverage"] = [
                    {"name": "已深度采集", "value": deep_total},
                    {"name": "未深度采集", "value": not_deep}
                ]

                # 图表数据：各表记录数明细（表格区用）
                stats["table_details"] = {
                    "users": stats["user_count"],
                    "data_warehouse": stats["data_count"],
                    "deep_collect_tasks": stats["task_count"],
                    "ai_models": stats["model_count"],
                    "watch_sources": stats["watch_count"],
                    "digital_employees": stats["de_count"],
                }
        except Exception:
            stats = {"user_count":0, "data_count":0, "task_count":0, "model_count":0,
                     "watch_count":0, "de_count":0, "today_task_count":0, "deep_count":0,
                     "task_status_bar":[], "daily_trend":[], "deep_coverage":[], "table_details":{}}
        self.write(json.dumps({"success": True, "data": stats}))


class AdminIndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        # 从数据库查询实时统计数据
        stats = {}
        try:
            with get_connection() as conn:
                stats["user_count"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
                stats["data_count"] = conn.execute("SELECT COUNT(*) FROM data_warehouse").fetchone()[0] or 0
                stats["task_count"] = conn.execute("SELECT COUNT(*) FROM deep_collect_tasks").fetchone()[0] or 0
                stats["model_count"] = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0] or 0
                stats["watch_count"] = conn.execute("SELECT COUNT(*) FROM watch_sources").fetchone()[0] or 0
                stats["de_count"] = conn.execute("SELECT COUNT(*) FROM digital_employees").fetchone()[0] or 0
                stats["today_task_count"] = conn.execute(
                    "SELECT COUNT(*) FROM deep_collect_tasks WHERE date(started_at)=date('now')"
                ).fetchone()[0] or 0
                stats["deep_count"] = conn.execute(
                    "SELECT COUNT(*) FROM data_warehouse WHERE is_deep_collected=1"
                ).fetchone()[0] or 0
        except Exception:
            stats = {"user_count":0, "data_count":0, "task_count":0, "model_count":0,
                     "watch_count":0, "de_count":0, "today_task_count":0, "deep_count":0}

        self.render("admin/index.html", title="后台管理", username=self.current_user, stats=stats)


class DataScreenHandler(BaseHandler):
    """数智大屏页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/data_screen.html", title="数智大屏", username=self.current_user)


class DataScreenStatsApiHandler(BaseHandler):
    """数智大屏概览统计数据API"""
    @tornado.web.authenticated
    def get(self):
        data = {}
        try:
            with get_connection() as conn:
                data["user_count"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] or 0
                data["data_count"] = conn.execute("SELECT COUNT(*) FROM data_warehouse").fetchone()[0] or 0
                data["task_count"] = conn.execute("SELECT COUNT(*) FROM deep_collect_tasks").fetchone()[0] or 0
                data["model_count"] = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0] or 0
                data["watch_count"] = conn.execute("SELECT COUNT(*) FROM watch_sources").fetchone()[0] or 0
                data["de_count"] = conn.execute("SELECT COUNT(*) FROM digital_employees").fetchone()[0] or 0
                data["today_data"] = conn.execute(
                    "SELECT COUNT(*) FROM data_warehouse WHERE date(collected_at)=date('now')"
                ).fetchone()[0] or 0
                data["deep_ratio"] = round(
                    (conn.execute("SELECT COUNT(*) FROM data_warehouse WHERE is_deep_collected=1").fetchone()[0] or 0)
                    / max(data["data_count"], 1) * 100, 1
                )
        except Exception:
            data = {}
        self.write(json.dumps({"success": True, "data": data}))


class DataScreenWordcloudApiHandler(BaseHandler):
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


class DataScreenTrendsApiHandler(BaseHandler):
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


class DataScreenSourceApiHandler(BaseHandler):
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


class DataScreenSankeyApiHandler(BaseHandler):
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
                sink = {"已完成": "任务已完成", "running": "任务运行中", "pending": "任务待处理", "failed": "任务失败"}
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


class OpinionScreenHandler(BaseHandler):
    """舆情大屏页面"""
    @tornado.web.authenticated
    def get(self):
        self.render("admin/opinion_screen.html", title="舆情大屏", username=self.current_user)


class OpinionWarningsApiHandler(BaseHandler):
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


class OpinionStatsApiHandler(BaseHandler):
    """舆情统计数据API"""
    @tornado.web.authenticated
    def get(self):
        try:
            with get_connection() as conn:
                total_warnings = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings").fetchone()[0] or 0
                unread_count = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings WHERE status='unread'").fetchone()[0] or 0
                high_count = conn.execute("SELECT COUNT(*) FROM public_opinion_warnings WHERE severity='high'").fetchone()[0] or 0

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
                    "by_category": by_category,
                    "trend": trend
                }
            }))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionAIAnalyzeApiHandler(BaseHandler):
    """AI分析告警"""
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

                risk_analysis = (
                    f"【风险分析】系统检测到内容中包含敏感词「{word}」（类别：{category}）。"
                    f"该词涉及{category}领域，建议管理员重点关注。"
                    f"相关原文摘要：{content[:200]}..."
                )
                risk_score = 75.0 if row["severity"] == "high" else 45.0

                conn.execute(
                    "UPDATE public_opinion_warnings SET risk_analysis=?, risk_score=? WHERE id=?",
                    (risk_analysis, risk_score, warning_id)
                )

            self.write(json.dumps({
                "success": True,
                "data": {"risk_analysis": risk_analysis, "risk_score": risk_score}
            }))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionAcknowledgeApiHandler(BaseHandler):
    """确认/已读告警"""
    @tornado.web.authenticated
    def post(self):
        try:
            body = json.loads(self.request.body)
            warning_id = body.get("id")
            status = body.get("status", "read")
            feedback = body.get("user_feedback", "")

            if not warning_id:
                self.write(json.dumps({"success": False, "message": "缺少id参数"}))
                return

            with get_connection() as conn:
                if feedback:
                    conn.execute(
                        "UPDATE public_opinion_warnings SET status=?, user_feedback=? WHERE id=?",
                        (status, feedback, warning_id)
                    )
                else:
                    conn.execute(
                        "UPDATE public_opinion_warnings SET status=? WHERE id=?",
                        (status, warning_id)
                    )

            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionFeedbackApiHandler(BaseHandler):
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

            self.write(json.dumps({"success": True}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class OpinionScanApiHandler(BaseHandler):
    """扫描采集数据+用户对话中的攻击性敏感词"""
    @tornado.web.authenticated
    def post(self):
        try:
            with get_connection() as conn:
                words = conn.execute(
                    "SELECT id, word, category, severity FROM sensitive_words WHERE is_active=1"
                ).fetchall()

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

                    # 扫描 conversations
                    conv_rows = conn.execute(
                        "SELECT id, messages, title FROM conversations"
                    ).fetchall()
                    for conv in conv_rows:
                        msg_text = (conv["messages"] or "") + " " + (conv["title"] or "")
                        if word_text in msg_text:
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

            self.write(json.dumps({"success": True, "new_count": new_count}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class SensitiveWordsApiHandler(BaseHandler):
    """敏感词列表/详情"""
    @tornado.web.authenticated
    def get(self):
        try:
            word_id = self.get_argument("id", "")
            with get_connection() as conn:
                if word_id:
                    row = conn.execute("SELECT * FROM sensitive_words WHERE id=?", (int(word_id),)).fetchone()
                    self.write(json.dumps({"success": True, "data": dict(row) if row else None}))
                else:
                    rows = conn.execute("SELECT * FROM sensitive_words ORDER BY id").fetchall()
                    self.write(json.dumps({"success": True, "data": [dict(r) for r in rows]}))
        except Exception as e:
            self.write(json.dumps({"success": False, "message": str(e)}))


class SensitiveWordsCreateApiHandler(BaseHandler):
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


class SensitiveWordsUpdateApiHandler(BaseHandler):
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


class SensitiveWordsDeleteApiHandler(BaseHandler):
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
