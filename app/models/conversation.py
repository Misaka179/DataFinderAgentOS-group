"""对话数据隔离：每个用户存储自己的对话记录"""
import json
from app.models.db import get_connection


class ConversationRepository:

    @staticmethod
    def get_by_user(user_id, page=1, page_size=50):
        """获取指定用户的所有对话，按更新时间倒序"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id=? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (user_id, page_size, offset)
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE user_id=?", (user_id,)
            ).fetchone()[0]
        data = []
        for r in rows:
            item = dict(r)
            item["messages"] = json.loads(item.get("messages", "[]"))
            data.append(item)
        return {"total": total, "data": data}

    @staticmethod
    def get_by_id(conv_id, user_id):
        """获取单个对话（需校验user_id确保数据隔离）"""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id=? AND user_id=?", (conv_id, user_id)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["messages"] = json.loads(item.get("messages", "[]"))
        return item

    @staticmethod
    def create(user_id, title="新对话", messages=None):
        """创建新对话"""
        if messages is None:
            messages = []
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO conversations (user_id, title, messages) VALUES (?, ?, ?)",
                (user_id, title, json.dumps(messages, ensure_ascii=False))
            )
            conn.commit()
            return cur.lastrowid

    @staticmethod
    def update(conv_id, user_id, **kwargs):
        """更新对话（标题、消息等），需校验user_id"""
        allowed = {"title", "messages"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return False
        if "messages" in fields and isinstance(fields["messages"], list):
            fields["messages"] = json.dumps(fields["messages"], ensure_ascii=False)
        fields["updated_at"] = "datetime('now', 'localtime')"  # SQL表达式
        set_clause = ", ".join(f"{k}=?" for k in fields if k != "updated_at")
        set_clause += ", updated_at=datetime('now', 'localtime')"
        values = [fields[k] for k in fields if k != "updated_at"]
        values += [conv_id, user_id]
        with get_connection() as conn:
            conn.execute(
                f"UPDATE conversations SET {set_clause} WHERE id=? AND user_id=?",
                values
            )
            conn.commit()
            return True

    @staticmethod
    def delete(conv_id, user_id):
        """删除对话，需校验user_id"""
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM conversations WHERE id=? AND user_id=?", (conv_id, user_id)
            )
            conn.commit()
            return True
