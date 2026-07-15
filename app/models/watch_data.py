from app.models.db import get_connection


class WatchDataRepository:
    """瞭望采集数据仓库"""

    @staticmethod
    def get_collected(keyword=None, source_id=None, page=1, page_size=12):
        """分页查询采集数据（橱窗列表模式，一页12条）"""
        conn = get_connection()
        try:
            conditions = []
            params = []

            if keyword:
                conditions.append("keyword LIKE ?")
                params.append(f"%{keyword}%")
            if source_id:
                conditions.append("source_id = ?")
                params.append(int(source_id))

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            count_sql = f"SELECT COUNT(*) FROM watch_collected_data {where}"
            total = conn.execute(count_sql, params).fetchone()[0]

            offset = (page - 1) * page_size
            data_sql = f"SELECT * FROM watch_collected_data {where} ORDER BY id DESC LIMIT ? OFFSET ?"
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
    def get_by_id(item_id):
        """根据ID获取单条采集数据"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM watch_collected_data WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def batch_insert(items):
        """批量插入采集数据"""
        conn = get_connection()
        try:
            for item in items:
                conn.execute(
                    """INSERT INTO watch_collected_data 
                    (source_id, keyword, title, url, summary, source_name) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        item.get("source_id"),
                        item.get("keyword"),
                        item.get("title"),
                        item.get("url"),
                        item.get("summary"),
                        item.get("source_name")
                    )
                )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def delete_by_source(source_id):
        """删除某个瞭源的所有采集数据"""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM watch_collected_data WHERE source_id = ?", (source_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
