"""技能管理数据访问层"""
import json
from app.models.db import get_connection


class SkillRepository:
    @staticmethod
    def get_all(page=1, size=20, keyword="", status=None):
        """分页查询技能列表，支持名称/编码搜索和状态过滤"""
        offset = (page - 1) * size
        conditions = []
        params = []

        if keyword:
            conditions.append("(name LIKE ? OR code LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if status is not None and status != "":
            conditions.append("status = ?")
            params.append(int(status))

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        db = get_connection()
        total = db.execute(f"SELECT COUNT(*) FROM skills{where}", params).fetchone()[0]
        rows = db.execute(
            f"SELECT * FROM skills{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [size, offset]
        ).fetchall()
        return total, [dict(r) for r in rows]

    @staticmethod
    def get_by_id(skill_id):
        db = get_connection()
        row = db.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_code(code):
        db = get_connection()
        row = db.execute("SELECT * FROM skills WHERE code=?", (code,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_enabled_list():
        """获取所有启用状态的技能（供数字员工关联选择）"""
        db = get_connection()
        rows = db.execute(
            "SELECT id, name, code, type, impl_type, description FROM skills WHERE status=1 ORDER BY name"
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_ids(skill_ids):
        """根据ID列表批量获取技能"""
        if not skill_ids:
            return []
        placeholders = ",".join("?" for _ in skill_ids)
        db = get_connection()
        rows = db.execute(
            f"SELECT * FROM skills WHERE id IN ({placeholders}) AND status=1 ORDER BY name",
            skill_ids
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def create(data):
        db = get_connection()
        db.execute(
            """INSERT INTO skills (name, code, type, impl_type, impl_config, input_schema,
               output_schema, status, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["name"], data["code"], data.get("type", "custom"), data["impl_type"],
             json.dumps(data.get("impl_config", {}), ensure_ascii=False),
             json.dumps(data.get("input_schema", {}), ensure_ascii=False),
             json.dumps(data.get("output_schema", {}), ensure_ascii=False),
             data.get("status", 1), data.get("description", ""))
        )
        db.commit()

    @staticmethod
    def update(data):
        db = get_connection()
        db.execute(
            """UPDATE skills SET name=?, code=?, type=?, impl_type=?, impl_config=?,
               input_schema=?, output_schema=?, status=?, description=?,
               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (data["name"], data["code"], data.get("type", "custom"), data["impl_type"],
             json.dumps(data.get("impl_config", {}), ensure_ascii=False),
             json.dumps(data.get("input_schema", {}), ensure_ascii=False),
             json.dumps(data.get("output_schema", {}), ensure_ascii=False),
             data.get("status", 1), data.get("description", ""), data["id"])
        )
        db.commit()

    @staticmethod
    def delete(skill_id):
        db = get_connection()
        db.execute("DELETE FROM skills WHERE id=? AND type='custom'", (skill_id,))
        db.commit()

    @staticmethod
    def toggle_status(skill_id):
        db = get_connection()
        skill = db.execute("SELECT id, status FROM skills WHERE id=?", (skill_id,)).fetchone()
        if skill:
            new_status = 0 if skill["status"] == 1 else 1
            db.execute("UPDATE skills SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
                       (new_status, skill_id))
            db.commit()
            return new_status
        return None
