# 思维圆桌 Web

十五位大师参与的多轮思维圆桌对谈。**人物设定已内置**，访客无需安装 nuwa / Cursor Skill。

## 功能

- 15 位大师 face card，选 2–4 位参与
- 三轮：独立观点 → 交叉辩论 → 共识收敛
- 单次输出 ≤ 3500 字
- 支持公网部署，**访客零配置**

## 关于 API Key（重要）

| 场景 | 谁需要 Key | 说明 |
|------|-----------|------|
| **你部署到公网** | **只有你（站长）** | 在服务器设 `OPENAI_API_KEY`，访客直接用 |
| 本地自己玩 | 你 | 网页里填 Key，或设环境变量 |
| Cursor 聊天框圆桌 | 不需要 | 走 Cursor 月费，与本网站无关 |

**结论：部署到网上后，别人不需要 nuwa，也不需要 API Key——但你需要在服务器上配置一个 Key，费用由你承担。**

单次圆桌（4人×2轮+共识）用 `gpt-4o-mini` 约 **¥0.1–0.3**。

## 本地启动

```bash
cd roundtable-web
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."   # 站长 Key，访客模式
cd backend && uvicorn main:app --reload --port 8765
```

打开 http://localhost:8765

## 部署到公网

### 方式一：Render（推荐，免费档）

1. 把 `roundtable-web` 推到 GitHub
2. 登录 [Render](https://render.com) → New → Web Service → 选仓库
3. Runtime 选 **Docker**
4. 环境变量添加：
   - `OPENAI_API_KEY` = 你的 sk-...
   - `RATE_LIMIT_PER_HOUR` = 8（防刷）
5. Deploy

或用 `render.yaml` Blueprint 一键部署。

### 方式二：Railway / Fly.io / 自己的 VPS

```bash
docker build -t roundtable-web .
docker run -p 8765:8765 \
  -e OPENAI_API_KEY="sk-..." \
  -e RATE_LIMIT_PER_HOUR=10 \
  roundtable-web
```

### 方式三：任意 Python 主机

```bash
export OPENAI_API_KEY="sk-..."
export PORT=8765
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 公网部署必填 | 服务端 Key，访客无需知道 |
| `DEFAULT_MODEL` | 否 | 默认 `gpt-4o-mini` |
| `RATE_LIMIT_PER_HOUR` | 否 | 每 IP 每小时上限，默认 10 |
| `ALLOW_CLIENT_API_KEY` | 否 | `true` 时允许访客自带 Key |

## 技术说明

- 人物设定：`data/masters.json` + `data/prompts.json`（内置，不依赖 nuwa）
- 后端：FastAPI + OpenAI API
- 前端：静态 HTML/CSS/JS

## 费用控制建议

1. 用 `gpt-4o-mini` 而非 gpt-4o
2. 设置 `RATE_LIMIT_PER_HOUR=5~10`
3. 监控 OpenAI 用量仪表盘
4. 可选：加 Cloudflare 或简单访问密码（自行扩展）
