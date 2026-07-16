import os, sys
sys.stdout.reconfigure(encoding='utf-8')
import tornado.ioloop
import tornado.web
from tornado.httpserver import HTTPServer

from app.config import config
from app.controllers.auth import LoginHandler, LogoutHandler, RegisterHandler, AdminLoginHandler, AdminLogoutHandler
from app.controllers.user_chat import (
    UserChatHandler,
    UserRegisterApiHandler,
    UserModelsApiHandler,
    UserDigitalEmployeesApiHandler,
    UserConversationsApiHandler,
    UserChatApiHandler
)
from app.controllers.mock_apis import (
    MockNewsHandler,
    MockMusicHandler,
    MockMovieHandler,
    MockWeatherHandler
)
from app.controllers.multimodal import ImageGenHandler, VideoGenHandler
from app.controllers.user_export import UserExportPdfApiHandler
from app.controllers.home import (IndexHandler, GestureHandler, AdminIndexHandler, DashboardStatsApiHandler,
    DataScreenHandler, DataScreenStatsApiHandler, DataScreenWordcloudApiHandler,
    DataScreenTrendsApiHandler, DataScreenSourceApiHandler, DataScreenSankeyApiHandler,
    OpinionScreenHandler, OpinionWarningsApiHandler, OpinionStatsApiHandler,
    OpinionAIAnalyzeApiHandler, OpinionAcknowledgeApiHandler, OpinionFeedbackApiHandler,
    OpinionScanApiHandler, OpinionBatchReviewApiHandler, SensitiveWordsApiHandler, SensitiveWordsCreateApiHandler,
    SensitiveWordsUpdateApiHandler, SensitiveWordsDeleteApiHandler)
from app.controllers.auth import FaceLoginHandler
from app.controllers.admin_user import (
    UserManagementHandler,
    UserListApiHandler,
    UserGetApiHandler,
    UserCreateApiHandler,
    UserUpdateApiHandler,
    UserDeleteApiHandler
)
from app.controllers.admin_conversation import (
    ConversationManagementHandler,
    MessageManagementHandler,
    ConversationListApiHandler,
    ConversationMessagesApiHandler,
    ConversationDeleteApiHandler,
    ConversationDeleteMessageApiHandler,
    ConversationMessagesAllApiHandler
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
from app.controllers.admin_api_interface import (
    ApiInterfaceManagementHandler,
    ApiInterfaceListApiHandler,
    ApiInterfaceGetApiHandler,
    ApiInterfaceEnabledListApiHandler,
    ApiInterfaceCreateApiHandler,
    ApiInterfaceUpdateApiHandler,
    ApiInterfaceDeleteApiHandler,
    ApiInterfaceToggleApiHandler
)
from app.controllers.admin_skill import (
    SkillManagementHandler,
    SkillListApiHandler,
    SkillGetApiHandler,
    SkillEnabledListApiHandler,
    SkillCreateApiHandler,
    SkillUpdateApiHandler,
    SkillDeleteApiHandler,
    SkillToggleApiHandler
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
    DigitalEmployeeSkillsApiHandler,
    DigitalEmployeeTestApiHandler
)
from app.models.db import init_db, run_runtime_checks
from app.models.migrations import run_migrations
from app.utils.logger import logger


def webapp():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    settings = dict(
        template_path=os.path.join(base_dir, "app", "templates"),
        static_path=os.path.join(base_dir, "app", "static"),
cookie_secret=config.COOKIE_SECRET,
        login_url="/",
        xsrf_cookies=True,
        debug=config.DEBUG,
        autoreload=config.AUTORELOAD,
    )
    return tornado.web.Application([
        (r"/favicon.ico", tornado.web.StaticFileHandler, {"path": os.path.join(base_dir, "app", "static", "favicon.ico")}),
        (r"/", LoginHandler),
        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/chat", UserChatHandler),
        (r"/logout", LogoutHandler),
        (r"/index", IndexHandler),
        (r"/gesture", GestureHandler),
        (r"/face-login", FaceLoginHandler),
        (r"/admin/", AdminLoginHandler),
        (r"/admin/login", AdminLoginHandler),
        (r"/admin/logout", AdminLogoutHandler),
        (r"/admin/index", AdminIndexHandler),
        (r"/api/dashboard/stats", DashboardStatsApiHandler),
        (r"/admin/data-screen", DataScreenHandler),
        (r"/api/data-screen/stats", DataScreenStatsApiHandler),
        (r"/api/data-screen/wordcloud", DataScreenWordcloudApiHandler),
        (r"/api/data-screen/trends", DataScreenTrendsApiHandler),
        (r"/api/data-screen/source", DataScreenSourceApiHandler),
        (r"/api/data-screen/sankey", DataScreenSankeyApiHandler),
        (r"/admin/opinion-screen", OpinionScreenHandler),
        (r"/api/opinion/stats", OpinionStatsApiHandler),
        (r"/api/opinion/warnings", OpinionWarningsApiHandler),
        (r"/api/opinion/ai-analyze", OpinionAIAnalyzeApiHandler),
        (r"/api/opinion/acknowledge", OpinionAcknowledgeApiHandler),
        (r"/api/opinion/feedback", OpinionFeedbackApiHandler),
        (r"/api/opinion/scan", OpinionScanApiHandler),
        (r"/api/opinion/batch-review", OpinionBatchReviewApiHandler),
        (r"/api/opinion/sensitive-words", SensitiveWordsApiHandler),
        (r"/api/opinion/sensitive-words/create", SensitiveWordsCreateApiHandler),
        (r"/api/opinion/sensitive-words/update", SensitiveWordsUpdateApiHandler),
        (r"/api/opinion/sensitive-words/delete", SensitiveWordsDeleteApiHandler),
        (r"/admin/user-management", UserManagementHandler),
        (r"/api/users/list", UserListApiHandler),
        (r"/api/users/get", UserGetApiHandler),
        (r"/api/users/create", UserCreateApiHandler),
        (r"/api/users/update", UserUpdateApiHandler),
        (r"/api/users/delete", UserDeleteApiHandler),
        # 会话管理 & 对话管理
        (r"/admin/conversation-management", ConversationManagementHandler),
        (r"/admin/message-management", MessageManagementHandler),
        (r"/api/admin/conversations/list", ConversationListApiHandler),
        (r"/api/admin/conversations/messages", ConversationMessagesApiHandler),
        (r"/api/admin/conversations/delete", ConversationDeleteApiHandler),
        (r"/api/admin/conversations/messages/delete", ConversationDeleteMessageApiHandler),
        (r"/api/admin/conversations/messages-all", ConversationMessagesAllApiHandler),
        # 角色管理
        (r"/admin/role-management", RoleManagementHandler),
        (r"/api/roles/list", RoleListApiHandler),
        (r"/api/roles/get", RoleGetApiHandler),
        (r"/api/roles/create", RoleCreateApiHandler),
        (r"/api/roles/update", RoleUpdateApiHandler),
        (r"/api/roles/delete", RoleDeleteApiHandler),
        (r"/api/roles/functions", RoleFunctionsApiHandler),
        (r"/api/roles/functions/save", RoleFunctionsSaveApiHandler),
        (r"/admin/function-management", FunctionManagementHandler),
        (r"/api/functions/list", FunctionListApiHandler),
        (r"/api/functions/get", FunctionGetApiHandler),
        (r"/api/functions/create", FunctionCreateApiHandler),
        (r"/api/functions/update", FunctionUpdateApiHandler),
        (r"/api/functions/delete", FunctionDeleteApiHandler),
        (r"/api/functions/toggle", FunctionToggleApiHandler),
        (r"/admin/menu-management", MenuManagementHandler),
        (r"/api/menus/list", MenuListApiHandler),
        (r"/api/menus/create", MenuCreateApiHandler),
        (r"/api/menus/update", MenuUpdateApiHandler),
        (r"/api/menus/delete", MenuDeleteApiHandler),
        (r"/api/menus/preview", MenuPreviewApiHandler),
        (r"/api/profile", ProfileApiHandler),
        (r"/api/profile/change-password", ChangePasswordApiHandler),
        (r"/admin/source-management", SourceManagementHandler),
        (r"/api/sources/list", SourceListApiHandler),
        (r"/api/sources/get", SourceGetApiHandler),
        (r"/api/sources/create", SourceCreateApiHandler),
        (r"/api/sources/update", SourceUpdateApiHandler),
        (r"/api/sources/delete", SourceDeleteApiHandler),
        (r"/api/sources/active", SourceActiveListApiHandler),
        (r"/admin/api-interface", ApiInterfaceManagementHandler),
        (r"/api/api-interfaces/list", ApiInterfaceListApiHandler),
        (r"/api/api-interfaces/get", ApiInterfaceGetApiHandler),
        (r"/api/api-interfaces/enabled", ApiInterfaceEnabledListApiHandler),
        (r"/api/api-interfaces/create", ApiInterfaceCreateApiHandler),
        (r"/api/api-interfaces/update", ApiInterfaceUpdateApiHandler),
        (r"/api/api-interfaces/delete", ApiInterfaceDeleteApiHandler),
        (r"/api/api-interfaces/toggle", ApiInterfaceToggleApiHandler),
        # 技能管理
        (r"/admin/skill-management", SkillManagementHandler),
        (r"/api/skills/list", SkillListApiHandler),
        (r"/api/skills/get", SkillGetApiHandler),
        (r"/api/skills/enabled", SkillEnabledListApiHandler),
        (r"/api/skills/create", SkillCreateApiHandler),
        (r"/api/skills/update", SkillUpdateApiHandler),
        (r"/api/skills/delete", SkillDeleteApiHandler),
        (r"/api/skills/toggle", SkillToggleApiHandler),
        (r"/admin/watch-management", WatchManagementHandler),
        (r"/api/watch/collect", WatchCollectApiHandler),
        (r"/api/watch/data", WatchCollectedDataApiHandler),
        (r"/api/watch/save-to-warehouse", WatchSaveToWarehouseApiHandler),
        (r"/admin/warehouse-management", WarehouseManagementHandler),
        (r"/api/warehouse/list", WarehouseListApiHandler),
        (r"/api/warehouse/get", WarehouseGetApiHandler),
        (r"/api/warehouse/delete", WarehouseDeleteApiHandler),
        (r"/api/warehouse/batch-delete", WarehouseBatchDeleteApiHandler),
        (r"/api/warehouse/batch-deep-collect", WarehouseBatchDeepCollectApiHandler),
        (r"/api/deep-collect/start", DeepCollectStartSingleApiHandler),
        (r"/api/deep-collect/task", DeepCollectTaskApiHandler),
        (r"/api/deep-collect/result", DeepCollectResultApiHandler),
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
        (r"/api/digital-employees/skills", DigitalEmployeeSkillsApiHandler),
        (r"/api/digital-employees/test", DigitalEmployeeTestApiHandler),
        (r"/api/user/register", UserRegisterApiHandler),
        (r"/api/user/models", UserModelsApiHandler),
        (r"/api/user/digital-employees", UserDigitalEmployeesApiHandler),
        (r"/api/user/conversations", UserConversationsApiHandler),
        (r"/api/user/chat", UserChatApiHandler),
        (r"/api/user/image-gen", ImageGenHandler),
        (r"/api/user/video-gen", VideoGenHandler),
        (r"/api/user/export/pdf", UserExportPdfApiHandler),
        
        # 内置API型数字员工（模拟）
        (r"/api/mock/news", MockNewsHandler),
        (r"/api/mock/music", MockMusicHandler),
        (r"/api/mock/weather", MockWeatherHandler),
        (r"/api/mock/movie", MockMovieHandler),
    ],
    **settings
    )


if __name__ == '__main__':
    logger.info(f"正在启动 {config.SYSTEM_NAME} ({config.SYSTEM_SHORT_NAME})...")
    
    logger.info("初始化数据库表结构...")
    init_db()

    logger.info("执行数据库迁移...")
    run_migrations()
    
    logger.info("执行运行时检查...")
    run_runtime_checks()
    
    webapp = webapp()
    server = HTTPServer(webapp)
    server.listen(config.PORT)
    
    logger.info(f"{config.SYSTEM_NAME} 已启动: http://localhost:{config.PORT}/")
    tornado.ioloop.IOLoop.current().start()
