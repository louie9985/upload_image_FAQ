# 图片问答上传平台

本项目是一个快速上线版本的企业内部图片问答生成与上传工具，前端使用 React + Ant Design 独立运行，后端使用 Django REST Framework 只提供 API/Admin，后台任务使用 Celery + Redis。

## 功能范围

- 系统账号密码登录。
- 批量上传 `.png`、`.jpg`、`.jpeg` 图片。
- 页面预览图片，并要求用户为每张图片填写描述。
- 调用大模型 API 生成主问题、相似问题和答案。
- 通过 Ant Design 弹窗进度条展示生成和上传进度，失败时展示后端返回的错误原因。
- 前端采用企业级简洁风：统一浅灰背景、白色卡片、顶部说明区、流程分区和 KPI 卡片。
- 用户可在页面中审核、修改生成结果。
- 上传到用户填写的企业微信智能表格 webhook，并通过进度条等待上传完成。
- 支持单张图片生成一条问答，也支持在填写描述阶段勾选多张图片新增合并生成项，例如额外生成 `13`、`34`。
- 上传前才把图片转成 JPEG base64。
- 上传成功后只保存 webhook 返回的图片 CDN 链接和企业微信返回字段，不保存本地图片路径或 base64。
- 记录每次大模型调用的 Token 用量，用户可查看当前账号累计用量和明细。
- 记录用户操作日志。

## 技术栈

- 后端：Django、Django REST Framework、Celery、Redis、Pillow、requests、OpenAI SDK。
- 前端：Vite、React、TypeScript、Ant Design。
- 依赖管理：后端使用 uv。

## 快速启动

安装后端依赖：

```bash
uv sync
```

复制环境变量：

```bash
cp .env.example .env
```

生成数据库迁移并初始化数据库：

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

启动 Django：

```bash
uv run python manage.py runserver
```

启动 Celery：

```bash
uv run celery -A config worker -l info
```

安装并启动前端：

```bash
cd frontend
npm install
npm run dev
```

前端本地访问：

```text
http://localhost:5173
```

后端 API/Admin 本地访问：

```text
http://localhost:8000
```

注意：Django 不托管前端页面，前端开发和部署都独立处理；本地开发时 Vite 通过代理访问 `/api` 和 `/media`。

## 环境变量

```bash
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://upload_image_faq:change-me@127.0.0.1:5432/upload_image_faq
REDIS_URL=redis://localhost:6379/0

LLM_API_KEY=sk-your-api-key
# 也可使用 DeepSeek 官方变量名；若两者都配置，优先使用 LLM_API_KEY。
DEEPSEEK_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_REASONING_EFFORT=high
LLM_SIMILAR_QUESTIONS_MIN=5
LLM_SIMILAR_QUESTIONS_MAX=10

WECHAT_FIELD_QUESTION=f04Gwj
WECHAT_FIELD_SIMILAR=ftQMc5
WECHAT_FIELD_ANSWER=ftk5Tx
WECHAT_FIELD_IMAGES=fMAfWQ
```

## 使用流程

1. 员工通过系统账号密码登录。
2. 在新建任务页创建批量任务并上传图片，页面按上传、描述合并、审核、结果分区展示。
3. 为每张图片填写描述，描述为必填。
4. 可勾选多张图片新增合并项，并为合并项填写独立描述；合并项会在独立卡片中展示。
5. 提交生成任务，页面通过弹窗进度条等待，单图项和合并项都会生成问答草稿。
6. 查看并修改生成的问答结果；点击单条“保存当前修改”可立即保存，直接上传 webhook 时系统也会先自动保存页面上的未保存修改。
7. 填写 webhook 链接并上传，页面会展示 webhook 上传弹窗进度条和最终结果。
8. 在上传记录中查看问题、相似问题、答案、企业微信记录 ID、来源草稿 ID、企业微信返回字段和图片 CDN 链接。
9. 在 Token 用量页通过 KPI 卡片查看当前账号累计用量，并在明细表中查看最近调用。
10. 在 Django Admin 中查看中文化后的任务、生成项、草稿、上传记录、操作日志和 AI Token 用量。

