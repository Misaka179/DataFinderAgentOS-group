import json
from .db import get_connection

class DigitalEmployeeRepository:

    @staticmethod
    def get_all(page=1, page_size=15, search='', type_filter=''):
        """获取数字员工列表（分页）"""
        conn = get_connection()
        try:
            conditions = []
            params = []
            if search:
                conditions.append("name LIKE ?")
                params.append(f"%{search}%")
            if type_filter:
                conditions.append("type = ?")
                params.append(type_filter)
            
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            
            # 查总数
            count_sql = f"SELECT COUNT(*) FROM digital_employees{where}"
            total = conn.execute(count_sql, params).fetchone()[0]
            
            # 查数据
            offset = (page - 1) * page_size
            data_sql = f"SELECT * FROM digital_employees{where} ORDER BY sort_order, id DESC LIMIT ? OFFSET ?"
            rows = conn.execute(data_sql, params + [page_size, offset]).fetchall()
            
            return {"total": total, "data": [dict(r) for r in rows], "page": page, "page_size": page_size}
        finally:
            conn.close()

    @staticmethod
    def get_by_id(item_id):
        """根据ID获取数字员工"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM digital_employees WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def create(data):
        """创建数字员工"""
        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO digital_employees 
                   (name, type, description, avatar, model_id, system_prompt, skills, 
                    crawl4ai_enabled, api_url, api_method, api_headers, api_params, 
                    api_response_template, card_config, sort_order, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("name", ""),
                    data.get("type", "llm"),
                    data.get("description", ""),
                    data.get("avatar", ""),
                    data.get("model_id"),
                    data.get("system_prompt", ""),
                    data.get("skills", "[]"),
                    1 if data.get("crawl4ai_enabled") else 0,
                    data.get("api_url", ""),
                    data.get("api_method", "GET"),
                    data.get("api_headers", "{}"),
                    data.get("api_params", "{}"),
                    data.get("api_response_template", ""),
                    data.get("card_config", "{}"),
                    int(data.get("sort_order", 0)),
                    int(data.get("status", 1))
                )
            )
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            print(f"[DigitalEmployee] create error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def update(item_id, data):
        """更新数字员工"""
        conn = get_connection()
        try:
            fields = []
            values = []
            for key in ("name", "type", "description", "avatar", "model_id",
                        "system_prompt", "skills", "crawl4ai_enabled",
                        "api_url", "api_method", "api_headers", "api_params",
                        "api_response_template", "card_config", "sort_order", "status"):
                if key in data:
                    fields.append(f"{key} = ?")
                    values.append(data[key])
            if fields:
                fields.append("updated_at = datetime('now','localtime')")
                values.append(item_id)
                sql = f"UPDATE digital_employees SET {', '.join(fields)} WHERE id = ?"
                conn.execute(sql, values)
                conn.commit()
                return True
            return False
        except Exception as e:
            print(f"[DigitalEmployee] update error: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def delete(item_id):
        """删除数字员工"""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM digital_employees WHERE id = ?", (item_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def get_all_models():
        """获取所有已启用的模型（用于选择关联模型）"""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, name, model_name FROM ai_models WHERE status=1 ORDER BY sort_order, id"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
