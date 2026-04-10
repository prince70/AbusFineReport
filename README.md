# 生产进度管理平台（production-query）

本项目是一个前后端一体化的生产查询系统，支持：

- 装嵌生产进度查询与导出
- 外协加工清单查询、导出、打印
- 用户/角色/权限管理
- Docker 一键构建与启动（包含前端自动构建）

## 1. 技术栈

- 前端：Vue 2 + Vue Router + Element UI + Vite
- 后端：Flask
- 数据源：SQLite（默认）/ SQL Server（可切换）
- Excel 导出：openpyxl（后端）+ xlsx-js-style（前端）

## 2. 运行端口

统一端口：`8001`

- `run.py` 监听：`0.0.0.0:8001`
- `Dockerfile` 暴露：`EXPOSE 8001`
- `docker-compose.yml` 映射：`8001:8001`

## 3. 目录说明

```text
production-query/
├── backend/                     # Flask 后端
│   ├── app_main.py
│   └── services/
│       ├── assembly_service.py
│       └── checklist_service.py
├── src/                         # Vue 前端源码
│   ├── pages/
│   │   ├── LoginPage.vue
│   │   ├── AssemblyProgressPage.vue
│   │   ├── ChecklistPage.vue
│   │   ├── UserManagementPage.vue
│   │   └── RoleManagementPage.vue
│   └── ...
├── frontend-dist/               # 前端构建产物（由 Vite 生成）
├── assets/                      # 本地静态资源
├── scripts/
│   ├── start_docker.ps1         # Windows 推荐启动脚本
│   └── start_docker.cmd
├── docker-compose.yml
├── Dockerfile
├── run.py
├── requirements.txt
└── package.json
```

## 4. 本地开发（非 Docker）

### 4.1 环境准备

- Python 3.11+
- Node.js 18+
- npm

### 4.2 安装依赖

```powershell
pip install -r requirements.txt
npm install
```

### 4.3 启动方式

后端（Flask）：

```powershell
python run.py
```

前端开发（可选，联调用）：

```powershell
npm run dev
```

访问：`http://127.0.0.1:8001/`

## 5. Docker 部署（推荐）

### 5.1 一键启动脚本（Windows）

项目内置脚本：`scripts/start_docker.ps1`

默认行为：

1. 检查 Docker/Compose 可用性
2. 自动执行前端构建 `npm run build`
3. `docker compose up -d --build web`
4. 进行本地探活检查

执行：

```powershell
./scripts/start_docker.ps1
```

常用参数：

- `-NoBuild`：跳过 Docker 镜像重建（仍会构建前端）
- `-SkipFrontendBuild`：跳过前端构建
- `-Service web`：指定服务名
- `-Port 8001`：指定探活端口

示例：

```powershell
# 前端构建 + 跳过镜像重建
./scripts/start_docker.ps1 -NoBuild

# 跳过前端构建 + 重建镜像
./scripts/start_docker.ps1 -SkipFrontendBuild
```

### 5.2 纯 Compose 命令

```powershell
docker compose up -d --build web
docker compose ps
docker compose logs --tail=120 web
```

## 6. 数据库说明

默认使用 SQLite：

- `docker-compose.yml` 中 `DB_TYPE=sqlite`
- 数据文件通过 volume 映射：`./production.db:/app/production.db`

如需使用 SQL Server，请配置环境变量（可在 Compose 中覆盖）：

- `DB_TYPE=sqlserver`
- `DB_SERVER`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- 可选：`DB_DRIVER`、`DB_ENCRYPT`、`DB_TRUST_CERTIFICATE`

## 7. 默认账号

- 管理员：`admin / admin123`
- 普通用户：`user / user123`

## 8. 外协清单（/list）规则说明

当前版本关键计算规则：

- 新增列：`盆数`
- `盆数` 计算：
	1. 优先取“该分组备注数值求和”
	2. 若无可用备注数值，则回退为 `订单数量总和 / 每盆只数`
	3. 最终结果统一向上取整（ceil）

同时在页面下方显示全部统计：订单数量、毛重、净重、盆数。

## 9. 常见问题

### 9.1 页面没更新

- 确认执行的是 `./scripts/start_docker.ps1`（不是仅 `-NoBuild` 且未重建镜像的旧容器）
- 浏览器强制刷新（Ctrl + F5）
- 查看容器日志：

```powershell
docker compose logs --tail=120 web
```

### 9.2 对外地址访问不了

- 确认 `docker compose ps` 显示 `0.0.0.0:8001->8001/tcp`
- 检查服务器防火墙/安全组是否放行 8001

### 9.3 SQL Server 报列不存在（如备注列）

- 系统已做列名兼容探测（`备注/算好盆数/盆数`）
- 若仍异常，请提供目标表真实列名用于补充映射

## 10. 交付与离线部署建议

如果目标服务器不能联网：

1. 在可联网机器构建镜像
2. 导出镜像包
3. 传到目标机器后导入并启动

示例：

```powershell
docker compose build web
docker save -o production-query-web.tar production-query-web:latest
```

目标机导入：

```powershell
docker load -i production-query-web.tar
docker compose up -d web
```

