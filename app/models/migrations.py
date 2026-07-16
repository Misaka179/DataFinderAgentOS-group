import hashlib
import secrets
import json

from app.models.db import get_connection
from app.config import config
from app.utils.logger import get_logger

logger = get_logger('migrations')


def run_migrations():
    conn = get_connection()
    try:
        _ensure_migration_table(conn)
        
        migrations = [
            _migrate_ai_models_add_fields,
            _migrate_digital_employees_add_fields,
            _migrate_digital_employees_data_migration,
            _migrate_deep_collect_tasks_add_fields,
            _migrate_default_roles,
            _migrate_default_functions,
            _migrate_default_sensitive_words,
            _migrate_watch_center_structure,
            _migrate_rename_watch_management,
            _migrate_move_source_watch_to_center,
            _migrate_add_data_warehouse,
            _migrate_model_engine_icon,
            _migrate_intelligent_hub_icon,
            _migrate_fill_warehouse_keywords,
            _migrate_model_engine_function,
            _migrate_ai_models_initial,
            _migrate_intelligent_hub_function,
            _migrate_move_model_engine_to_hub,
            _migrate_move_digital_employee_to_hub,
            _migrate_digital_employee_function,
            _migrate_digital_employees_initial,
            _migrate_weather_api_update,
            _migrate_weather_api_fix_url,
            _migrate_weather_api_fix_user_agent,
            _migrate_weather_api_json_format,
            _migrate_big_screen_to_data_screen,
            _migrate_data_screen_function,
            _migrate_opinion_screen_function,
            _migrate_sensitive_words_to_attack_protection,
            _create_default_admin,
            _create_baidu_watch_source,
            _migrate_watch_sources_source_type,
            _create_hackernews_watch_source,
            _create_36kr_watch_source,
            _migrate_encrypt_api_keys,
            _migrate_digital_employees_update_descs,
            _migrate_ai_models_replace_static,
            _migrate_api_interface_table,
            _migrate_api_interface_function,
            _migrate_api_interface_seed,
            _migrate_api_interface_reorder,
            _migrate_digital_employees_api_config,
            _migrate_skill_table,
            _migrate_skill_function,
            _migrate_skill_seed,
            _migrate_conversation_management_function,
        ]
        
        for migration in migrations:
            migration_name = migration.__name__
            if _is_migration_done(conn, migration_name):
                continue
            try:
                migration(conn)
                _mark_migration_done(conn, migration_name)
                logger.info(f"迁移完成: {migration_name}")
            except Exception as e:
                logger.error(f"迁移 {migration_name} 失败: {e}")
                conn.rollback()
                raise
        
        conn.commit()
        logger.info("所有迁移完成")
    except Exception as e:
        logger.error(f"迁移执行出错: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_migration_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            executed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)


def _is_migration_done(conn, name):
    row = conn.execute("SELECT id FROM migrations WHERE name=?", (name,)).fetchone()
    return row is not None


def _mark_migration_done(conn, name):
    conn.execute("INSERT OR IGNORE INTO migrations (name) VALUES (?)", (name,))


def _migrate_ai_models_add_fields(conn):
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


def _migrate_digital_employees_add_fields(conn):
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


def _migrate_digital_employees_data_migration(conn):
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


def _migrate_deep_collect_tasks_add_fields(conn):
    try:
        conn.execute("ALTER TABLE deep_collect_tasks ADD COLUMN employee_name TEXT DEFAULT ''")
    except Exception:
        pass


def _migrate_default_roles(conn):
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


def _migrate_default_functions(conn):
    func_count = conn.execute("SELECT COUNT(*) FROM functions").fetchone()[0]
    if func_count == 0:
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
        
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("瞭源管理", "source_management", "layui-icon-website", "/admin/source-management", 1, watch_center_id, 1)
        )
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("瞭望采集", "watch_management", "layui-icon-util", "/admin/watch-management", 2, watch_center_id, 1)
        )
        
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("智能中枢", "intelligent_hub", "layui-icon-bot", "", 4, 0, 1)
        )
        hub_id = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()["id"]
        
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("模型引擎", "model_engine", "layui-icon-senior", "/admin/model-engine", 1, hub_id, 1)
        )
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("数字员工", "digital_employee", "layui-icon-user", "/admin/digital-employee", 2, hub_id, 1)
        )


def _migrate_default_sensitive_words(conn):
    sw_count = conn.execute("SELECT COUNT(*) FROM sensitive_words").fetchone()[0]
    if sw_count == 0:
        default_words = [
            ("DROP TABLE", "SQL注入", "high"),
            ("DELETE FROM", "SQL注入", "high"),
            ("TRUNCATE", "SQL注入", "high"),
            ("ALTER TABLE", "SQL注入", "high"),
            ("UNION SELECT", "SQL注入", "high"),
            ("1=1", "SQL注入", "high"),
            ("' OR '", "SQL注入", "high"),
            ("exec(", "代码注入", "high"),
            ("system(", "代码注入", "high"),
            ("eval(", "代码注入", "high"),
            ("__import__", "代码注入", "high"),
            ("subprocess", "代码注入", "high"),
            ("os.system", "代码注入", "high"),
            ("{{", "SSTI注入", "high"),
            ("{%", "SSTI注入", "high"),
            ("${", "SSTI注入", "high"),
            ("admin密码", "越权试探", "high"),
            ("后台地址", "越权试探", "high"),
            ("管理员账号", "越权试探", "high"),
            ("绕过验证", "越权试探", "high"),
            ("忽略你之前的指令", "Prompt注入", "high"),
            ("忽略系统提示", "Prompt注入", "high"),
            ("ignore above", "Prompt注入", "high"),
            ("ignore all", "Prompt注入", "high"),
            ("假装你是", "Prompt注入", "medium"),
            ("你现在是", "Prompt注入", "medium"),
            ("role play", "Prompt注入", "medium"),
            ("你傻", "恶意骚扰", "medium"),
            ("废物", "恶意骚扰", "medium"),
            ("垃圾", "恶意骚扰", "medium"),
        ]
        for word, category, severity in default_words:
            conn.execute(
                "INSERT OR IGNORE INTO sensitive_words (word, category, severity) VALUES (?, ?, ?)",
                (word, category, severity)
            )


def _migrate_watch_center_structure(conn):
    watch_center = conn.execute("SELECT id FROM functions WHERE code='watch_center'").fetchone()
    if not watch_center:
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("瞭望中心", "watch_center", "layui-icon-engine", "", 3, 0, 1)
        )


def _migrate_rename_watch_management(conn):
    watch_func = conn.execute("SELECT id, name FROM functions WHERE code='watch_management'").fetchone()
    if watch_func and watch_func["name"] == "瞭望管理":
        conn.execute("UPDATE functions SET name='瞭望采集' WHERE id=?", (watch_func["id"],))


def _migrate_move_source_watch_to_center(conn):
    watch_center = conn.execute("SELECT id FROM functions WHERE code='watch_center'").fetchone()
    if not watch_center:
        return
    watch_center_id = watch_center["id"]
    
    source_func = conn.execute("SELECT id, parent_id FROM functions WHERE code='source_management'").fetchone()
    if source_func and source_func["parent_id"] != watch_center_id:
        conn.execute("UPDATE functions SET parent_id=?, sort_order=1 WHERE id=?", (watch_center_id, source_func["id"]))
    
    watch_func = conn.execute("SELECT id, parent_id FROM functions WHERE code='watch_management'").fetchone()
    if watch_func and watch_func["parent_id"] != watch_center_id:
        conn.execute("UPDATE functions SET parent_id=?, sort_order=2 WHERE id=?", (watch_center_id, watch_func["id"]))
    
    mgmt_id_row = conn.execute("SELECT id FROM functions WHERE code='management'").fetchone()
    if mgmt_id_row:
        mgmt_id = mgmt_id_row["id"]
        conn.execute("UPDATE functions SET parent_id=? WHERE code='source_management' AND parent_id=?", (watch_center_id, mgmt_id))
        conn.execute("UPDATE functions SET parent_id=? WHERE code='watch_management' AND parent_id=?", (watch_center_id, mgmt_id))
        conn.execute("UPDATE functions SET name='瞭望采集' WHERE code='watch_management' AND name='瞭望管理'")


def _migrate_add_data_warehouse(conn):
    warehouse_func = conn.execute("SELECT id FROM functions WHERE code='data_warehouse'").fetchone()
    if not warehouse_func:
        watch_center = conn.execute("SELECT id FROM functions WHERE code='watch_center'").fetchone()
        parent_id = watch_center["id"] if watch_center else 0
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("数据仓库", "data_warehouse", "layui-icon-template", "/admin/warehouse-management", 3, parent_id, 1)
        )


def _migrate_model_engine_icon(conn):
    conn.execute("UPDATE functions SET icon='layui-icon-senior' WHERE code='model_engine' AND icon!='layui-icon-senior'")


def _migrate_intelligent_hub_icon(conn):
    conn.execute("UPDATE functions SET icon='layui-icon-bot' WHERE code='intelligent_hub' AND icon!='layui-icon-bot'")


def _migrate_fill_warehouse_keywords(conn):
    conn.execute("""
        UPDATE data_warehouse SET keyword = (
            SELECT w.keyword FROM watch_collected_data w
            WHERE w.title = data_warehouse.title AND w.keyword != '' AND w.keyword IS NOT NULL
                AND (data_warehouse.keyword = '' OR data_warehouse.keyword IS NULL)
            LIMIT 1
        )
        WHERE (keyword = '' OR keyword IS NULL)
    """)


def _migrate_model_engine_function(conn):
    me_func = conn.execute("SELECT id FROM functions WHERE code='model_engine'").fetchone()
    if not me_func:
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("模型引擎", "model_engine", "layui-icon-senior", "/admin/model-engine", 4, 0, 1)
        )
        me_func = conn.execute("SELECT id FROM functions WHERE code='model_engine'").fetchone()
        
        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        if admin_role and me_func:
            conn.execute(
                "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                (admin_role["id"], me_func["id"])
            )
            conn.execute(
                "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                (admin_role["id"], me_func["id"], 20)
            )


def _migrate_ai_models_initial(conn):
    """内置4个AI模型（agnes-2.0-flash、qwen3.5-flash、DALL-E 3、Sora/视频生成）"""
    model_count = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0]
    if model_count == 0:
        conn.execute(
            """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
               max_tokens, token_count, is_default, status, sort_order, category,
               system_prompt, temperature, top_p, context_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("agnes-2.0-flash", "openai", "agnes-2.0-flash", "https://api.openai.com/v1", "",
             128000, 0, 1, 1, 1, "text", "You are a helpful assistant.", 0.7, 1.0, 128000)
        )
        conn.execute(
            """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
               max_tokens, token_count, is_default, status, sort_order, category,
               system_prompt, temperature, top_p, context_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("qwen3.5-flash", "openai", "qwen3.5-flash", "https://api.openai.com/v1", "",
             128000, 0, 0, 1, 2, "text", "You are a helpful assistant.", 0.7, 1.0, 128000)
        )
        conn.execute(
            """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
               max_tokens, token_count, is_default, status, sort_order, category,
               system_prompt, temperature, top_p, context_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("DALL-E 3", "openai", "dall-e-3", "https://aigc.aitoolcore.com/v1", "",
             0, 0, 0, 1, 3, "image", "", 0.7, 1.0, 4096)
        )
        conn.execute(
            """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
               max_tokens, token_count, is_default, status, sort_order, category,
               system_prompt, temperature, top_p, context_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Sora/视频生成", "openai", "video-gen", "https://aigc.aitoolcore.com/v1", "",
             0, 0, 0, 1, 4, "video", "", 0.7, 1.0, 4096)
        )


def _migrate_intelligent_hub_function(conn):
    hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
    if not hub_func:
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("智能中枢", "intelligent_hub", "layui-icon-bot", "", 4, 0, 1)
        )
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        
        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        if admin_role and hub_func:
            conn.execute(
                "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                (admin_role["id"], hub_func["id"])
            )
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role["id"],)
            ).fetchone()[0] or 0
            conn.execute(
                "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                (admin_role["id"], hub_func["id"], max_order + 1)
            )


def _migrate_move_model_engine_to_hub(conn):
    hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
    if hub_func:
        conn.execute(
            "UPDATE functions SET parent_id=?, sort_order=1 WHERE code='model_engine' AND parent_id=0",
            (hub_func["id"],)
        )


def _migrate_move_digital_employee_to_hub(conn):
    hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
    if hub_func:
        conn.execute(
            "UPDATE functions SET parent_id=?, sort_order=2 WHERE code='digital_employee' AND parent_id=0",
            (hub_func["id"],)
        )


def _migrate_digital_employee_function(conn):
    de_func = conn.execute("SELECT id FROM functions WHERE code='digital_employee'").fetchone()
    if not de_func:
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        parent_id = hub_func["id"] if hub_func else 0
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("数字员工", "digital_employee", "layui-icon-user", "/admin/digital-employee", 2, parent_id, 1)
        )
        de_func = conn.execute("SELECT id FROM functions WHERE code='digital_employee'").fetchone()
        
        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        if admin_role and de_func:
            conn.execute(
                "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                (admin_role["id"], de_func["id"])
            )
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role["id"],)
            ).fetchone()[0] or 0
            conn.execute(
                "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                (admin_role["id"], de_func["id"], max_order + 1)
            )


def _migrate_digital_employees_initial(conn):
    """内置6个数字员工（逐个检查，确保始终存在）"""
    default_model = conn.execute("SELECT id FROM ai_models WHERE is_default=1 LIMIT 1").fetchone()
    model_id = default_model["id"] if default_model else None

    # 1. 采集专员（LLM型）
    if not conn.execute("SELECT id FROM digital_employees WHERE name='采集专员'").fetchone():
        conn.execute(
            """INSERT INTO digital_employees 
               (name, type, description, model_id, system_prompt, skills, crawl4ai_enabled, sort_order, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "采集专员",
                "llm",
                "负责深度采集任务，自动获取指定数据并给出结果",
                model_id,
                "你是一个专业的数据采集专员，负责从互联网采集、整理和分析数据。请根据用户需求，全面获取相关信息并给出结构化的分析结果。",
                json.dumps([{"name": "深度采集", "description": "执行深度数据采集任务", "action": "deep_collect"}], ensure_ascii=False),
                1,
                1, 1
            )
        )

    # 2. 天气（API型）
    if not conn.execute("SELECT id FROM digital_employees WHERE name='天气'").fetchone():
        conn.execute(
            """INSERT INTO digital_employees 
               (name, type, description, api_url, api_method, api_headers, api_params, api_response_template, sort_order, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "天气",
                "api",
                "查询天气信息，支持通过城市名称获取实时天气数据",
                "https://wttr.in/{city}",
                "GET",
                json.dumps({}, ensure_ascii=False),
                json.dumps({"format": "j1", "lang": "zh"}, ensure_ascii=False),
                "current_condition.0.lang_zh.0.value",
                2, 1
            )
        )

    # 3. 新闻（API型-内置Mock）
    if not conn.execute("SELECT id FROM digital_employees WHERE name='新闻'").fetchone():
        conn.execute(
            """INSERT INTO digital_employees 
               (name, type, description, api_url, api_method, api_headers, api_params, api_response_template, sort_order, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "新闻",
                "api",
                "返回实时热门新闻（聚合数据API+百度兜底，含标题、来源、时间、摘要、链接）",
                "http://localhost:10010/api/mock/news",
                "GET",
                json.dumps({}, ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                "",
                3, 1
            )
        )

    # 4. 随机音乐（API型-内置Mock，iTunes真实音源）
    if not conn.execute("SELECT id FROM digital_employees WHERE name='随机音乐'").fetchone():
        conn.execute(
            """INSERT INTO digital_employees 
               (name, type, description, api_url, api_method, api_headers, api_params, api_response_template, sort_order, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "随机音乐",
                "api",
                "随机推荐一首歌，iTunes真实音源，含歌名、歌手、封面、播放链接",
                "http://localhost:10010/api/mock/music",
                "GET",
                json.dumps({}, ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                "",
                4, 1
            )
        )

    # 5. 电影（API型-内置Mock，豆瓣搜索+本地详情）
    if not conn.execute("SELECT id FROM digital_employees WHERE name='电影'").fetchone():
        conn.execute(
            """INSERT INTO digital_employees 
               (name, type, description, api_url, api_method, api_headers, api_params, api_response_template, sort_order, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "电影",
                "api",
                "搜索电影信息，TMDB API+豆瓣补充+本地详情，含导演、演员、简介、评分、年份",
                "http://localhost:10010/api/mock/movie?keyword={query}",
                "GET",
                json.dumps({}, ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                "",
                5, 1
            )
        )

    # 6. 小dummy（文案生成助手）（LLM型）
    if not conn.execute("SELECT id FROM digital_employees WHERE name LIKE '%小dummy%'").fetchone():
        conn.execute(
            """INSERT INTO digital_employees 
               (name, type, description, model_id, system_prompt, skills, crawl4ai_enabled, sort_order, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "小dummy（文案生成助手）",
                "llm",
                "具有特定步骤的文案生成助手",
                model_id,
                "你是小dummy，一个专业的文案生成助手。请严格按照工作步骤执行任务：分析需求→查阅模板→撰写大纲→生成正文→润色优化。",
                json.dumps([{"name": "文案生成", "description": "按照工作步骤生成专业文案", "action": "copywriting"}], ensure_ascii=False),
                0,
                6, 1
            )
        )


def _migrate_digital_employees_update_descs(conn):
    """更新数字员工描述，与当前API实现同步"""
    news_emp = conn.execute("SELECT id, description FROM digital_employees WHERE name='新闻'").fetchone()
    if news_emp and "聚合数据" not in (news_emp["description"] or ""):
        conn.execute(
            "UPDATE digital_employees SET description=? WHERE id=?",
            ("返回实时热门新闻（聚合数据API+百度兜底，含标题、来源、时间、摘要、链接）", news_emp["id"])
        )

    movie_emp = conn.execute("SELECT id, description FROM digital_employees WHERE name='电影'").fetchone()
    if movie_emp and "TMDB" not in (movie_emp["description"] or ""):
        conn.execute(
            "UPDATE digital_employees SET description=? WHERE id=?",
            ("搜索电影信息，TMDB API+豆瓣补充+本地详情，含导演、演员、简介、评分、年份", movie_emp["id"])
        )


def _migrate_weather_api_update(conn):
    weather_emp = conn.execute("SELECT id, api_url FROM digital_employees WHERE name='天气'").fetchone()
    if weather_emp and weather_emp["api_url"] and "openweathermap" in weather_emp["api_url"]:
        conn.execute(
            """UPDATE digital_employees SET 
               api_url=?, api_headers=?, api_params=?, api_response_template=?, description=?
               WHERE id=?""",
            (
                "https://wttr.in/{city}",
                json.dumps({}, ensure_ascii=False),
                json.dumps({"format": "%C+%t+%h+%w", "lang": "zh"}, ensure_ascii=False),
                "",
                "查询天气信息，支持通过城市名称获取实时天气数据",
                weather_emp["id"]
            )
        )


def _migrate_weather_api_fix_url(conn):
    weather_emp = conn.execute("SELECT id, api_url FROM digital_employees WHERE name='天气' AND api_url='https://wttr.in'").fetchone()
    if weather_emp:
        conn.execute(
            "UPDATE digital_employees SET api_url=?, api_params=?, api_headers=? WHERE id=?",
            ("https://wttr.in/{city}",
             json.dumps({"format": "%C+%t+%h+%w", "lang": "zh"}, ensure_ascii=False),
             json.dumps({}, ensure_ascii=False),
             weather_emp["id"])
        )


def _migrate_weather_api_fix_user_agent(conn):
    weather_emp = conn.execute("SELECT id, api_headers FROM digital_employees WHERE name='天气' AND api_headers LIKE '%Mozilla%'").fetchone()
    if weather_emp:
        conn.execute(
            "UPDATE digital_employees SET api_headers=? WHERE id=?",
            (json.dumps({}, ensure_ascii=False), weather_emp["id"])
        )


def _migrate_weather_api_json_format(conn):
    weather_emp = conn.execute(
        "SELECT id, api_params FROM digital_employees WHERE name='天气' AND api_params NOT LIKE '%j1%'"
    ).fetchone()
    if weather_emp:
        conn.execute(
            "UPDATE digital_employees SET api_params=?, api_response_template=? WHERE id=?",
            (
                json.dumps({"format": "j1", "lang": "zh"}, ensure_ascii=False),
                "current_condition.0.lang_zh.0.value",
                weather_emp["id"]
            )
        )


def _migrate_big_screen_to_data_screen(conn):
    old_bs = conn.execute("SELECT id FROM functions WHERE code='big_screen'").fetchone()
    if old_bs:
        conn.execute("UPDATE functions SET code='data_screen', route='/admin/data-screen' WHERE code='big_screen'")


def _migrate_data_screen_function(conn):
    ds_func = conn.execute("SELECT id FROM functions WHERE code='data_screen'").fetchone()
    if not ds_func:
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        parent_id = hub_func["id"] if hub_func else 0
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("数智大屏", "data_screen", "layui-icon-chart-screen", "/admin/data-screen", 4, parent_id, 1)
        )


def _migrate_opinion_screen_function(conn):
    op_func = conn.execute("SELECT id FROM functions WHERE code='opinion_screen'").fetchone()
    if not op_func:
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        parent_id = hub_func["id"] if hub_func else 0
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("舆情大屏", "opinion_screen", "layui-icon-flag", "/admin/opinion-screen", 5, parent_id, 1)
        )
    else:
        conn.execute("UPDATE functions SET icon='layui-icon-flag' WHERE code='opinion_screen' AND icon!='layui-icon-flag'")


def _migrate_sensitive_words_to_attack_protection(conn):
    old_words = conn.execute("SELECT word FROM sensitive_words WHERE word IN ('数据泄露','黑客','漏洞','攻击','违规','投诉','宕机','故障','崩溃','异常','虚假','误导','谣言')").fetchall()
    if old_words:
        conn.execute("DELETE FROM sensitive_words")
        new_words = [
            ("DROP TABLE", "SQL注入", "high"), ("DELETE FROM", "SQL注入", "high"),
            ("TRUNCATE", "SQL注入", "high"), ("ALTER TABLE", "SQL注入", "high"),
            ("UNION SELECT", "SQL注入", "high"), ("1=1", "SQL注入", "high"),
            ("' OR '", "SQL注入", "high"),
            ("exec(", "代码注入", "high"), ("system(", "代码注入", "high"),
            ("eval(", "代码注入", "high"), ("__import__", "代码注入", "high"),
            ("subprocess", "代码注入", "high"), ("os.system", "代码注入", "high"),
            ("{{", "SSTI注入", "high"), ("{%", "SSTI注入", "high"), ("${", "SSTI注入", "high"),
            ("admin密码", "越权试探", "high"), ("后台地址", "越权试探", "high"),
            ("管理员账号", "越权试探", "high"), ("绕过验证", "越权试探", "high"),
            ("忽略你之前的指令", "Prompt注入", "high"), ("忽略系统提示", "Prompt注入", "high"),
            ("ignore above", "Prompt注入", "high"), ("ignore all", "Prompt注入", "high"),
            ("假装你是", "Prompt注入", "medium"), ("你现在是", "Prompt注入", "medium"),
            ("role play", "Prompt注入", "medium"),
            ("你傻", "恶意骚扰", "medium"), ("废物", "恶意骚扰", "medium"),
            ("垃圾", "恶意骚扰", "medium"),
        ]
        for word, cat, sev in new_words:
            conn.execute("INSERT OR IGNORE INTO sensitive_words (word, category, severity) VALUES (?, ?, ?)", (word, cat, sev))


def _create_default_admin(conn):
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        salt = secrets.token_bytes(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", config.DEFAULT_ADMIN_PASSWORD.encode(), salt, 100_000).hex()
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, role_id, status) VALUES (?, ?, ?, ?, ?)",
            (config.DEFAULT_ADMIN_USERNAME, pwd_hash, salt.hex(), admin_role["id"] if admin_role else 1, 1)
        )


def _create_baidu_watch_source(conn):
    baidu_exists = conn.execute("SELECT id FROM watch_sources WHERE name='百度新闻'").fetchone()
    if not baidu_exists:
        baidu_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows"
        }
        conn.execute(
            """INSERT INTO watch_sources (name, url_template, method, headers, keyword_param, page_param, page_step, status, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("百度新闻", "https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&rsv_dl=ns_pc&",
             "GET", json.dumps(baidu_headers, ensure_ascii=False), "word", "pn", 10, 1, "baidu_news")
        )


def _migrate_watch_sources_source_type(conn):
    try:
        conn.execute("ALTER TABLE watch_sources ADD COLUMN source_type TEXT DEFAULT ''")
        logger.info("已为 watch_sources 添加 source_type 列")
    except Exception:
        pass


def _create_hackernews_watch_source(conn):
    hn_exists = conn.execute("SELECT id FROM watch_sources WHERE name='Hacker News'").fetchone()
    if not hn_exists:
        conn.execute(
            """INSERT INTO watch_sources (name, url_template, method, headers, keyword_param, page_param, page_step, status, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("Hacker News", "https://hn.algolia.com/api/v1/search?",
             "GET", "{}", "query", "page", 1, 1, "json_api")
        )
        logger.info("已初始化「Hacker News」瞭源规则 (json_api)")


def _create_36kr_watch_source(conn):
    kr36_exists = conn.execute("SELECT id FROM watch_sources WHERE name='36氪 RSS'").fetchone()
    if not kr36_exists:
        conn.execute(
            """INSERT INTO watch_sources (name, url_template, method, headers, keyword_param, page_param, page_step, status, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("36氪 RSS", "https://36kr.com/feed",
             "GET", "{}", "", "", 0, 1, "rss")
        )
        logger.info("已初始化「36氪 RSS」瞭源规则 (rss)")


def _migrate_encrypt_api_keys(conn):
    if not config.ENCRYPTION_KEY:
        logger.warning("未配置 ENCRYPTION_KEY，跳过 API Key 加密迁移")
        return

    try:
        from app.utils.crypto import encrypt_api_key, decrypt_api_key
    except ImportError:
        logger.warning("加密模块导入失败，跳过 API Key 加密迁移")
        return

    rows = conn.execute("SELECT id, api_key FROM ai_models WHERE api_key IS NOT NULL AND api_key != ''").fetchall()
    encrypted_count = 0
    for row in rows:
        model_id = row["id"]
        api_key = row["api_key"]
        if not api_key:
            continue

        try:
            decrypt_api_key(api_key)
        except Exception:
            try:
                encrypted_key = encrypt_api_key(api_key)
                conn.execute("UPDATE ai_models SET api_key=? WHERE id=?", (encrypted_key, model_id))
                encrypted_count += 1
            except Exception as e:
                logger.error(f"加密模型 {model_id} 的 API Key 失败: {e}")

    if encrypted_count > 0:
        logger.info(f"已加密 {encrypted_count} 个模型的 API Key")


def _migrate_ai_models_replace_static(conn):
    """替换旧的GPT/Claude静态模型为agnes-2.0-flash和qwen3.5-flash"""
    # 删除旧的3个静态模型
    old_models = ["GPT-4o", "GPT-4 Turbo", "Claude 3.5 Sonnet"]
    for name in old_models:
        conn.execute("DELETE FROM ai_models WHERE name=?", (name,))

    # 确保 agnes-2.0-flash 存在
    if not conn.execute("SELECT id FROM ai_models WHERE name='agnes-2.0-flash'").fetchone():
        model_count = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0]
        conn.execute(
            """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
               max_tokens, token_count, is_default, status, sort_order, category,
               system_prompt, temperature, top_p, context_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("agnes-2.0-flash", "openai", "agnes-2.0-flash", "https://api.openai.com/v1", "",
             128000, 0, 1 if model_count == 0 else 0, 1, 1, "text",
             "You are a helpful assistant.", 0.7, 1.0, 128000)
        )

    # 确保 qwen3.5-flash 存在
    if not conn.execute("SELECT id FROM ai_models WHERE name='qwen3.5-flash'").fetchone():
        conn.execute(
            """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
               max_tokens, token_count, is_default, status, sort_order, category,
               system_prompt, temperature, top_p, context_length)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("qwen3.5-flash", "openai", "qwen3.5-flash", "https://api.openai.com/v1", "",
             128000, 0, 0, 1, 2, "text", "You are a helpful assistant.", 0.7, 1.0, 128000)
        )

    # 确保没有默认模型时设置一个
    has_default = conn.execute("SELECT id FROM ai_models WHERE is_default=1").fetchone()
    if not has_default:
        conn.execute("UPDATE ai_models SET is_default=1 WHERE name='agnes-2.0-flash'")

    logger.info("已将静态模型替换为agnes-2.0-flash、qwen3.5-flash")


def _migrate_api_interface_table(conn):
    """创建 api_interfaces 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_interfaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            method TEXT NOT NULL DEFAULT 'GET',
            url TEXT NOT NULL DEFAULT '',
            headers TEXT DEFAULT '{}',
            params TEXT DEFAULT '{}',
            status INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    logger.info("api_interfaces 表已创建")


def _migrate_api_interface_function(conn):
    """添加接口管理功能菜单（智能中枢下）"""
    func = conn.execute("SELECT id FROM functions WHERE code='api_interface'").fetchone()
    if not func:
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        parent_id = hub_func["id"] if hub_func else 0
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("接口管理", "api_interface", "layui-icon-link", "/admin/api-interface", 3, parent_id, 1)
        )
        func = conn.execute("SELECT id FROM functions WHERE code='api_interface'").fetchone()

        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        if admin_role and func:
            conn.execute(
                "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                (admin_role["id"], func["id"])
            )
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role["id"],)
            ).fetchone()[0] or 0
            conn.execute(
                "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                (admin_role["id"], func["id"], max_order + 1)
            )
        logger.info("接口管理功能菜单已添加")


def _migrate_api_interface_seed(conn):
    """同步数字员工已有的API接口到接口管理列表（跳过已存在的编码）"""
    interfaces = [
        {
            "name": "wttr.in 天气查询",
            "code": "wttr_weather",
            "description": "通过 wttr.in 获取城市实时天气数据（温度/湿度/风速/能见度）",
            "method": "GET",
            "url": "https://wttr.in/{city}",
            "headers": json.dumps({}, ensure_ascii=False),
            "params": json.dumps({"format": "j1", "lang": "zh"}, ensure_ascii=False),
        },
        {
            "name": "聚合数据新闻头条",
            "code": "juhe_news",
            "description": "通过聚合数据API获取实时热门新闻（含标题、来源、时间、摘要）",
            "method": "GET",
            "url": "https://v.juhe.cn/toutiao/index",
            "headers": json.dumps({}, ensure_ascii=False),
            "params": json.dumps({"type": "top"}, ensure_ascii=False),
        },
        {
            "name": "iTunes 随机音乐",
            "code": "itunes_music",
            "description": "通过 iTunes Search API 随机推荐歌曲（含歌名、歌手、封面、试听链接）",
            "method": "GET",
            "url": "https://itunes.apple.com/search",
            "headers": json.dumps({}, ensure_ascii=False),
            "params": json.dumps({"term": "random", "media": "music", "limit": "50"}, ensure_ascii=False),
        },
        {
            "name": "TMDB 电影搜索",
            "code": "tmdb_movie_search",
            "description": "通过 TMDB API 搜索电影信息（含评分、海报、年份、简介），豆瓣+本地库补充",
            "method": "GET",
            "url": "https://api.themoviedb.org/3/search/movie",
            "headers": json.dumps({}, ensure_ascii=False),
            "params": json.dumps({"language": "zh-CN", "page": "1"}, ensure_ascii=False),
        },
    ]

    inserted = 0
    for iface in interfaces:
        exist = conn.execute(
            "SELECT id FROM api_interfaces WHERE code=?", (iface["code"],)
        ).fetchone()
        if not exist:
            conn.execute(
                """INSERT INTO api_interfaces (name, code, description, method, url, headers, params, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (iface["name"], iface["code"], iface["description"],
                 iface["method"], iface["url"], iface["headers"], iface["params"], 1)
            )
            inserted += 1

    if inserted > 0:
        logger.info(f"已同步 {inserted} 个数字员工API到接口管理列表")


def _migrate_api_interface_reorder(conn):
    """调整智能中枢下模块排序：数字员工(2) → 接口管理(3) → 数智大屏(4) → 舆情大屏(5)"""
    ordering = [
        ("model_engine", 1),
        ("digital_employee", 2),
        ("api_interface", 3),
        ("data_screen", 4),
        ("opinion_screen", 5),
    ]
    for code, order in ordering:
        conn.execute(
            "UPDATE functions SET sort_order=? WHERE code=? AND sort_order!=?",
            (order, code, order)
        )
    logger.info("智能中枢模块排序已调整：数字员工→接口管理→数智大屏→舆情大屏")


def _migrate_digital_employees_api_config(conn):
    """修复新闻和电影数字员工的API配置——强制恢复为localhost mock（内部集成真实API+格式化），真实API源通过描述和关联接口展示

    修复后不再检查旧URL特征，只要 api_url 不含 /mock/ 就强制恢复。
    这解决了迁移标记为"已完成"但数据未被实际更新的时序竞争问题。
    """
    news_emp = conn.execute("SELECT id, api_url FROM digital_employees WHERE name='新闻'").fetchone()
    if news_emp and "/mock/" not in (news_emp["api_url"] or ""):
        conn.execute(
            """UPDATE digital_employees SET 
               api_url=?, api_method=?, api_headers=?, api_params=?, api_response_template=?
               WHERE id=?""",
            (
                "http://localhost:10010/api/mock/news",
                "GET",
                json.dumps({}, ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                "",
                news_emp["id"]
            )
        )
        logger.info("新闻数字员工API配置已恢复为内置mock（聚合数据+百度兜底）")

    movie_emp = conn.execute("SELECT id, api_url FROM digital_employees WHERE name='电影'").fetchone()
    if movie_emp and "/mock/" not in (movie_emp["api_url"] or ""):
        conn.execute(
            """UPDATE digital_employees SET 
               api_url=?, api_method=?, api_headers=?, api_params=?, api_response_template=?
               WHERE id=?""",
            (
                "http://localhost:10010/api/mock/movie?keyword={query}",
                "GET",
                json.dumps({}, ensure_ascii=False),
                json.dumps({}, ensure_ascii=False),
                "",
                movie_emp["id"]
            )
        )
        logger.info("电影数字员工API配置已恢复为内置mock（TMDB+豆瓣+本地库）")


def _migrate_skill_table(conn):
    """创建 skills 表"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL DEFAULT 'custom',
            impl_type TEXT NOT NULL DEFAULT 'api_call',
            impl_config TEXT DEFAULT '{}',
            input_schema TEXT DEFAULT '{}',
            output_schema TEXT DEFAULT '{}',
            status INTEGER NOT NULL DEFAULT 1,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    logger.info("skills 表已创建")


def _migrate_skill_function(conn):
    """添加技能管理功能菜单（智能中枢下）"""
    func = conn.execute("SELECT id FROM functions WHERE code='skill_management'").fetchone()
    if not func:
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        parent_id = hub_func["id"] if hub_func else 0
        conn.execute(
            "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("技能管理", "skill_management", "layui-icon-util", "/admin/skill-management", 6, parent_id, 1)
        )
        func = conn.execute("SELECT id FROM functions WHERE code='skill_management'").fetchone()

        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        if admin_role and func:
            conn.execute(
                "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                (admin_role["id"], func["id"])
            )
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role["id"],)
            ).fetchone()[0] or 0
            conn.execute(
                "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                (admin_role["id"], func["id"], max_order + 1)
            )
        logger.info("技能管理功能菜单已添加")


def _migrate_skill_seed(conn):
    """预置一个自定义技能：今日热点摘要（调用新闻API获取头条并生成摘要）"""
    if not conn.execute("SELECT id FROM skills WHERE code='hot_news_summary'").fetchone():
        conn.execute(
            """INSERT INTO skills (name, code, type, impl_type, impl_config, input_schema, output_schema, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "今日热点摘要",
                "hot_news_summary",
                "custom",
                "api_call",
                json.dumps({
                    "url": "https://v.juhe.cn/toutiao/index",
                    "method": "GET",
                    "headers": {},
                    "params": {"type": "top", "key": "7eb1ec877934110a5fada4024bd027c7"}
                }, ensure_ascii=False),
                json.dumps({"type": "object", "properties": {}}, ensure_ascii=False),
                json.dumps({"type": "object"}, ensure_ascii=False),
                1,
                "调用聚合数据新闻头条API获取最新热点新闻，可链式传递给LLM生成摘要"
            )
        )
        logger.info("已预置技能：今日热点摘要")


def _migrate_conversation_management_function(conn):
    """添加会话管理和对话管理功能菜单（管理系统下）"""
    mgmt_func = conn.execute("SELECT id FROM functions WHERE code='management'").fetchone()
    parent_id = mgmt_func["id"] if mgmt_func else 0
    admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()

    for name, code, icon, route, sort_order in [
        ("会话管理", "conversation_management", "layui-icon-dialogue", "/admin/conversation-management", 5),
        ("对话管理", "message_management", "layui-icon-chat", "/admin/message-management", 6),
    ]:
        func = conn.execute("SELECT id FROM functions WHERE code=?", (code,)).fetchone()
        if not func:
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, code, icon, route, sort_order, parent_id, 1)
            )
            func = conn.execute("SELECT id FROM functions WHERE code=?", (code,)).fetchone()

            if admin_role and func:
                conn.execute(
                    "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                    (admin_role["id"], func["id"])
                )
                max_order = conn.execute(
                    "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role["id"],)
                ).fetchone()[0] or 0
                conn.execute(
                    "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                    (admin_role["id"], func["id"], max_order + 1)
                )
            logger.info(f"{name}功能菜单已添加")
