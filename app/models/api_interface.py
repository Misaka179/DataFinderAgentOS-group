"""API 接口管理 — 数据仓库层"""

import json
from app.models.db import get_connection


class ApiInterfaceRepository:
    """API 接口仓库"""

    @staticmethod
    def get_all(page=1, page_size=20, search=None, status=None):
        """分页查询接口列表"""
        conn = get_connection()
        try:
            conditions = []
            params = []

            if search:
                conditions.append("(name LIKE ? OR code LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])
            if status is not None:
                conditions.append("status = ?")
                params.append(int(status))

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            count_sql = f"SELECT COUNT(*) FROM api_interfaces {where}"
            total = conn.execute(count_sql, params).fetchone()[0]

            offset = (page - 1) * page_size
            data_sql = f"SELECT * FROM api_interfaces {where} ORDER BY id DESC LIMIT ? OFFSET ?"
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
    def get_by_id(interface_id):
        """根据ID获取接口"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM api_interfaces WHERE id=?", (interface_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_enabled_list():
        """获取所有启用状态的接口（供数字员工选择用）"""
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, name, code, method, url, headers, params "
                "FROM api_interfaces WHERE status=1 ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def create(name, code, description, method, url, headers, params, status=1):
        """创建接口"""
        conn = get_connection()
        try:
            # 检查编码唯一性
            exist = conn.execute("SELECT id FROM api_interfaces WHERE code=?", (code,)).fetchone()
            if exist:
                return None, "接口编码已存在"

            conn.execute(
                """INSERT INTO api_interfaces (name, code, description, method, url, headers, params, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, code, description, method, url, headers, params, status)
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0], None
        finally:
            conn.close()

    @staticmethod
    def update(interface_id, name, code, description, method, url, headers, params, status):
        """更新接口"""
        conn = get_connection()
        try:
            # 检查编码唯一性（排除自身）
            exist = conn.execute(
                "SELECT id FROM api_interfaces WHERE code=? AND id!=?", (code, interface_id)
            ).fetchone()
            if exist:
                return False, "接口编码已存在"

            conn.execute(
                """UPDATE api_interfaces SET name=?, code=?, description=?, method=?, url=?, 
                   headers=?, params=?, status=? WHERE id=?""",
                (name, code, description, method, url, headers, params, status, interface_id)
            )
            conn.commit()
            return True, None
        finally:
            conn.close()

    @staticmethod
    def delete(interface_id):
        """删除接口"""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM api_interfaces WHERE id=?", (interface_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def toggle_status(interface_id):
        """切换接口启用/禁用状态"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT status FROM api_interfaces WHERE id=?", (interface_id,)).fetchone()
            if not row:
                return None
            new_status = 0 if row["status"] == 1 else 1
            conn.execute("UPDATE api_interfaces SET status=? WHERE id=?", (new_status, interface_id))
            conn.commit()
            return new_status
        finally:
            conn.close()
