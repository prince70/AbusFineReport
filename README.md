# 装嵌生产进度管理平台

完整的生产进度查询与权限管理系统，包含登录、菜单导航、用户管理、角色权限管理等功能。

## 功能特性

- ✅ 用户登录/登出
- ✅ 响应式菜单导航
- ✅ 装嵌生产进度查询
- ✅ 数据导出 Excel
- ✅ 用户管理（CRUD）
- ✅ 角色管理（CRUD）
- ✅ 权限控制（按钮级权限）
- ✅ 仪表板统计
- ✅ Docker 部署

## 快速开始

### 方式一：Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问：http://localhost:5000

### 方式二：本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

访问：http://localhost:5000

## 默认账号

- **管理员**：admin / admin123
- **普通用户**：user / user123

## 技术栈

- **前端**：Vue 2 + Element UI
- **后端**：Flask + SQLite
- **部署**：Docker

## 项目结构

```
production-query/
├── app.py                 # 后端 Flask 应用
├── index.html            # 前端主页面
├── requirements.txt      # Python 依赖
├── Dockerfile          # Docker 镜像配置
├── docker-compose.yml # Docker Compose 配置
├── production.db     # SQLite 数据库（自动生成）
└── src/
    └── assemblyProductionProgress.vue  # 参考组件
```
