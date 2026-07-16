import os, sys
sys.stdout.reconfigure(encoding='utf-8')
import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer

from app.controllers.auth import LoginHandler, LogoutHandler, RegisterHandler, AdminLoginHandler, AdminLogoutHandler
from app.controllers.user_chat import (
    UserChatHandler,
    UserRegisterApiHandler,
    UserModelsApiHandler,
    UserDigitalEmployeesApiHandler,
    UserConversationsApiHandler,
    UserChatApiHandler
)
from app.controllers.user_export import UserExportPdfApiHandler
from app.controllers.home import (IndexHandler, AdminIndexHandler, DashboardStatsApiHandler,
    DataScreenHandler, DataScreenStatsApiHandler, DataScreenWordcloudApiHandler,
    DataScreenTrendsApiHandler, DataScreenSourceApiHandler, DataScreenSankeyApiHandler,
    OpinionScreenHandler, OpinionWarningsApiHandler, OpinionStatsApiHandler,
    OpinionAIAnalyzeApiHandler, OpinionAcknowledgeApiHandler, OpinionFeedbackApiHandler,
    OpinionScanApiHandler, SensitiveWordsApiHandler, SensitiveWordsCreateApiHandler,
    SensitiveWordsUpdateApiHandler, SensitiveWordsDeleteApiHandler)
from app.controllers.admin_user import (
    UserManagementHandler,
    UserListApiHandler,
    UserGetApiHandler,
    UserCreateApiHandler,
    UserUpdateApiHandler,
    UserDeleteApiHandler
)
from app.controllers.admin_role import (
    RoleManagementHandler,
    RoleListApiHandler,
    RoleGetApiHandler,
    RoleCreateApiHandler,
    RoleUpdateApiHandler,
    RoleDeleteApiHandler,
    RoleFunctionsApiHandler,
    RoleFunctionsSaveApiHandler
)
from app.controllers.admin_function import (
    FunctionManagementHandler,
    FunctionListApiHandler,
    FunctionGetApiHandler,
    FunctionCreateApiHandler,
    FunctionUpdateApiHandler,
    FunctionDeleteApiHandler,
    FunctionToggleApiHandler
)
from app.controllers.admin_menu import (
    MenuManagementHandler,
    MenuListApiHandler,
    MenuCreateApiHandler,
    MenuUpdateApiHandler,
    MenuDeleteApiHandler,
    MenuPreviewApiHandler
)
from app.controllers.admin_profile import (
    ProfileApiHandler,
    ChangePasswordApiHandler
)
from app.controllers.admin_source import (
    SourceManagementHandler,
    SourceListApiHandler,
    SourceGetApiHandler,
    SourceCreateApiHandler,
    SourceUpdateApiHandler,
    SourceDeleteApiHandler,
    SourceActiveListApiHandler
)
from app.controllers.admin_watch import (
    WatchManagementHandler,
    WatchCollectApiHandler,
    WatchCollectedDataApiHandler,
    WatchSaveToWarehouseApiHandler
)
from app.controllers.admin_warehouse import (
    WarehouseManagementHandler,
    WarehouseListApiHandler,
    WarehouseGetApiHandler,
    WarehouseDeleteApiHandler,
    WarehouseBatchDeleteApiHandler,
    WarehouseBatchDeepCollectApiHandler,
    DeepCollectTaskApiHandler,
    DeepCollectResultApiHandler,
    DeepCollectStartSingleApiHandler
)
from app.controllers.admin_model import (
    ModelEngineHandler,
    ModelListApiHandler,
    ModelCategoriesApiHandler,
    ModelGetApiHandler,
    ModelCreateApiHandler,
    ModelUpdateApiHandler,
    ModelDeleteApiHandler,
    ModelSetDefaultApiHandler,
    ModelGetDefaultApiHandler,
    ModelChatApiHandler
)
from app.controllers.admin_digital_employee import (
    DigitalEmployeeManagementHandler,
    DigitalEmployeeListApiHandler,
    DigitalEmployeeGetApiHandler,
    DigitalEmployeeCreateApiHandler,
    DigitalEmployeeUpdateApiHandler,
    DigitalEmployeeDeleteApiHandler,
    DigitalEmployeeUploadMdHandler,
    DigitalEmployeeListMdHandler,
    DigitalEmployeeModelsApiHandler,
    DigitalEmployeeTestApiHandler
)
from app.models.db import init_db
from app.models.role import RoleRepository
from app.models.function import FunctionRepository
from app.models.menu import MenuRepository
from app.models.watch_source import WatchSourceRepository

def webapp():
    # 定义一个web应用程序，并配置访问各个模块/页面路由
    # 整个程序的安全配置也需要在此处完成
    base_dir = os.path.dirname(os.path.abspath(__file__))
    settings = dict(
        template_path=os.path.join(base_dir, "app", "templates"),
        static_path=os.path.join(base_dir, "app", "static"),
        cookie_secret=os.environ.get("COOKIE_SECRET", "datafinderagentos-token"),
        login_url="/",
        xsrf_cookies=True,
        debug=True,
        autoreload=True
    )
    return tornado.web.Application([
        # 前台路由
        (r"/", LoginHandler),
        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/chat", UserChatHandler),
        (r"/logout", LogoutHandler),
        (r"/index", IndexHandler),
        # 后台路由
        (r"/admin/", AdminLoginHandler),
        (r"/admin/login", AdminLoginHandler),
        (r"/admin/logout", AdminLogoutHandler),
        (r"/admin/index", AdminIndexHandler),
        # 控制台统计数据API（实时刷新用）
        (r"/api/dashboard/stats", DashboardStatsApiHandler),
        # 数智大屏
        (r"/admin/data-screen", DataScreenHandler),
        (r"/api/data-screen/stats", DataScreenStatsApiHandler),
        (r"/api/data-screen/wordcloud", DataScreenWordcloudApiHandler),
        (r"/api/data-screen/trends", DataScreenTrendsApiHandler),
        (r"/api/data-screen/source", DataScreenSourceApiHandler),
        (r"/api/data-screen/sankey", DataScreenSankeyApiHandler),
        # 舆情大屏
        (r"/admin/opinion-screen", OpinionScreenHandler),
        (r"/api/opinion/stats", OpinionStatsApiHandler),
        (r"/api/opinion/warnings", OpinionWarningsApiHandler),
        (r"/api/opinion/ai-analyze", OpinionAIAnalyzeApiHandler),
        (r"/api/opinion/acknowledge", OpinionAcknowledgeApiHandler),
        (r"/api/opinion/feedback", OpinionFeedbackApiHandler),
        (r"/api/opinion/scan", OpinionScanApiHandler),
        (r"/api/opinion/sensitive-words", SensitiveWordsApiHandler),
        (r"/api/opinion/sensitive-words/create", SensitiveWordsCreateApiHandler),
        (r"/api/opinion/sensitive-words/update", SensitiveWordsUpdateApiHandler),
        (r"/api/opinion/sensitive-words/delete", SensitiveWordsDeleteApiHandler),
        # 用户管理
        (r"/admin/user-management", UserManagementHandler),
        (r"/api/users/list", UserListApiHandler),
        (r"/api/users/get", UserGetApiHandler),
        (r"/api/users/create", UserCreateApiHandler),
        (r"/api/users/update", UserUpdateApiHandler),
        (r"/api/users/delete", UserDeleteApiHandler),
        # 角色管理
        (r"/admin/role-management", RoleManagementHandler),
        (r"/api/roles/list", RoleListApiHandler),
        (r"/api/roles/get", RoleGetApiHandler),
        (r"/api/roles/create", RoleCreateApiHandler),
        (r"/api/roles/update", RoleUpdateApiHandler),
        (r"/api/roles/delete", RoleDeleteApiHandler),
        (r"/api/roles/functions", RoleFunctionsApiHandler),
        (r"/api/roles/functions/save", RoleFunctionsSaveApiHandler),
        # 功能管理
        (r"/admin/function-management", FunctionManagementHandler),
        (r"/api/functions/list", FunctionListApiHandler),
        (r"/api/functions/get", FunctionGetApiHandler),
        (r"/api/functions/create", FunctionCreateApiHandler),
        (r"/api/functions/update", FunctionUpdateApiHandler),
        (r"/api/functions/delete", FunctionDeleteApiHandler),
        (r"/api/functions/toggle", FunctionToggleApiHandler),
        # 菜单管理
        (r"/admin/menu-management", MenuManagementHandler),
        (r"/api/menus/list", MenuListApiHandler),
        (r"/api/menus/create", MenuCreateApiHandler),
        (r"/api/menus/update", MenuUpdateApiHandler),
        (r"/api/menus/delete", MenuDeleteApiHandler),
        (r"/api/menus/preview", MenuPreviewApiHandler),
        # 个人信息 / 修改密码
        (r"/api/profile", ProfileApiHandler),
        (r"/api/profile/change-password", ChangePasswordApiHandler),
        # 瞭源管理
        (r"/admin/source-management", SourceManagementHandler),
        (r"/api/sources/list", SourceListApiHandler),
        (r"/api/sources/get", SourceGetApiHandler),
        (r"/api/sources/create", SourceCreateApiHandler),
        (r"/api/sources/update", SourceUpdateApiHandler),
        (r"/api/sources/delete", SourceDeleteApiHandler),
        (r"/api/sources/active", SourceActiveListApiHandler),
        # 瞭望管理
        (r"/admin/watch-management", WatchManagementHandler),
        (r"/api/watch/collect", WatchCollectApiHandler),
        (r"/api/watch/data", WatchCollectedDataApiHandler),
        # 瞭望采集 - 数据保存到数据仓库
        (r"/api/watch/save-to-warehouse", WatchSaveToWarehouseApiHandler),
        
        # 数据仓库
        (r"/admin/warehouse-management", WarehouseManagementHandler),
        (r"/api/warehouse/list", WarehouseListApiHandler),
        (r"/api/warehouse/get", WarehouseGetApiHandler),
        (r"/api/warehouse/delete", WarehouseDeleteApiHandler),
        (r"/api/warehouse/batch-delete", WarehouseBatchDeleteApiHandler),
        (r"/api/warehouse/batch-deep-collect", WarehouseBatchDeepCollectApiHandler),
        # 深度采集
        (r"/api/deep-collect/start", DeepCollectStartSingleApiHandler),
        (r"/api/deep-collect/task", DeepCollectTaskApiHandler),
        (r"/api/deep-collect/result", DeepCollectResultApiHandler),
        
        # 模型引擎
        (r"/admin/model-engine", ModelEngineHandler),
        (r"/api/models/list", ModelListApiHandler),
        (r"/api/models/categories", ModelCategoriesApiHandler),
        (r"/api/models/get", ModelGetApiHandler),
        (r"/api/models/create", ModelCreateApiHandler),
        (r"/api/models/update", ModelUpdateApiHandler),
        (r"/api/models/delete", ModelDeleteApiHandler),
        (r"/api/models/set-default", ModelSetDefaultApiHandler),
        (r"/api/models/get-default", ModelGetDefaultApiHandler),
        (r"/api/models/chat", ModelChatApiHandler),
        
        # 数字员工
        (r"/admin/digital-employee", DigitalEmployeeManagementHandler),
        (r"/admin/digital-employee-management", DigitalEmployeeManagementHandler),
        (r"/api/digital-employees/list", DigitalEmployeeListApiHandler),
        (r"/api/digital-employees/get", DigitalEmployeeGetApiHandler),
        (r"/api/digital-employees/create", DigitalEmployeeCreateApiHandler),
        (r"/api/digital-employees/update", DigitalEmployeeUpdateApiHandler),
        (r"/api/digital-employees/delete", DigitalEmployeeDeleteApiHandler),
        (r"/api/digital-employees/upload-md", DigitalEmployeeUploadMdHandler),
        (r"/api/digital-employees/list-md", DigitalEmployeeListMdHandler),
        (r"/api/digital-employees/models", DigitalEmployeeModelsApiHandler),
        (r"/api/digital-employees/test", DigitalEmployeeTestApiHandler),
        
        # 用户侧-前台API
        (r"/api/user/register", UserRegisterApiHandler),
        (r"/api/user/models", UserModelsApiHandler),
        (r"/api/user/digital-employees", UserDigitalEmployeesApiHandler),
        (r"/api/user/conversations", UserConversationsApiHandler),
        (r"/api/user/chat", UserChatApiHandler),
        (r"/api/user/export/pdf", UserExportPdfApiHandler),
    ],
    **settings
    )

if __name__ == '__main__':
    init_db()
    # 初始化默认数据（角色、功能、菜单、角色-功能关联、默认用户）
    try:
        from app.models.db import get_connection
        import hashlib, secrets, json
        conn = get_connection()
        admin_role = conn.execute("SELECT id FROM roles WHERE code='admin'").fetchone()
        if admin_role:
            admin_role_id = admin_role["id"]
            
            # === 瞭望中心子系统 ===
            # 1. 创建顶级功能「瞭望中心」（如果不存在）
            watch_center = conn.execute("SELECT id FROM functions WHERE code='watch_center'").fetchone()
            if not watch_center:
                conn.execute(
                    "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("瞭望中心", "watch_center", "layui-icon-engine", "", 3, 0, 1)
                )
                watch_center_id = conn.execute("SELECT id FROM functions WHERE code='watch_center'").fetchone()["id"]
                print("✓ 已创建「瞭望中心」子系统")
            else:
                watch_center_id = watch_center["id"]

            # 2. 创建/迁移瞭源管理到瞭望中心下
            source_func = conn.execute("SELECT id, parent_id FROM functions WHERE code='source_management'").fetchone()
            if source_func:
                # 如果父级是管理系统（非瞭望中心），则迁移
                old_parent = source_func["parent_id"]
                if old_parent != watch_center_id:
                    conn.execute("UPDATE functions SET parent_id=?, sort_order=1 WHERE id=?", (watch_center_id, source_func["id"]))
                    print("✓ 已迁移「瞭源管理」到瞭望中心子系统")
            else:
                conn.execute(
                    "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("瞭源管理", "source_management", "layui-icon-website", "/admin/source-management", 1, watch_center_id, 1)
                )
                print("✓ 已添加「瞭源管理」功能")

            # 3. 创建/迁移瞭望采集（原瞭望管理）到瞭望中心下
            watch_func = conn.execute("SELECT id, parent_id, name FROM functions WHERE code='watch_management'").fetchone()
            if watch_func:
                # 重命名：瞭望管理 → 瞭望采集
                if watch_func["name"] == "瞭望管理":
                    conn.execute("UPDATE functions SET name='瞭望采集' WHERE id=?", (watch_func["id"],))
                    print("✓ 已重命名「瞭望管理」→「瞭望采集」")
                # 如果父级不是瞭望中心，则迁移
                old_parent = watch_func["parent_id"]
                if old_parent != watch_center_id:
                    conn.execute("UPDATE functions SET parent_id=?, sort_order=2 WHERE id=?", (watch_center_id, watch_func["id"]))
                    print("✓ 已迁移「瞭望采集」到瞭望中心子系统")
            else:
                conn.execute(
                    "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("瞭望采集", "watch_management", "layui-icon-util", "/admin/watch-management", 2, watch_center_id, 1)
                )
                print("✓ 已添加「瞭望采集」功能")

            # 4. 从系统管理菜单中移除瞭源管理和瞭望采集（如果有旧的菜单关联）
            mgmt_id_row = conn.execute("SELECT id FROM functions WHERE code='management'").fetchone()
            if mgmt_id_row:
                mgmt_id = mgmt_id_row["id"]
                # 将这些功能的父级从 management 改为 watch_center（处理初始创建时错误的场景）
                conn.execute("UPDATE functions SET parent_id=? WHERE code='source_management' AND parent_id=?", (watch_center_id, mgmt_id))
                conn.execute("UPDATE functions SET parent_id=? WHERE code='watch_management' AND parent_id=?", (watch_center_id, mgmt_id))
                conn.execute("UPDATE functions SET name='瞭望采集' WHERE code='watch_management' AND name='瞭望管理'")
            
            # 5. 添加数据仓库功能到瞭望中心下（如果不存在）
            warehouse_func = conn.execute("SELECT id FROM functions WHERE code='data_warehouse'").fetchone()
            if not warehouse_func:
                conn.execute(
                    "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("数据仓库", "data_warehouse", "layui-icon-template", "/admin/warehouse-management", 3, watch_center_id, 1)
                )
                print("✓ 已添加「数据仓库」功能到瞭望中心")
            
            # 迁移：统一模型引擎图标
            cur = conn.execute("UPDATE functions SET icon='layui-icon-senior' WHERE code='model_engine' AND icon!='layui-icon-senior'")
            if cur.rowcount > 0:
                print("✓ 已更新「模型引擎」图标")
            
            # 迁移：统一智能中枢图标（与瞭望中心区分）
            cur = conn.execute("UPDATE functions SET icon='layui-icon-bot' WHERE code='intelligent_hub' AND icon!='layui-icon-bot'")
            if cur.rowcount > 0:
                print("✓ 已更新「智能中枢」图标")
            
            # 迁移：回填数据仓库中为空的关键词（从瞭望采集数据按标题匹配）
            cur = conn.execute("""
                UPDATE data_warehouse SET keyword = (
                    SELECT w.keyword FROM watch_collected_data w
                    WHERE w.title = data_warehouse.title AND w.keyword != '' AND w.keyword IS NOT NULL
                        AND (data_warehouse.keyword = '' OR data_warehouse.keyword IS NULL)
                    LIMIT 1
                )
                WHERE (keyword = '' OR keyword IS NULL)
            """)
            if cur.rowcount > 0:
                print(f"✓ 已回填 {cur.rowcount} 条数据仓库关键词")
            
            funcs = conn.execute("SELECT id FROM functions ORDER BY sort_order").fetchall()
            # 为系统管理员分配所有功能（role_functions）
            rf_count = conn.execute("SELECT COUNT(*) FROM role_functions WHERE role_id=?", (admin_role_id,)).fetchone()[0]
            if rf_count == 0:
                for func in funcs:
                    conn.execute(
                        "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                        (admin_role_id, func["id"])
                    )
                print(f"✓ 已为系统管理员分配 {len(funcs)} 个功能")
            # 检查并插入默认菜单（系统管理员关联所有功能）
            menu_count = conn.execute("SELECT COUNT(*) FROM menus").fetchone()[0]
            if menu_count == 0:
                for i, func in enumerate(funcs):
                    conn.execute(
                        "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                        (admin_role_id, func["id"], i + 1)
                    )
                print(f"✓ 已为系统管理员创建 {len(funcs)} 个默认菜单")
            
            # 确保数据仓库功能已分配角色和菜单（即使非首次启动）
            warehouse_func = conn.execute("SELECT id FROM functions WHERE code='data_warehouse'").fetchone()
            if warehouse_func:
                conn.execute(
                    "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                    (admin_role_id, warehouse_func["id"])
                )
                menu_exists = conn.execute(
                    "SELECT id FROM menus WHERE role_id=? AND func_id=?",
                    (admin_role_id, warehouse_func["id"])
                ).fetchone()
                if not menu_exists:
                    max_order = conn.execute(
                        "SELECT MAX(sort_order) FROM menus WHERE role_id=?", (admin_role_id,)
                    ).fetchone()[0] or 0
                    conn.execute(
                        "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                        (admin_role_id, warehouse_func["id"], max_order + 1)
                    )
        # 创建默认 admin 用户（如果不存在）
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            salt = secrets.token_bytes(16)
            pwd_hash = hashlib.pbkdf2_hmac("sha256", b"123456", salt, 100_000).hex()
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role_id, status) VALUES (?, ?, ?, ?, ?)",
                ("admin", pwd_hash, salt.hex(), admin_role["id"] if admin_role else 1, 1)
            )
            print("✓ 已创建默认管理员用户（admin / 123456）")
        
        # 初始化百度新闻瞭源规则（如果不存在）
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
            print("✓ 已初始化「百度新闻」瞭源规则 (baidu_news)")

        # 初始化 Hacker News JSON API 瞭源（如果不存在）
        hn_exists = conn.execute("SELECT id FROM watch_sources WHERE name='Hacker News'").fetchone()
        if not hn_exists:
            conn.execute(
                """INSERT INTO watch_sources (name, url_template, method, headers, keyword_param, page_param, page_step, status, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("Hacker News", "https://hn.algolia.com/api/v1/search?",
                 "GET", "{}", "query", "page", 1, 1, "json_api")
            )
            print("✓ 已初始化「Hacker News」瞭源规则 (json_api)")

        # 初始化 36氪 RSS 瞭源（如果不存在）
        kr36_exists = conn.execute("SELECT id FROM watch_sources WHERE name='36氪 RSS'").fetchone()
        if not kr36_exists:
            conn.execute(
                """INSERT INTO watch_sources (name, url_template, method, headers, keyword_param, page_param, page_step, status, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("36氪 RSS", "https://36kr.com/feed",
                 "GET", "{}", "", "", 0, 1, "rss")
            )
            print("✓ 已初始化「36氪 RSS」瞭源规则 (rss)")

        # 初始化模型引擎功能（如果不存在）
        me_func = conn.execute("SELECT id FROM functions WHERE code='model_engine'").fetchone()
        if not me_func:
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("模型引擎", "model_engine", "layui-icon-senior", "/admin/model-engine", 4, 0, 1)
            )
            print("✓ 已创建「模型引擎」功能")
            me_func = conn.execute("SELECT id FROM functions WHERE code='model_engine'").fetchone()
            # 为admin角色重新分配所有功能
            if admin_role and me_func:
                conn.execute(
                    "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                    (admin_role["id"], me_func["id"])
                )
                conn.execute(
                    "INSERT INTO menus (role_id, func_id, sort_order) VALUES (?, ?, ?)",
                    (admin_role["id"], me_func["id"], 20)
                )
        
        # 初始化示例AI模型（如果模型表为空）
        model_count = conn.execute("SELECT COUNT(*) FROM ai_models").fetchone()[0]
        if model_count == 0:
            conn.execute(
                """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
                   max_tokens, token_count, is_default, status, sort_order, category,
                   system_prompt, temperature, top_p, context_length)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("GPT-4o", "openai", "gpt-4o", "https://api.openai.com/v1", "sk-your-key-here",
                 128000, 0, 1, 1, 1, "text", "You are a helpful assistant.", 0.7, 1.0, 128000)
            )
            conn.execute(
                """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
                   max_tokens, token_count, is_default, status, sort_order, category,
                   system_prompt, temperature, top_p, context_length)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("GPT-4 Turbo", "openai", "gpt-4-turbo", "https://api.openai.com/v1", "sk-your-key-here",
                 128000, 0, 0, 1, 2, "text", "You are a helpful assistant.", 0.7, 1.0, 128000)
            )
            conn.execute(
                """INSERT INTO ai_models (name, provider, model_name, api_base_url, api_key,
                   max_tokens, token_count, is_default, status, sort_order, category,
                   system_prompt, temperature, top_p, context_length)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("Claude 3.5 Sonnet", "anthropic", "claude-3-5-sonnet-latest", "https://api.anthropic.com/v1", "sk-ant-your-key-here",
                 200000, 0, 0, 1, 3, "text", "You are a helpful assistant.", 0.7, 1.0, 200000)
            )
            print("✓ 已初始化 3 个示例AI模型（GPT-4o为默认模型）")
        
        # 初始化智能中枢功能（如果不存在）
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        if not hub_func:
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("智能中枢", "intelligent_hub", "layui-icon-bot", "", 4, 0, 1)
            )
            print("✓ 已创建「智能中枢」功能")
            hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
            # 为admin角色分配智能中枢
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
        
        # 将模型引擎和数字员工设为智能中枢的子功能
        hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
        if hub_func:
            conn.execute(
                "UPDATE functions SET parent_id=?, sort_order=1 WHERE code='model_engine' AND parent_id=0",
                (hub_func["id"],)
            )
            conn.execute(
                "UPDATE functions SET parent_id=?, sort_order=2 WHERE code='digital_employee' AND parent_id=0",
                (hub_func["id"],)
            )
        
        # 确保数字员工功能存在（兼容旧版）
        de_func = conn.execute("SELECT id FROM functions WHERE code='digital_employee'").fetchone()
        if not de_func:
            hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
            parent_id = hub_func["id"] if hub_func else 0
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("数字员工", "digital_employee", "layui-icon-user", "/admin/digital-employee", 2, parent_id, 1)
            )
            print("✓ 已创建「数字员工」功能")
            de_func = conn.execute("SELECT id FROM functions WHERE code='digital_employee'").fetchone()
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
        
        # 创建示例数字员工（如果表为空）
        de_count = conn.execute("SELECT COUNT(*) FROM digital_employees").fetchone()[0]
        if de_count == 0:
            # 获取默认模型ID
            default_model = conn.execute("SELECT id FROM ai_models WHERE is_default=1 LIMIT 1").fetchone()
            model_id = default_model["id"] if default_model else None

            # 采集专员（LLM型）
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
            print("✓ 已创建示例数字员工：采集专员")

            # 天气（API型）
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
            print("✓ 已创建示例数字员工：天气")

        # 迁移：更新已有天气数字员工的API配置（OpenWeatherMap → wttr.in）
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
            print("✓ 已迁移天气数字员工API配置（OpenWeatherMap → wttr.in）")

        # 二次迁移：修复已迁移但URL不含{city}占位符的天气员工
        weather_emp2 = conn.execute("SELECT id, api_url FROM digital_employees WHERE name='天气' AND api_url='https://wttr.in'").fetchone()
        if weather_emp2:
            conn.execute(
                "UPDATE digital_employees SET api_url=?, api_params=?, api_headers=? WHERE id=?",
                ("https://wttr.in/{city}",
                 json.dumps({"format": "%C+%t+%h+%w", "lang": "zh"}, ensure_ascii=False),
                 json.dumps({}, ensure_ascii=False),
                 weather_emp2["id"])
            )
            print("✓ 已修复天气员工URL格式（添加{city}占位符）")

        # 三次迁移：修复天气员工Mozilla User-Agent导致返回HTML的问题
        weather_emp3 = conn.execute("SELECT id, api_headers FROM digital_employees WHERE name='天气' AND api_headers LIKE '%Mozilla%'").fetchone()
        if weather_emp3:
            conn.execute(
                "UPDATE digital_employees SET api_headers=? WHERE id=?",
                (json.dumps({}, ensure_ascii=False), weather_emp3["id"])
            )
            print("✓ 已修复天气员工User-Agent头（避免wttr.in返回HTML）")

        # 四次迁移：天气员工改用JSON格式(format=j1)以支持中文输出
        weather_emp4 = conn.execute(
            "SELECT id, api_params FROM digital_employees WHERE name='天气' AND api_params NOT LIKE '%j1%'"
        ).fetchone()
        if weather_emp4:
            conn.execute(
                "UPDATE digital_employees SET api_params=?, api_response_template=? WHERE id=?",
                (
                    json.dumps({"format": "j1", "lang": "zh"}, ensure_ascii=False),
                    "current_condition.0.lang_zh.0.value",
                    weather_emp4["id"]
                )
            )
            print("✓ 已迁移天气员工参数（format=%C... → format=j1，支持中文输出）")

        # ============================================================
        # 迁移旧版 big_screen → data_screen（兼容已有数据库）
        # ============================================================
        old_bs = conn.execute("SELECT id FROM functions WHERE code='big_screen'").fetchone()
        if old_bs:
            conn.execute("UPDATE functions SET code='data_screen', route='/admin/data-screen' WHERE code='big_screen'")
            print("✓ 已迁移旧版 big_screen → data_screen")

        # ============================================================
        # 创建数智大屏功能（如果不存在）
        # ============================================================
        ds_func = conn.execute("SELECT id FROM functions WHERE code='data_screen'").fetchone()
        if not ds_func:
            hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
            parent_id = hub_func["id"] if hub_func else 0
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("数智大屏", "data_screen", "layui-icon-chart-screen", "/admin/data-screen", 3, parent_id, 1)
            )
            print("✓ 已创建「数智大屏」功能")

        # ============================================================
        # 创建舆情大屏功能（如果不存在）
        # ============================================================
        op_func = conn.execute("SELECT id FROM functions WHERE code='opinion_screen'").fetchone()
        if not op_func:
            hub_func = conn.execute("SELECT id FROM functions WHERE code='intelligent_hub'").fetchone()
            parent_id = hub_func["id"] if hub_func else 0
            conn.execute(
                "INSERT INTO functions (name, code, icon, route, sort_order, parent_id, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("舆情大屏", "opinion_screen", "layui-icon-flag", "/admin/opinion-screen", 4, parent_id, 1)
            )
            print("✓ 已创建「舆情大屏」功能")
        else:
            # 保证已有数据的图标正确
            conn.execute("UPDATE functions SET icon='layui-icon-flag' WHERE code='opinion_screen' AND icon!='layui-icon-flag'")

        # ============================================================
        # 迁移旧版敏感词 → 攻击防护词库
        # ============================================================
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
            print("✓ 已迁移敏感词库为攻击防护词库（共 {} 个）".format(len(new_words)))

        # ============================================================
        # 通用保障：确保所有已启用的功能都已分配给admin角色并创建菜单
        # 这解决了增量部署时新功能缺少菜单的问题
        # ============================================================
        all_funcs = conn.execute("SELECT id, name FROM functions WHERE status=1 ORDER BY sort_order, id").fetchall()
        if admin_role:
            for func in all_funcs:
                # 确保角色-功能关联存在
                conn.execute(
                    "INSERT OR IGNORE INTO role_functions (role_id, func_id) VALUES (?, ?)",
                    (admin_role_id, func["id"])
                )
                # 确保菜单存在
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
            print(f"✓ 已完成所有功能的菜单保障检查 (共 {len(all_funcs)} 个功能)")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠ 初始化默认数据出错: {e}")
    
    webapp = webapp()
    # 将应用程序部署到服务器
    server = HTTPServer(webapp)
    server.listen(10010)
    print("Server Started:http://localhost:10010/", flush=True)
    tornado.ioloop.IOLoop.current().start()
