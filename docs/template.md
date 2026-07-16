# DataFinderAgentOS 模板规范

## 文档定位
- 本文件记录当前项目中所有模板文件的规范、职责和映射关系。
- 各模板需遵循统一的页面结构和组件引用策略。

---

## 一、模板目录结构

```
app/templates/
├── base.html                         用户侧-公共基础模板
├── index.html                        用户侧-登录后重定向页 → /chat
├── login.html                        用户侧-登录页（双栏品牌布局）
├── register.html                     用户侧-注册页
├── chat.html                         用户侧-智能问数对话主页
├── face_login.html                   人脸识别登录页（模板初版）
├── gesture.html                      手势交互页（模板初版）
│
└── admin/
    ├── base.html                     管理侧-公共基础模板（Layui Admin）
    ├── login.html                    管理侧-登录页
    ├── index.html                    管理侧-首页仪表盘
    ├── data_screen.html              数智大屏（ECharts可视化）
    ├── opinion_screen.html           舆情大屏
    ├── user_management.html          用户管理
    ├── role_management.html          角色管理
    ├── function_management.html      功能管理
    ├── menu_management.html          菜单管理
    ├── source_management.html        瞭源管理
    ├── watch_management.html         瞭望采集
    ├── warehouse_management.html     数据仓库
    ├── model_engine.html             模型引擎
    ├── digital_employee_management.html 数字员工
    └── profile_modals.html           个人信息/修改密码弹窗
```

---

## 二、基础模板规范

### 2.1 用户侧 `base.html`
- **角色**：所有用户侧页面的基础骨架
- **提供**：`<head>`（meta/viewport/Layui CSS/自定义CSS）、`<body>` 框架
- **块定义**：
  - `{% block body %}{% end %}` — 页面主体内容
  - `{% block script %}{% end %}` — 页面底部JS
- **引用资源**：
  - `layui.css`（来自 `/static/dist/layui/css/layui.css`）
  - `base.css`

### 2.2 管理侧 `base.html`
- **角色**：所有管理侧页面的基础骨架
- **提供**：同用户侧 base
- **引用资源**：
  - `layui.css`
  - `base.css`、`admin.css`、`theme.css`
- **页面布局结构**（在各子模板中实现）：
  - `<div class="layui-layout layui-layout-admin">`
    - `<div class="layui-header">` — LOGO + 用户菜单
    - `<div class="layui-side">` — 侧边菜单树
    - `<div class="layui-body">` — 工作区
    - `<div class="layui-footer">` — 版权

---

## 三、页面模板映射表

| 模板文件 | 路由 | 控制器 | 布局风格 | 功能描述 |
|---------|------|-------|---------|---------|
| 用户侧 `login.html` | `/login` | `LoginHandler` | 双栏品牌 | 用户邮箱/密码登录 |
| 用户侧 `register.html` | `/register` | `RegisterHandler` | 双栏品牌 | 用户注册 + XSRF |
| 用户侧 `chat.html` | `/chat` | `UserChatHandler` | 五区布局 | SSE流式对话 + @技能 |
| 用户侧 `face_login.html` | - | - | 全屏深色 | 人脸识别（模板初版） |
| 用户侧 `gesture.html` | - | - | 全屏深色 | 手势交互（模板初版） |
| 管理侧 `login.html` | `/admin/` `/admin/login` | `AdminLoginHandler` | 居中卡片 | 管理员登录 |
| 管理侧 `index.html` | `/admin/index` | `AdminIndexHandler` | Admin布局 | 统计卡片+系统概览 |
| 管理侧 `data_screen.html` | `/admin/data-screen` | `DataScreenHandler` | 全屏布局 | ECharts可视化大屏 |
| 管理侧 `opinion_screen.html` | `/admin/opinion-screen` | `OpinionScreenHandler` | 全屏布局 | 舆情监控大屏 |
| 管理侧 `user_management.html` | `/admin/user-management` | `UserManagementHandler` | Admin布局 | 用户CRUD表格 |
| 管理侧 `role_management.html` | `/admin/role-management` | `RoleManagementHandler` | Admin布局 | 角色CRUD+功能树+编辑弹窗 |
| 管理侧 `function_management.html` | `/admin/function-management` | `FunctionManagementHandler` | Admin布局 | 功能CRUD+父子层级 |
| 管理侧 `menu_management.html` | `/admin/menu-management` | `MenuManagementHandler` | Admin布局 | 菜单CRUD+排序+预览+图标 |
| 管理侧 `source_management.html` | `/admin/source-management` | `SourceManagementHandler` | Admin布局 | 瞭源CRUD+规则+解析器 |
| 管理侧 `watch_management.html` | `/admin/watch-management` | `WatchManagementHandler` | Admin布局 | A搜索+B瞭源+C橱窗 |
| 管理侧 `warehouse_management.html` | `/admin/warehouse-management` | `WarehouseManagementHandler` | Admin布局 | 数据仓库+深度采集+批量 |
| 管理侧 `model_engine.html` | `/admin/model-engine` | `ModelEngineHandler` | Admin布局 | 网格模型+SSE对话 |
| 管理侧 `digital_employee_management.html` | `/admin/digital-employee` `/admin/digital-employee-management` | `DigitalEmployeeManagementHandler` | Admin布局 | 数字员工CRUD+双型+MD |
| `profile_modals.html` | 嵌入各管理页面 | — | 弹窗 | 个人信息/修改密码 |

---

## 四、UI 组件引用规范

### 4.1 优先级策略
1. **Layui** — 通用表单、表格、导航、按钮、分页、弹窗、树组件
2. **ECharts** — 数据可视化、图表、词云、桑基图
3. **Bootstrap** — 仅当 Layui 无法满足响应式栅格或特殊布局时补充

### 4.2 JS 库引用
- Layui JS → `{{ static_url('dist/layui/layui.js') }}`
- 管理侧每个模板通过 `layui.use(['form', 'table', 'layer', 'element', 'jquery'], ...)` 加载模块
- 对话场景 → `marked.min.js`（Markdown渲染）
- 可视化场景 → `echarts.min.js`、`echarts-gl.min.js`、`echarts-wordcloud.min.js`、`dashboard-charts.js`
- 用户侧对话 → `chat.js`

---

## 五、sidebar 菜单渲染规范

所有管理侧模板（`user_management.html`、`role_management.html` 等）中，sidebar 菜单渲染代码必须与以下规范保持一致：

```html
{% for parent in user_info.get('menu_tree', []) %}
{% if parent.get('children', []) %}
<li class="layui-nav-item">
    <a href="javascript:;">
        <i class="layui-icon {{ parent.get('func_icon') }}"></i> {{ parent.get('func_name') }}
    </a>
    <dl class="layui-nav-child">
        {% for child in parent.get('children', []) %}
        <dd>
            <a href="{{ child.get('func_route') }}">{{ child.get('func_name') }}</a>
        </dd>
        {% end %}
    </dl>
</li>
{% else %}
<li class="layui-nav-item">
    <a href="{{ parent.get('func_route') }}">
        <i class="layui-icon {{ parent.get('func_icon') }}"></i> {{ parent.get('func_name') }}
    </a>
</li>
{% end %}
{% end %}
```

注意：该代码块在各管理模板中重复出现，维护时需同步更新所有文件。

---

## 六、模板修改记录

| 日期 | 文件 | 变更内容 |
|------|------|---------|
| 2026-07-15 | 所有admin模板 | 增加 `type="button"` 防止弹窗闪现，修复 `form.reset()` |
| 2026-07-15 | `user_management.html` | 增加编辑密码字段、超管保护 |
| 2026-07-15 | `role_management.html` | 实现编辑弹窗（AJAX回填+状态修改） |
| 2026-07-15 | `index.html` | 增加8项实时统计卡片+30秒轮询 |
| 2026-07-15 | 所有admin模板 | 统一Logo CSS（line-height/width修复） |
| 2026-07-15 | `menu_management.html` | 图标以图形化展示 |
| 2026-07-15 | `login.html`、`register.html` | 输入框样式与后台管理侧统一 |
| 2026-07-15 | `digital_employee_management.html` | 操作按钮溢出修复、MD文件上传 |
| v0.3合并 | `data_screen.html` | 新增：数智大屏ECharts可视化 |
| v0.3合并 | `opinion_screen.html` | 新增：舆情大屏实时监控 |
| v0.3合并 | `face_login.html` | 新增：人脸识别登录模板 |
| v0.3合并 | `gesture.html` | 新增：手势交互模板 |
| v0.3合并 | 所有admin模板 | 增加 `admin.css` + `theme.css` 引用 |
