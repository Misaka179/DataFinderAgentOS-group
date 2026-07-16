import os
import sqlite3

from app.config import config
from app.utils.logger import get_logger

logger = get_logger('db')

DB_PATH = config.DB_PATH


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role_id INTEGER NOT NULL DEFAULT 2,
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                code TEXT NOT NULL UNIQUE,
                description TEXT,
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER DEFAULT 0,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                icon TEXT,
                route TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (parent_id) REFERENCES functions(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                func_id INTEGER NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (role_id) REFERENCES roles(id),
                FOREIGN KEY (func_id) REFERENCES functions(id),
                UNIQUE(role_id, func_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS role_functions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                func_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (role_id) REFERENCES roles(id),
                FOREIGN KEY (func_id) REFERENCES functions(id),
                UNIQUE(role_id, func_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url_template TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'GET',
                headers TEXT NOT NULL DEFAULT '{}',
                keyword_param TEXT NOT NULL DEFAULT 'word',
                page_param TEXT DEFAULT 'pn',
                page_step INTEGER NOT NULL DEFAULT 10,
                status INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        try:
            conn.execute("ALTER TABLE watch_sources ADD COLUMN source_type TEXT NOT NULL DEFAULT 'baidu_news'")
        except Exception:
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_collected_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                summary TEXT,
                source_name TEXT,
                collected_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (source_id) REFERENCES watch_sources(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_warehouse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT,
                summary TEXT,
                source_name TEXT,
                keyword TEXT,
                source_id INTEGER DEFAULT 0,
                is_deep_collected INTEGER NOT NULL DEFAULT 0,
                collected_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'openai',
                model_name TEXT NOT NULL,
                api_base_url TEXT,
                api_key TEXT,
                max_tokens INTEGER NOT NULL DEFAULT 4096,
                token_count INTEGER NOT NULL DEFAULT 0,
                is_default INTEGER NOT NULL DEFAULT 0,
                status INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT 'text',
                system_prompt TEXT DEFAULT '',
                temperature REAL NOT NULL DEFAULT 0.7,
                top_p REAL NOT NULL DEFAULT 1.0,
                context_length INTEGER NOT NULL DEFAULT 4096,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS digital_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'llm',
                description TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                status INTEGER NOT NULL DEFAULT 1,
                model_id INTEGER DEFAULT NULL,
                system_prompt TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                crawl4ai_enabled INTEGER NOT NULL DEFAULT 0,
                api_url TEXT DEFAULT '',
                api_method TEXT DEFAULT 'GET',
                api_headers TEXT DEFAULT '{}',
                api_params TEXT DEFAULT '{}',
                api_response_template TEXT DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deep_collect_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_id INTEGER NOT NULL,
                employee_id INTEGER DEFAULT NULL,
                employee_name TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                progress INTEGER NOT NULL DEFAULT 0,
                steps TEXT NOT NULL DEFAULT '[]',
                logs TEXT NOT NULL DEFAULT '[]',
                result_data TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                started_at TEXT,
                completed_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deep_collect_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                warehouse_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                crawled_title TEXT DEFAULT '',
                crawled_content TEXT DEFAULT '',
                analysis_result TEXT DEFAULT '',
                extra_data TEXT DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (warehouse_id) REFERENCES data_warehouse(id),
                FOREIGN KEY (task_id) REFERENCES deep_collect_tasks(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                messages TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sensitive_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT '一般',
                severity TEXT DEFAULT 'medium',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public_opinion_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT,
                source_content TEXT,
                matched_word TEXT NOT NULL,
                word_category TEXT DEFAULT '一般',
                severity TEXT DEFAULT 'medium',
                risk_analysis TEXT,
                risk_score REAL DEFAULT 0,
                status TEXT DEFAULT 'unread',
                user_feedback TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()


def run_runtime_checks():
    conn = get_connection()
    try:
        _ensure_all_funcs_in_menus(conn)
        _recover_stalled_deep_collect_tasks(conn)
        conn.commit()
    except Exception as e:
        logger.error(f"运行时检查出错: {e}")
        conn.rollback()
    finally:
        conn.close()


def _ensure_all_funcs_in_menus(conn):
    admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
    if not admin_role:
        return
    admin_role_id = admin_role["id"]

    all_funcs = conn.execute("SELECT id, name FROM functions WHERE status=1 ORDER BY sort_order, id").fetchall()
    added_count = 0
    for func in all_funcs:
        conn.execute(
            "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
            (admin_role_id, func["id"])
        )
        menu_exists = conn.execute(
            "SELECT id FROM menus WHERE role_id=? AND func_id=?",
            (admin_role_id, func["id"])
        ).fetchone()
        if not menu_exists:
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role_id,)
            ).fetchone()[0] or 0
            conn.execute(
                "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                (admin_role_id, func["id"], max_order + 1)
            )
            added_count += 1
    if added_count > 0:
        logger.info(f"已为管理员补充 {added_count} 个功能菜单")


def _recover_stalled_deep_collect_tasks(conn):
    """服务重启后，将中断的 running/pending 深度采集任务标记为 failed"""
    import datetime
    stalled = conn.execute(
        "SELECT COUNT(*) FROM deep_collect_tasks WHERE status IN ('running', 'pending')"
    ).fetchone()[0]
    if stalled > 0:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE deep_collect_tasks SET status='failed', error_message=?, updated_at=? WHERE status IN ('running', 'pending')",
            (f"服务器重启，任务中断（{now}）", now)
        )
        logger.info(f"已恢复 {stalled} 个中断的深度采集任务（标记为 failed）")
