---
name: docker-slim-packaging
description: "Use when: Docker打包、镜像体积优化、导出tar/tar.gz、端口一致性检查。关键词: 重新打包, 压缩镜像, docker镜像太大, 导出镜像包, docker compose build。"
---

# Docker Slim Packaging

## 目标

用稳定、可复用的流程完成以下事项：
1. 构建可运行镜像。
2. 控制镜像体积（优先保持小体积）。
3. 导出交付文件（tar/tar.gz）。
4. 验证端口与服务连通性。

## 默认规范

1. `.dockerignore` 必须排除本地大文件和虚拟环境：
- `*.tar`
- `*.tar.gz`
- `.venv/`
- `venv/`
- `.git/`
- `**/__pycache__/`

2. Python 依赖安装必须使用：
- `pip install --no-cache-dir -r requirements.txt`

3. Dockerfile 优先使用多阶段构建：
- `builder` 阶段安装编译依赖（如 `gcc`, `g++`, `unixodbc-dev`）
- `runtime` 阶段只保留运行时依赖（如 `unixodbc`, `msodbcsql18`）

4. 端口配置一致性：
- `app.py` 监听端口
- `Dockerfile` `EXPOSE` 端口
- `docker-compose.yml` 映射端口
以上三处必须一致（本项目默认 `8001`）。

## 标准执行步骤

1. 构建镜像
```powershell
docker compose build web
```

2. 启动容器（必要时重建）
```powershell
docker compose up -d --build web
```

3. 查看运行状态和端口
```powershell
docker compose ps
```

4. 连通性检查（本项目默认 8001）
```powershell
curl -s -o NUL -w "%{http_code}" http://127.0.0.1:8001/
```
期望返回 `200`。

5. 导出镜像并压缩
```powershell
docker save -o production-query-web.tar production-query-web:latest
tar -czf production-query-web.tar.gz production-query-web.tar
```

6. 输出产物信息
```powershell
Get-Item production-query-web.tar, production-query-web.tar.gz | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
```

## 排障清单

1. `compose ps` 端口映射正确，但 `curl` 返回 `000`：
- 检查容器日志是否监听了错误端口。
```powershell
docker compose logs --tail=120 web
```
- 若监听端口与映射不一致，执行 `docker compose up -d --build web`。

2. 镜像体积异常增大：
- 优先检查构建上下文是否误包含 `*.tar`、`.venv`、数据库备份等。
- 再检查是否遗漏 `--no-cache-dir` 与多阶段构建。

3. 修改端口后不生效：
- 检查 `app.py` / `Dockerfile` / `docker-compose.yml` 三处是否一致。
- 强制重建并重启容器。

## 交付要求

每次打包后，至少汇报：
1. 镜像名和 tag。
2. 镜像大小。
3. 访问地址和探活状态码。
4. 导出包文件名与大小。
