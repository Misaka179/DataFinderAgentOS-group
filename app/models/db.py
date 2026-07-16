import os
import sqlite3

def project_root():
    # 当前项目的 ../DataFinderAgentOS/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

DB_PATH = os.path.join(project_root(), "database", "finderos.db")

def get_connection():
    # 获得一个数据库的连接，用于操作数据库完成事务和数据操作
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        # 用户表
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
        
        # 角色表
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
        
        # 功能表（一级+二级）
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
        
        # 菜单表
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
        
        # 角色-功能关联表
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
        
        # 瞭源管理表（采集源 + 采集规则）
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

        # Migration: add source_type column for multi-source parser dispatch
        try:
            conn.execute("ALTER TABLE watch_sources ADD COLUMN source_type TEXT NOT NULL DEFAULT 'baidu_news'")
        except Exception:
            pass

        # 瞭望采集数据表
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
        
        # 数据仓库表
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
        
        # 模型引擎表（OpenAI API范式）
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
        
        # 模型表迁移：兼容已有表添加新字段
        try:
            conn.execute("ALTER TABLE ai_models ADD COLUMN category TEXT NOT NULL DEFAULT 'text'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE ai_models ADD COLUMN system_prompt TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE ai_models ADD COLUMN temperature REAL NOT NULL DEFAULT 0.7")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE ai_models ADD COLUMN top_p REAL NOT NULL DEFAULT 1.0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE ai_models ADD COLUMN context_length INTEGER NOT NULL DEFAULT 4096")
        except Exception:
            pass
        
        # 数字员工表
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS digital_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'llm',
                description TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                status INTEGER NOT NULL DEFAULT 1,
                -- 类型1：LLM 相关字段
                model_id INTEGER DEFAULT NULL,
                system_prompt TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                crawl4ai_enabled INTEGER NOT NULL DEFAULT 0,
                -- 类型2：API 相关字段
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
        
        # 数字员工表兼容迁移：添加新字段（如果表已存在）
        for mig_col, mig_def in [
            ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
            ("avatar", "TEXT DEFAULT ''"),
            ("system_prompt", "TEXT DEFAULT ''"),
            ("skills", "TEXT DEFAULT '[]'"),
            ("api_params", "TEXT DEFAULT '{}'"),
            ("api_response_template", "TEXT DEFAULT ''"),
            ("card_config", "TEXT DEFAULT '{}'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE digital_employees ADD COLUMN {mig_col} {mig_def}")
            except Exception:
                pass
        
        # 数字员工表数据迁移：旧列 → 新列
        try:
            conn.execute("UPDATE digital_employees SET system_prompt = prompt WHERE system_prompt = '' AND prompt != ''")
        except Exception:
            pass
        try:
            conn.execute("UPDATE digital_employees SET skills = skill_config WHERE skills = '[]' AND skill_config != ''")
        except Exception:
            pass
        try:
            conn.execute("UPDATE digital_employees SET api_params = api_params_template WHERE api_params = '{}' AND api_params_template != ''")
        except Exception:
            pass
        try:
            conn.execute("UPDATE digital_employees SET api_response_template = response_format WHERE api_response_template = '' AND response_format != ''")
        except Exception:
            pass
        
        # 深度采集任务表
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
        # 深度采集任务表兼容迁移
        try:
            conn.execute("ALTER TABLE deep_collect_tasks ADD COLUMN employee_name TEXT DEFAULT ''")
        except Exception:
            pass
        
        # 深度采集数据表（存储实际采集到的详细数据）
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
        
        # 用户对话表（数据隔离：每个用户存储自己的对话记录）
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
        
        # 敏感词表
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
        
        # 舆情告警表
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
        
        # 插入默认角色（如果不存在）
        cursor = conn.execute("SELECT id FROM roles WHERE code = 'admin'")
        if not cursor.fetchone():
            conn.execute(
                "INSERT INTO roles (name, code, description, status) VALUES (?, ?, ?, ?)",
                ("系统管理员", "admin", "拥有系统所有权限", 1)
            )
            conn.execute(
                "INSERT INTO roles (name, code, description, status) VALUES (?, ?, ?, ?)",
                ("普通用户", "user", "只能登录前台用户侧", 1)
            )
        
        # 插入默认功能（如果不存在）
        func_count = conn.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
        if func_count == 0:
            # 一级功能
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("控制台", "dashboard", "layui-icon-home", "/admin/index", 1, 0, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("管理系统", "management", "layui-icon-set", "", 2, 0, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("瞭望中心", "watch_center", "layui-icon-engine", "", 3, 0, 1)
            )
            mgmt_id = conn.execute("SELECT id FROM functions WHERE code='management'").fetchone()["id"]
            watch_center_id = conn.execute("SELECT id FROM functions WHERE code='watch_center'").fetchone()["id"]
            # 二级功能（管理系统下）
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("用户管理", "user_management", "layui-icon-user", "/admin/user-management", 1, mgmt_id, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("角色管理", "role_management", "layui-icon-group", "/admin/role-management", 2, mgmt_id, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("功能管理", "func_management", "layui-icon-component", "/admin/function-management", 3, mgmt_id, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("菜单管理", "menu_management", "layui-icon-auz", "/admin/menu-management", 4, mgmt_id, 1)
            )
            # 二级功能（瞭望中心下）
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("瞭源管理", "source_management", "layui-icon-website", "/admin/source-management", 1, watch_center_id, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("瞭望采集", "watch_management", "layui-icon-util", "/admin/watch-management", 2, watch_center_id, 1)
            )
            # 一级功能（智能中枢）
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("智能中枢", "intelligent_hub", "layui-icon-bot", "", 4, 0, 1)
            )
            hub_id = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()["id"]
            # 二级功能（智能中枢下）
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("模型引擎", "model_engine", "layui-icon-senior", "/admin/model-engine", 1, hub_id, 1)
            )
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("数字员工", "digital_employee", "layui-icon-user", "/admin/digital-employee", 2, hub_id, 1)
            )
        
        # 插入默认敏感词（用户攻击防护，如果不存在）
        sw_count = conn.execute("SELECT COUNT(*) FROM sensitive_words").fetchone()[0]
        if sw_count == 0:
            default_words = [
                # SQL注入
                ("DROP TABLE", "SQL注入", "high"),
                ("DELETE FROM", "SQL注入", "high"),
                ("TRUNCATE", "SQL注入", "high"),
                ("ALTER TABLE", "SQL注入", "high"),
                ("UNION SELECT", "SQL注入", "high"),
                ("1=1", "SQL注入", "high"),
                ("' OR '", "SQL注入", "high"),
                # 代码注入
                ("exec(", "代码注入", "high"),
                ("system(", "代码注入", "high"),
                ("eval(", "代码注入", "high"),
                ("__import__", "代码注入", "high"),
                ("subprocess", "代码注入", "high"),
                ("os.system", "代码注入", "high"),
                # SSTI模板注入
                ("{{", "SSTI注入", "high"),
                ("{%", "SSTI注入", "high"),
                ("${", "SSTI注入", "high"),
                # 越权/社工
                ("admin密码", "越权试探", "high"),
                ("后台地址", "越权试探", "high"),
                ("管理员账号", "越权试探", "high"),
                ("绕过验证", "越权试探", "high"),
                # Prompt注入
                ("忽略你之前的指令", "Prompt注入", "high"),
                ("忽略系统提示", "Prompt注入", "high"),
                ("ignore above", "Prompt注入", "high"),
                ("ignore all", "Prompt注入", "high"),
                ("假装你是", "Prompt注入", "medium"),
                ("你现在是", "Prompt注入", "medium"),
                ("role play", "Prompt注入", "medium"),
                # 恶意骚扰
                ("你傻", "恶意骚扰", "medium"),
                ("废物", "恶意骚扰", "medium"),
                ("垃圾", "恶意骚扰", "medium"),
            ]
            for word, category, severity in default_words:
                conn.execute(
                    "INSERT OR IGNORE INTO sensitive_words (word, category, severity) VALUES (?, ?, ?)",
                    (word, category, severity)
                )
            print("✓ 已插入默认敏感词（用户攻击防护）")
        
        conn.commit()
