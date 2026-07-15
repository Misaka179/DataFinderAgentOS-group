from app.models.db import get_connection


class DataWarehouseRepository:

    @staticmethod
    def get_all(page=1, page_size=20, search=None):
        conn = get_connection()
        try:
            conditions = []
            params = []
            if search:
                conditions.append("(title LIKE ? OR summary LIKE ? OR source_name LIKE ? OR keyword LIKE ?)")
                like = f"%{search}%"
                params.extend([like, like, like, like])
            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            total = conn.execute(f"SELECT COUNT(*) FROM data_warehouse {where}", params).fetchone()[0]
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"SELECT * FROM data_warehouse {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            ).fetchall()
            return {"data": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}
        finally:
            conn.close()

    @staticmethod
    def get_by_id(item_id):
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM data_warehouse WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def upsert(title, url, summary, source_name, keyword, source_id=0):
        """插入或更新（根据URL去重）"""
        conn = get_connection()
        try:
            if url:
                existing = conn.execute(
                    "SELECT id FROM data_warehouse WHERE url = ?", (url,)
                ).fetchone()
            else:
                existing = conn.execute(
                    "SELECT id FROM data_warehouse WHERE title = ? AND source_name = ?",
                    (title, source_name)
                ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE data_warehouse SET title=?, summary=?, source_name=?, keyword=?,
                       source_id=?, updated_at=datetime('now','localtime') WHERE id=?""",
                    (title, summary, source_name, keyword, source_id, existing["id"])
                )
            else:
                conn.execute(
                    """INSERT INTO data_warehouse (title, url, summary, source_name, keyword, source_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, url, summary, source_name, keyword, source_id)
                )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def batch_upsert(items):
        """批量upsert"""
        conn = get_connection()
        try:
            for item in items:
                title = item.get("title", "")
                url = item.get("url", "")
                summary = item.get("summary", "")
                source_name = item.get("source_name", "")
                keyword = item.get("keyword", "")
                source_id = item.get("source_id", 0)
                if not title:
                    continue
                if url:
                    existing = conn.execute(
                        "SELECT id FROM data_warehouse WHERE url = ?", (url,)
                    ).fetchone()
                else:
                    existing = conn.execute(
                        "SELECT id FROM data_warehouse WHERE title = ? AND source_name = ?",
                        (title, source_name)
                    ).fetchone()
                if existing:
                    conn.execute(
                        """UPDATE data_warehouse SET title=?, summary=?, source_name=?, keyword=?,
                           source_id=?, updated_at=datetime('now','localtime') WHERE id=?""",
                        (title, summary, source_name, keyword, source_id, existing["id"])
                    )
                else:
                    conn.execute(
                        """INSERT INTO data_warehouse (title, url, summary, source_name, keyword, source_id)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (title, url, summary, source_name, keyword, source_id)
                    )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def delete(item_id):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM data_warehouse WHERE id = ?", (item_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def batch_delete(ids):
        """批量删除"""
        conn = get_connection()
        try:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM data_warehouse WHERE id IN ({placeholders})", ids)
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def _update_deep_collected(item_id, value):
        """更新深度采集状态（内部方法）"""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE data_warehouse SET is_deep_collected=?, updated_at=datetime('now','localtime') WHERE id=?",
                (value, item_id)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
