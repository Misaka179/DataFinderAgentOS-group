import json
import sqlite3

from app.models.db import get_connection


class WatchSourceRepository:
    """瞭源管理 - 采集源规则仓库"""

    @staticmethod
    def get_all(page=1, page_size=20, search=None, status=None):
        """分页查询瞭源列表"""
        conn = get_connection()
        try:
            conditions = []
            params = []

            if search:
                conditions.append("name LIKE ?")
                params.append(f"%{search}%")
            if status is not None:
                conditions.append("status = ?")
                params.append(int(status))

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            # 统计总数
            count_sql = f"SELECT COUNT(*) FROM watch_sources {where}"
            total = conn.execute(count_sql, params).fetchone()[0]

            # 分页查询
            offset = (page - 1) * page_size
            data_sql = f"SELECT * FROM watch_sources {where} ORDER BY id DESC LIMIT ? OFFSET ?"
            rows = conn.execute(data_sql, params + [page_size, offset]).fetchall()

            return {
                "data": [dict(r) for r in rows],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        finally:
            conn.close()

    @staticmethod
    def get_by_id(source_id):
        """根据ID获取瞭源"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM watch_sources WHERE id = ?", (source_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all_active():
        """获取所有启用的瞭源"""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM watch_sources WHERE status = 1 ORDER BY id DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def create(name, url_template, method, headers, keyword_param, page_param, page_step, source_type="baidu_news"):
        """创建瞭源"""
        conn = get_connection()
        try:
            if isinstance(headers, dict):
                headers = json.dumps(headers, ensure_ascii=False)
            conn.execute(
                """INSERT INTO watch_sources
                (name, url_template, method, headers, keyword_param, page_param, page_step, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, url_template, method, headers, keyword_param, page_param, page_step, source_type)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def update(source_id, **kwargs):
        """更新瞭源"""
        conn = get_connection()
        try:
            allowed = {"name", "url_template", "method", "headers",
                       "keyword_param", "page_param", "page_step", "status", "source_type"}
            updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}

            if not updates:
                return False

            if "headers" in updates and isinstance(updates["headers"], dict):
                updates["headers"] = json.dumps(updates["headers"], ensure_ascii=False)

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [source_id]

            conn.execute(
                f"UPDATE watch_sources SET {set_clause}, updated_at = datetime('now', 'localtime') WHERE id = ?",
                values
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def delete(source_id):
        """删除瞭源"""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM watch_collected_data WHERE source_id = ?", (source_id,))
            conn.execute("DELETE FROM watch_sources WHERE id = ?", (source_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
