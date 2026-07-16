# DataFinderAgentOS 开发约束

## 系统背景
- **系统名称**：某政务智能瞭望与智能问数系统
- **系统类型**：Web B/S 结构的数据智能采集和智能问数系统
- **架构划分**：用户侧-前台 + 管理侧-后台
- **用户侧定位**：类 ChatGPT 的智能应用，用户通过 Chat 模式与数据直接对话，实现智能问数
- **用户侧功能**：登录、注册、对话、数字员工调用、@技能命令、智能问数、报表渲染、PDF导出
- **管理侧功能**：控制台、用户管理、功能管理、菜单管理、角色管理、瞭望采集、瞭源管理、数据仓库、深度采集、数字员工、模型引擎、数智大屏、舆情大屏

## 文档定位
- 本文件用于沉淀当前项目中需要长期遵守的开发约束，作为团队协作的基础上下文。

## 环境约束
- 所有开发、运行、测试均在项目根目录下的 `venv/` 虚拟环境中完成。
- Python 启动入口固定为 `run.py`（`venv\Scripts\python run.py`）。
- 当前运行端口由 `run.py` 配置为 `10010`。
- 依赖见 `requirements.txt`：tornado、crawl4ai、reportlab、psutil 等。

## 架构约束
- 项目采用轻量 MVC 结构，核心业务代码集中在 `app/`。
- `app/controllers/` 负责路由处理、参数获取、调用模型与模板渲染。
- `app/models/` 负责 SQLite 数据访问与业务相关数据方法。
- `app/parsers/` 负责数据源解析（百度新闻、JSON API、RSS等）。
- `app/services/` 负责业务服务（PDF导出等）。
- `app/templates/` 负责 Tornado 模板页面。
- `app/static/` 负责公共 CSS/JS/第三方资源。
- 数据库文件固定存放于 `database/finderos.db`。

## 模板分层约束
- `app/templates/admin/` 目录专用于后台管理侧页面。
- `app/templates/` 下与 `admin/` 同级的模板文件专用于用户侧前台页面。
- 前后台页面在模板组织、菜单结构、权限控制和路由设计中严格区分。
- @技能命令作为对话界面的插件式能力，无需独立模板页面。

## 路由设计约束
- 后台管理侧路由统一使用 `/admin/` 前缀。
- 用户侧前台路由统一使用根路径体系。
- API路由统一使用 `/api/` 前缀。
- 多模态API：`/api/user/image-gen`，`/api/user/video-gen`。
- 导出API：`/api/user/export/pdf`。
- 后续新增路由时，前后台不得混用 URL 前缀。

## 代码组织约束
- 旧版控制器 `app/controllers/admin.py`（含 AdminUserController 等）已删除。
- 新版控制器按模块拆分到独立文件（15个控制器文件）。
- 数据模型按模块拆分到独立文件（12个模型文件）。
- 解析器按数据源类型拆分到独立文件（4个解析器文件）。
- 遗留模板 `app/templates/admin/user_manage.html` 已删除。
- `app/controllers/admin_deep_collect.py` 不存在，深度采集集成在 `admin_warehouse.py` 中。

## 界面设计约束
- 系统页面必须支持响应式设计、沉浸式体验、自适应模式（移动端+PC端）。
- 后台管理侧基于 Layui Admin 布局，用户侧前台采用浅色系政务简约风格。
- 后台主题支持亮/暗色切换（通过 `theme.css`）。
- 同一套视觉语言，前后台根据业务场景区分信息密度和操作复杂度。

## 框架约束
- 后端框架：Tornado（自定义 web.Application）。
- 数据存储：SQLite 本地单文件模式。
- 认证机制：Tornado `secure_cookie` + PBKDF2-HMAC-SHA256 密码哈希 + XSRF。
- AI对话通信：SSE（Server-Sent Events）代理到 OpenAI 兼容 API，基于 AsyncHTTPClient。
- 数据可视化：ECharts（含 echarts-gl、echarts-wordcloud）。
- PDF导出：reportlab（Windows 微软雅黑）。
- 网页爬虫：crawl4ai + Playwright Chromium 引擎。
- 前端界面：Layui 优先，Bootstrap 补充。

## 前端资源约束
- `app/static/dist/` 已放置本地化第三方资源包。
- 当前包含：bootstrap-5.3.8-dist、layui、echarts。
- 后台管理侧和用户前台侧默认优先基于 Layui 构建界面。
- 数据可视化场景优先使用 ECharts。
- 当 Layui 无法满足响应式样式或栅格补充时，引入 Bootstrap 补充。

## 安全与配置约束
- 安全设计需覆盖 OWASP Top 10 主要风险。
- 身份认证、权限控制（RBAC）、输入校验、XSS防护、CSRF防护、注入防护已基本实现。
- 所有配置统一存放在 `config/` 目录下（当前 `config/api_keys.json` 已启用，其余配置仍待抽离）。
- 智能问数场景不允许暴露真实 SQL 或接受用户 SQL 输入。

## 文档维护约束
- `docs/codingprompt.txt` 视为人类约定文档，不由 AI 主动维护。
- `docs/constraint.md`、`docs/requirement.md`、`docs/project_tree_full.txt` 由 AI 持续维护。
- `docs/test_case.md` 在收到明确测试相关指令时维护。
- `docs/role.md`、`docs/template.md` 本次起纳入 AI 维护范围，根据任务书同步更新。

## 当前真实状态约束（v0.3 合并后）

### 已实现的业务模块（15个后台功能 + 7个用户侧功能）
- **后台管理侧**：控制台（实时统计刷新）、用户管理、角色管理（含编辑弹窗）、功能管理、菜单管理（含图标展示）、瞭望采集、瞭源管理（多解析器）、数据仓库、深度采集（crawl4ai + 采集专员）、模型引擎（SSE对话/分类/Markdown）、数字员工管理（LLM+API双型）、数智大屏（ECharts可视化）、舆情大屏（实时监控/敏感词/AI分析）、个人信息管理
- **用户前台侧**：登录/注册、智能对话（五区布局+SSE流式）、智能问数（意图识别+数据库查询+报表渲染）、数字员工调用（@菜单+LLM/API双型）、@技能命令（天气/wttr.in、新闻-聚合数据API+Baidu兜底、音乐-iTunes API、电影-TMDB API+豆瓣补充+本地库、小dummy-LLM文案生成）、PDF导出、快捷功能（/菜单）

### 新增模块（远程合并引入）
- **数智大屏**: `/admin/data-screen` + 4个统计API（统计/词云/趋势/桑基图）
- **舆情大屏**: `/admin/opinion-screen` + 7个API（监控/告警/AI分析/敏感词）
- **PDF导出**: `UserExportPdfApiHandler` + `pdf_export.py`（reportlab）
- **人脸识别登录**: 前端模板 `face_login.html`（摄像头捕捉）
- **手势交互**: 前端模板 `gesture.html`（姿态识别）
- **多模态API**: 生图/生视频（DALL-E/Pollinations.ai回退）
- **解析器体系**: `parsers/` 包（百度新闻/JSON API/RSS三类型）
- **数据库迁移**: `big_screen → data_screen` 兼容旧版本
- **ECharts可视化**: `dist/echarts/` + `dashboard-charts.js`
- **主题切换**: `theme.css` 亮/暗色切换
- **管理侧专用样式**: `admin.css`

### 初始化数据
- **AI模型预设**: 4个（agnes-2.0-flash、qwen3.5-flash、DALL-E-3文本生图、Sora视频生成）
- **数字员工预设**: 6个（采集专员-LLM型、天气-API型(wttr.in)、小dummy-LLM文案生成、新闻-API型(聚合数据+Baidu兜底)、随机音乐-API型(iTunes API)、电影-API型(TMDB API+豆瓣补充+本地库)）
- **瞭源预设**: 3个（百度新闻-baidu_news、Hacker News-json_api、36氪-rss）
- **外部API已对接**: TMDB电影、聚合数据新闻、iTunes音乐、wttr.in天气
- **功能数量**: 15个（5个一级 + 10个二级）
- **角色预设**: 2个（系统管理员、普通用户）
- **敏感词预设**: 15条（用户攻击防护）

### 待实现需求
- **用户侧**: 独立历史记录页面、报表独立页面、自定义快捷命令
- **管理侧**: 日志审计、系统配置界面、会话/对话管理、系统设置
- **交互增强**: 人脸登录后端对接、手势识别后端对接、语音合成播报
- **安全治理**: 配置从 `run.py` 抽离到 `config/`、OWASP专项清单

### Q&A
**Q**: `config/` 和 `skills/` 目录为什么是空的？
**A**: `config/` 为配置目录，当前已存放 `api_keys.json`（外部API密钥管理：TMDB电影、聚合数据新闻已配置密钥并启用，iTunes音乐/wttr.in天气免费无需密钥），其余端口/模型配置仍硬编码在 `run.py` 中；`skills/` 为开发技能预留目录。
