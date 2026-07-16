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

    # ────────────── 管理侧方法（跨用户）──────────────

    @staticmethod
    def get_all_admin(page=1, page_size=20, search=None):
        """分页获取所有用户的会话（JOIN users 获取用户名）"""
        offset = (page - 1) * page_size
        with get_connection() as conn:
            if search:
                search_term = f"%{search}%"
                count_sql = """SELECT COUNT(*) FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.title LIKE ? OR u.username LIKE ?"""
                data_sql = """SELECT c.*, u.username FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.title LIKE ? OR u.username LIKE ?
                    ORDER BY c.updated_at DESC LIMIT ? OFFSET ?"""
                total = conn.execute(count_sql, (search_term, search_term)).fetchone()[0]
                rows = conn.execute(data_sql, (search_term, search_term, page_size, offset)).fetchall()
            else:
                total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
                rows = conn.execute(
                    """SELECT c.*, u.username FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    ORDER BY c.updated_at DESC LIMIT ? OFFSET ?""",
                    (page_size, offset)
                ).fetchall()
        data = []
        for r in rows:
            item = dict(r)
            messages = json.loads(item.get("messages", "[]"))
            item["msg_count"] = len(messages)
            item.pop("messages", None)  # 列表不返回完整消息
            data.append(item)
        return {"total": total, "data": data, "page": page, "page_size": page_size}

    @staticmethod
    def get_by_id_admin(conv_id):
        """获取单个会话（不含 user_id 校验），含完整 messages"""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT c.*, u.username FROM conversations c JOIN users u ON c.user_id = u.id WHERE c.id=?",
                (conv_id,)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["messages"] = json.loads(item.get("messages", "[]"))
        return item

    @staticmethod
    def delete_admin(conv_id):
        """删除会话（不含 user_id 校验）"""
        with get_connection() as conn:
            conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
            conn.commit()
            return True

    @staticmethod
    def delete_message(conv_id, msg_index):
        """删除会话中指定索引的单条消息"""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT messages FROM conversations WHERE id=?", (conv_id,)
            ).fetchone()
            if not row:
                return False
            messages = json.loads(row["messages"] or "[]")
            if msg_index < 0 or msg_index >= len(messages):
                return False
            messages.pop(msg_index)
            conn.execute(
                "UPDATE conversations SET messages=?, updated_at=datetime('now','localtime') WHERE id=?",
                (json.dumps(messages, ensure_ascii=False), conv_id)
            )
            conn.commit()
            return True

    @staticmethod
    def get_all_messages_admin(page=1, page_size=20, search=None):
        """分页获取所有会话的所有消息（展平），用于对话管理页面"""
        # 先获取所有会话
        with get_connection() as conn:
            if search:
                search_term = f"%{search}%"
                rows = conn.execute(
                    """SELECT c.id, c.user_id, c.title, c.messages, c.updated_at, u.username
                    FROM conversations c JOIN users u ON c.user_id = u.id
                    WHERE c.messages LIKE ?
                    ORDER BY c.updated_at DESC""",
                    (search_term,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT c.id, c.user_id, c.title, c.messages, c.updated_at, u.username
                    FROM conversations c JOIN users u ON c.user_id = u.id
                    ORDER BY c.updated_at DESC"""
                ).fetchall()

        # 展平所有消息
        all_messages = []
        for r in rows:
            item = dict(r)
            messages = json.loads(item.get("messages", "[]"))
            for i, msg in enumerate(messages):
                msg_content = msg.get("content", "")
                if search and search.lower() not in str(msg_content).lower():
                    continue
                all_messages.append({
                    "conv_id": item["id"],
                    "conv_title": item["title"],
                    "user_id": item["user_id"],
                    "username": item["username"],
                    "msg_index": i,
                    "role": msg.get("role", ""),
                    "content": msg_content,
                    "employee_name": msg.get("employee_name", ""),
                    "tokens": msg.get("tokens", 0),
                    "time_ms": msg.get("time_ms", 0),
                    "conv_updated_at": item["updated_at"]
                })

        # 分页
        total = len(all_messages)
        start = (page - 1) * page_size
        end = start + page_size
        return {"total": total, "data": all_messages[start:end], "page": page, "page_size": page_size}
