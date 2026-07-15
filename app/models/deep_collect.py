import json
from .db import get_connection


class DeepCollectRepository:

    @staticmethod
    def create_task(warehouse_id, employee_id, employee_name):
        """创建深度采集任务"""
        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO deep_collect_tasks 
                   (warehouse_id, employee_id, employee_name, status, progress, steps, logs)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (warehouse_id, employee_id, employee_name, "pending", 0, "[]", "[]")
            )
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            print(f"[DeepCollect] create_task error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_task(task_id):
        """获取任务详情"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM deep_collect_tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_task_by_warehouse(warehouse_id):
        """获取某条数据的最新任务"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM deep_collect_tasks WHERE warehouse_id = ? ORDER BY id DESC LIMIT 1",
                (warehouse_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def update_task(task_id, data):
        """更新任务（状态/进度/日志/结果）"""
        conn = get_connection()
        try:
            fields = []
            values = []
            for key in ("status", "progress", "steps", "logs", "result_data", "error_message", "started_at", "completed_at"):
                if key in data:
                    fields.append(f"{key} = ?")
                    values.append(data[key])
            if not fields:
                return False
            fields.append("updated_at = datetime('now','localtime')")
            values.append(task_id)
            conn.execute(
                f"UPDATE deep_collect_tasks SET {', '.join(fields)} WHERE id = ?",
                values
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[DeepCollect] update_task error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def list_tasks(page=1, page_size=20, status_filter=""):
        """获取任务列表"""
        conn = get_connection()
        try:
            conditions = []
            params = []
            if status_filter:
                conditions.append("t.status = ?")
                params.append(status_filter)
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            total = conn.execute(
                f"SELECT COUNT(*) FROM deep_collect_tasks t{where}", params
            ).fetchone()[0]
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""SELECT t.*, w.title as warehouse_title, w.url as warehouse_url
                    FROM deep_collect_tasks t
                    LEFT JOIN data_warehouse w ON t.warehouse_id = w.id
                    {where} ORDER BY t.id DESC LIMIT ? OFFSET ?""",
                params + [page_size, offset]
            ).fetchall()
            return {"data": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}
        finally:
            conn.close()

    @staticmethod
    def get_latest_by_warehouse_ids(warehouse_ids):
        """批量查询多条数据的最新任务状态"""
        if not warehouse_ids:
            return {}
        conn = get_connection()
        try:
            placeholders = ",".join("?" for _ in warehouse_ids)
            rows = conn.execute(
                f"""SELECT w.id as warehouse_id, t.id as task_id, t.status, t.progress
                    FROM (SELECT id FROM data_warehouse WHERE id IN ({placeholders})) w
                    LEFT JOIN deep_collect_tasks t ON t.warehouse_id = w.id
                    WHERE t.id IN (
                        SELECT MAX(id) FROM deep_collect_tasks
                        WHERE warehouse_id IN ({placeholders})
                        GROUP BY warehouse_id
                    )
                    UNION ALL
                    SELECT w2.id as warehouse_id, NULL as task_id, NULL as status, NULL as progress
                    FROM (SELECT id FROM data_warehouse WHERE id IN ({placeholders})) w2
                    WHERE w2.id NOT IN (
                        SELECT DISTINCT warehouse_id FROM deep_collect_tasks
                        WHERE warehouse_id IN ({placeholders})
                    )""",
                warehouse_ids + warehouse_ids + warehouse_ids + warehouse_ids
            ).fetchall()
            return {r["warehouse_id"]: {"task_id": r["task_id"], "status": r["status"], "progress": r["progress"]} for r in rows}
        finally:
            conn.close()

    # ========== 深度采集数据（deep_collect_data）==========

    @staticmethod
    def save_collected_data(warehouse_id, task_id, crawled_title, crawled_content, analysis_result, extra_data=None):
        """保存深度采集到的详细数据"""
        conn = get_connection()
        try:
            # 先删除该条数据的旧采集记录（更新采集）
            conn.execute("DELETE FROM deep_collect_data WHERE warehouse_id = ?", (warehouse_id,))
            cur = conn.execute(
                """INSERT INTO deep_collect_data
                   (warehouse_id, task_id, crawled_title, crawled_content, analysis_result, extra_data)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (warehouse_id, task_id, crawled_title or "", crawled_content or "",
                 analysis_result or "", json.dumps(extra_data or {}, ensure_ascii=False))
            )
            conn.commit()
            data_id = cur.lastrowid
            print(f"[DeepCollect] 采集数据已保存, data_id={data_id}, warehouse_id={warehouse_id}")
            return data_id
        except Exception as e:
            print(f"[DeepCollect] save_collected_data error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_collected_data(warehouse_id):
        """获取某条数据的最新采集数据"""
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT d.*, t.employee_name, t.status as task_status, t.progress, t.completed_at,
                          w.title as warehouse_title, w.url as warehouse_url
                   FROM deep_collect_data d
                   JOIN deep_collect_tasks t ON d.task_id = t.id
                   LEFT JOIN data_warehouse w ON d.warehouse_id = w.id
                   WHERE d.warehouse_id = ?
                   ORDER BY d.id DESC LIMIT 1""",
                (warehouse_id,)
            ).fetchone()
            result = dict(row) if row else None
            if result and isinstance(result.get("extra_data"), str):
                try:
                    result["extra_data"] = json.loads(result["extra_data"])
                except (json.JSONDecodeError, TypeError):
                    result["extra_data"] = {}
            return result
        finally:
            conn.close()

    @staticmethod
    def get_collected_data_by_task(task_id):
        """根据任务ID获取采集数据"""
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT d.*, t.employee_name, t.status as task_status, t.completed_at
                   FROM deep_collect_data d
                   JOIN deep_collect_tasks t ON d.task_id = t.id
                   WHERE d.task_id = ?""",
                (task_id,)
            ).fetchone()
            result = dict(row) if row else None
            if result and isinstance(result.get("extra_data"), str):
                try:
                    result["extra_data"] = json.loads(result["extra_data"])
                except (json.JSONDecodeError, TypeError):
                    result["extra_data"] = {}
            return result
        finally:
            conn.close()
