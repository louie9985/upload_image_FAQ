# 部署说明

## 进程

第一版至少需要三个进程：

- Django Web：只提供 DRF API、Admin 和 media 文件访问。
- React Web：由 Vite 开发服务或独立前端静态服务提供页面。
- Celery Worker：执行大模型生成和 webhook 上传任务。
- Celery Beat：定时触发周期任务（例如每周清理 7 天前的媒体图片）。
- Redis：作为 Celery broker/result backend。

## Docker Compose（推荐）

适用于只有 IP、公司内网使用、媒体文件落本地磁盘的场景。默认通过 Nginx 提供同源入口：

- 前端：`http://<服务器IP>/`
- 后端 API：`http://<服务器IP>/api/`
- Admin：`http://<服务器IP>/admin/`
- 媒体：`http://<服务器IP>/media/`

准备 `.env`（可从 `.env.example` 复制）后启动：

```bash
docker compose up -d --build
```

首次启动后创建管理员：

```bash
docker compose exec backend uv run python manage.py createsuperuser
```

查看日志：

```bash
docker compose logs -f --tail=200
```

数据持久化：

- Postgres 数据：`pg_data` volume
- Redis 数据：`redis_data` volume
- 媒体文件：`media_data` volume（容器重建不会丢）

## 静态资源

开发时建议使用 Vite：

```bash
cd frontend
npm run dev
```

上线时构建前端：

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/`，请交给独立静态服务、Nginx、对象存储或未来企业平台前端基座托管。Django 不读取 `frontend/dist/index.html`，也不托管 `/assets`。

本地开发时，Vite 会把 `/api` 和 `/media` 代理到 Django：

```text
React:  http://localhost:5173
Django: http://localhost:8000
```

## 文件存储

第一版图片保存到本地 `media/faq_images/`。数据库中的上传日志只记录 webhook 返回的 CDN 链接和来源草稿 ID，不保存 base64。

后续接入企业平台时，可以把 `UploadedImage.image` 切换到对象存储，业务层不需要大改。

## 注意事项

- 不要把 `.env` 提交到仓库。
- Redis 必须先启动，否则 Celery 任务无法执行。
- 本地临时调试且未安装 Redis 时，可以用 `CELERY_TASK_ALWAYS_EAGER=true uv run python manage.py runserver` 启动 Django，让任务在 Web 进程内同步执行；正式环境仍应使用 Redis + Celery Worker。
- 变更模型后需要执行 `uv run python manage.py migrate`，否则生成项、上传记录的企业微信返回字段、来源草稿 ID 和 AI Token 用量日志无法写入。
- 企业微信 OAuth 回调地址必须与企业微信后台配置一致。
- webhook 链接由用户在页面填写，系统保存配置并脱敏展示扩展点已预留。

## Celery Beat（定时任务）

启动 worker：

```bash
uv run celery -A config worker -l info
```

启动 beat：

```bash
uv run celery -A config beat -l info
```

当前内置的定时任务：

- 每周六北京时间 04:00 清理 7 天前上传的本地媒体图片（`UploadedImage`）。

