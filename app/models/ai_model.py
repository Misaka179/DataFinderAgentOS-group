from app.models.db import get_connection


class AiModelRepository:
    """模型引擎仓库"""

    @staticmethod
    def get_all(page=1, page_size=20, search=None, category=None):
        """分页查询模型列表，支持按分类筛选"""
        conn = get_connection()
        try:
            conditions = []
            params = []
            if search:
                conditions.append("(name LIKE ? OR provider LIKE ? OR model_name LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            if category:
                conditions.append("category = ?")
                params.append(category)
            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            total = conn.execute(f"SELECT COUNT(*) FROM ai_models {where}", params).fetchone()[0]
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"SELECT * FROM ai_models {where} ORDER BY sort_order ASC, id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset]
            ).fetchall()
            return {"data": [dict(r) for r in rows], "total": total, "page": page, "page_size": page_size}
        finally:
            conn.close()

    @staticmethod
    def get_categories():
        """获取所有模型分类"""
        conn = get_connection()
        try:
            rows = conn.execute("SELECT DISTINCT category FROM ai_models ORDER BY category").fetchall()
            return [r["category"] for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(model_id):
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM ai_models WHERE id=?", (model_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_default():
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM ai_models WHERE is_default=1 AND status=1 LIMIT 1").fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create(name, provider, model_name, api_base_url, api_key, max_tokens,
               category='text', system_prompt='', temperature=0.7, top_p=1.0, context_length=4096):
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
                   max_tokens, category, system_prompt, temperature, top_p, context_length)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (name, provider, model_name, api_base_url, api_key,
                 max_tokens, category, system_prompt, temperature, top_p, context_length)
            )
            conn.commit()
            return True
        except Exception as e:
            return False
        finally:
            conn.close()

    @staticmethod
    def update(model_id, **kwargs):
        conn = get_connection()
        try:
            allowed = {"name", "provider", "model_name", "api_base_url", "api_key",
                       "max_tokens", "token_count", "is_default", "status", "sort_order",
                       "category", "system_prompt", "temperature", "top_p", "context_length"}
            updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
            if not updates:
                return False
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [model_id]
            conn.execute(
                f"UPDATE ai_models SET {set_clause}, updated_at = datetime('now', 'localtime') WHERE id = ?",
                values
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def set_default(model_id):
        """设置默认模型（先清除所有默认标记，再设置）"""
        conn = get_connection()
        try:
            conn.execute("UPDATE ai_models SET is_default=0")
            conn.execute("UPDATE ai_models SET is_default=1 WHERE id=?", (model_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def delete(model_id):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM ai_models WHERE id=?", (model_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_all_active():
        """获取所有启用的模型"""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM ai_models WHERE status=1 ORDER BY sort_order ASC, id DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
