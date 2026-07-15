# DataFinderAgentOS 模板分层说明

## 系统背景
- **系统名称**：某政务智能瞭望与智能问数系统
- **系统类型**：Web B/S 结构的数据智能采集和数据智能问数系统
- **架构划分**：用户侧-前台 + 管理侧-后台
- **用户侧定位**：类 ChatGPT 的智能应用，用户通过 Chat 模式与数据直接对话，实现智能问数，通过模型直接获得数据统计、分析、生成图形图像报表
- **管理侧定位**：后台管理系统，负责用户、权限、数据采集、模型引擎、数字员工、大屏展示等管理功能

## 文档定位
- 本文件说明项目模板的目录组织方式、前后台模板的边界划分和各自承载的页面范围。
- 以真实仓库代码为依据，反映模板分层结构的当前状态和规划。

---

## 模板目录结构

```
app/templates/
├── base.html              # 用户侧-前台母版页（含chat.css全局样式）
├── login.html             # 用户侧-前台登录页（双栏布局，含系统品牌展示）
├── register.html          # 用户侧-前台注册页（含表单验证）
├── chat.html              # 用户侧-智能问数对话主页（五区布局）
│
├── admin/                 # 后台管理侧页面
│   ├── base.html          # 后台母版页（Layui Admin 布局）
│   ├── login.html         # 后台登录页
│   ├── index.html         # 后台首页/仪表盘
│   ├── user_management.html       # 用户管理
│   ├── role_management.html       # 角色管理
│   ├── function_management.html   # 功能模块管理
│   ├── menu_management.html       # 菜单管理
│   ├── source_management.html     # 瞭源管理（对应需求：采集管理）
│   ├── watch_management.html      # 瞭望采集管理（对应需求：瞭望管理）
│   ├── warehouse_management.html  # 数据仓库管理（对应需求：数据管理）
│   ├── model_engine.html          # 模型引擎
│   ├── digital_employee_management.html  # 数字员工管理
│   ├── profile_modals.html        # 个人信息/修改密码（嵌入模板）
│   ├── user_manage.html           # 遗留文件（旧版用户管理）
└───└── ...
```

---

## 模板分层原则

### 前后台严格分离
- `app/templates/admin/` 下的模板文件**仅**用于后台管理侧页面。
- `app/templates/` 下与 `admin/` 同级的模板文件**仅**用于用户侧前台页面。
- 前后台模板不得混用，不出现后台模板引用前台布局、或前台模板引入后台组件的情况。

### 模板归属判定
| 判断条件 | 归属 | 示例 |
|---------|------|------|
| 页面入口路由以 `/admin/` 开头 | 后台管理侧 | `/admin/user-management` |
| 页面入口路由为根路径 `/` | 用户侧前台 | `/`, `/login`, `/chat`, `/index` |
| 页面需要 RBAC 权限校验 | 后台管理侧 | 用户/角色/功能/菜单管理等 |
| 页面面向公众用户 | 用户侧前台 | 登录、注册、对话等 |

---

## 需求功能 → 模板映射

### 后台管理侧模块映射
| 需求功能 | 对应模板 | 实现状态 | 说明 |
|---------|---------|---------|------|
| 用户管理 | `admin/user_management.html` | ✅ 已实现 | 用户CRUD、分页、超管保护 |
| 功能管理 | `admin/function_management.html` | ✅ 已实现 | 功能CRUD、父子层级 |
| 菜单管理 | `admin/menu_management.html` | ✅ 已实现 | 菜单CRUD、排序、预览 |
| 角色管理 | `admin/role_management.html` | ✅ 已实现 | 角色CRUD、功能分配树 |
| 瞭望管理 | `admin/watch_management.html` | ✅ 已实现 | 瞭望采集执行、橱窗展示、保存到仓库 |
| 数据管理 | `admin/warehouse_management.html` | ✅ 已实现 | 数据仓库列表、深度采集、结果查看 |
| 采集管理 | `admin/source_management.html` | ✅ 已实现 | 瞭源CRUD、URL模板配置（采集源管理） |
| 数字员工 | `admin/digital_employee_management.html` | ✅ 已实现 | 数字员工CRUD、测试 |
| 模型引擎 | `admin/model_engine.html` | ✅ 已实现 | 模型管理、分类筛选、对话测试 |
| 数智大屏 | `admin/big_screen.html` | ❌ 待实现 | 数据可视化大屏 |
| 舆情大屏 | `admin/opinion_screen.html` | ❌ 待实现 | 舆情监控大屏 |

### 用户侧前台模块映射
| 需求功能 | 对应模板 | 实现状态 | 说明 |
|---------|---------|---------|------|
| 用户登录 | `login.html` | ✅ 已实现 | 双栏品牌布局，AJAX异步登录 |
| 用户注册 | `register.html` | ✅ 已实现 | 含表单验证、XSRF防护 |
| 用户对话 | `chat.html` | ✅ 已实现 | 五区布局（A/B/C/D/E），SSE流式输出 |
| 数字员工 | `chat.html`(集成) | ✅ 已实现 | 通过 `@` 命令在对话界面调用 |
| @天气 | `chat.html`(集成) | ✅ 已实现 | @数字员工技能调用，对话界面集成 |
| @新闻 | `chat.html`(集成) | ✅ 已实现 | 同上 |
| @音乐 | `chat.html`(集成) | ✅ 已实现 | 同上 |
| @电影 | `chat.html`(集成) | ✅ 已实现 | 同上 |
| @yummy | `chat.html`(集成) | ✅ 已实现 | 同上 |
| 报表功能 | `report.html` | ❌ 待实现 | 独立报表页面 |
| 历史记录 | (对话侧栏C区已实现) | ⏳ 部分完成 | C区显示对话历史列表，本地存储 |
| 报告导出 | `export.html` | ❌ 待实现 | 报告导出页面 |

> **说明**：@天气/@新闻/@音乐/@电影/@yummy 为数字员工技能调用的快捷入口，通过对话界面中的 `@` 命令菜单激活，无需独立模板页面。

---

## 当前模板状态

### 已实现的模板
| 模板文件 | 所属侧 | 功能 |
|---------|-------|------|
| `admin/base.html` | 后台 | Layui Admin 布局，含侧栏菜单树、顶栏用户菜单 |
| `admin/login.html` | 后台 | 管理员登录页 |
| `admin/index.html` | 后台 | 后台首页仪表盘 |
| `admin/user_management.html` | 后台 | 用户CRUD、分页搜索、超管保护 |
| `admin/role_management.html` | 后台 | 角色CRUD、功能分配树 |
| `admin/function_management.html` | 后台 | 功能CRUD、父子层级、启用/禁用 |
| `admin/menu_management.html` | 后台 | 菜单CRUD、排序、预览 |
| `admin/source_management.html` | 后台 | 瞭源CRUD、URL模板配置 |
| `admin/watch_management.html` | 后台 | 瞭望采集、橱窗展示、保存到仓库 |
| `admin/warehouse_management.html` | 后台 | 数据仓库列表、深度采集、结果查看 |
| `admin/model_engine.html` | 后台 | 模型管理、分类筛选、对话测试 |
| `admin/digital_employee_management.html` | 后台 | 数字员工CRUD、测试 |
| `admin/profile_modals.html` | 后台 | 嵌入模板，个人信息/改密码弹窗 |
| `base.html` | 前台 | 用户侧母版页（含chat.css样式） |
| `login.html` | 前台 | 用户登录页（双栏品牌布局） |
| `register.html` | 前台 | 用户注册页（含表单验证） |
| `chat.html` | 前台 | 智能问数对话主页（五区：A LOGO/B 模型/C 历史/D 对话/E 输入） |

### 待实现的模板
| 模板文件 | 所属侧 | 规划功能 |
|---------|-------|---------|
| `report.html` | 前台 | 报表查看/生成页面 |
| `history.html` | 前台 | 历史记录独立页面（C区已有基础列表） |
| `export.html` | 前台 | 报告导出页面 |
| `admin/big_screen.html` | 后台 | 数智大屏 |
| `admin/opinion_screen.html` | 后台 | 舆情大屏 |

---

## 模板引用关系

```
admin/base.html ← 所有后台页面继承
├── user_management.html
├── role_management.html
├── function_management.html
├── menu_management.html
├── source_management.html
├── watch_management.html
├── warehouse_management.html
├── model_engine.html
├── digital_employee_management.html
└── profile_modals.html（被各页面 {% include %} 引用）

base.html ← 用户侧页面继承（含chat.css样式表）
├── login.html（已实现）
├── register.html（已实现）
├── chat.html（已实现，五区ChatGPT式布局）
├── report.html（待实现）
├── history.html（待实现）
└── export.html（待实现）
```

---

## 模板开发规范
1. 后台所有页面必须继承 `admin/base.html`，使用 `{% block body %}` 定义内容区域。
2. 后台页面内容区域使用 Layui 标准组件（表格、表单、分页、弹窗）。
3. 用户侧页面使用独立设计语言（类ChatGPT界面），不与后台Layui Admin布局混用。
4. 新增后台管理模块 → 模板放入 `app/templates/admin/`。
5. 新增用户侧功能 → 模板放入 `app/templates/`。
6. 所有模板统一使用 Tornado 模板语法（`{{ }}`、`{% %}`）。
7. 用户侧对话界面采用流式 SSE 输出（复用 `UserChatApiHandler` 的 SSE 代理能力）。
8. @技能命令（天气/新闻/音乐/电影/yummy）作为对话界面的插件式能力，通过数字员工 API 调用实现，无需独立模板页面。
9. 用户侧模板共享 `chat.css` 样式文件（含登录/注册/对话三套样式），使用浅色系政务简约风格。
