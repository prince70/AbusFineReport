# 装嵌生产进度管理平台

当前项目采用真正的 Vue SFC + Vite 构建，以及 Python 后端服务分层结构。

## 核心能力

- 登录与会话管理
- 动态菜单与权限控制
- 装嵌进度查询（完成状态多选）
- 装嵌进度后端 Excel 导出
- 外协清单查询、导出、打印
- 用户管理与角色管理

## 技术栈

- 前端：Vue 2 SFC + Vue Router + Element UI + Vite
- 后端：Flask + SQLite + SQL Server(pyodbc)
- 导出：openpyxl / xlsx-js-style

## 目录结构

```text
production-query/
├── run.py                       # 后端启动入口
├── index.html                   # Vite 入口模板
├── package.json
├── vite.config.js
├── requirements.txt
├── backend/
│   ├── __init__.py
│   ├── app_main.py              # Flask 应用与路由入口
│   └── services/
│       ├── __init__.py
│       ├── assembly_service.py
│       └── checklist_service.py
├── src/
│   ├── App.vue
│   ├── main.js
│   ├── components/
│   │   └── AppLayout.vue
│   ├── pages/
│   │   ├── LoginPage.vue
│   │   ├── DashboardPage.vue
│   │   ├── AssemblyProgressPage.vue
│   │   ├── ChecklistPage.vue
│   │   ├── UserManagementPage.vue
│   │   ├── RoleManagementPage.vue
│   │   └── ForbiddenPage.vue
│   ├── router/
│   │   └── index.js
│   ├── services/
│   │   └── auth.js
│   └── styles/
│       └── app.css
└── assets/
	├── logo.ico
	└── fonts/
```

## 本地开发

1. 安装前端依赖

```bash
npm install
```

2. 安装后端依赖

```bash
pip install -r requirements.txt
```

3. 启动后端（5000）

```bash
python run.py
```

4. 启动前端开发服务（5173）

```bash
npm run dev
```

## 生产构建

```bash
npm run build
python run.py
```

构建产物输出到 `frontend-dist/`，由 Flask 在 `/static/*` 下托管。

## 默认账号

- 管理员：admin / admin123
- 普通用户：user / user123
