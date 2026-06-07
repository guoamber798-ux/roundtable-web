# TopTalk领晤

十五位大师参与的多轮深度领晤。**人物设定已内置**，访客无需安装 nuwa / Cursor Skill。

## 功能

- 用户注册 / 登录
- 兑换购买口令，获得领晤次数（每次讨论消耗 1 次）
- 15 位大师 face card，选 2–4 位参与
- 三轮：独立观点 → 交叉辩论 → 共识收敛
- 单次输出 ≤ 3500 字

## 关于 API Key（重要）

| 场景 | 谁需要 Key | 说明 |
|------|-----------|------|
| **公网部署** | **只有你（站长）** | 在服务器设 `OPENAI_API_KEY`，所有用户领晤都走你的 Key |
| 本地开发 | 你 | 设环境变量即可 |

**结论：访客不需要也不应填写 API Key。费用由站长承担，通过口令控制每人可用次数。**

单次领晤（4人×2轮+共识）用 `gpt-4o-mini` 约 **¥0.1–0.3**。

## 本地启动

```bash
cd roundtable-web
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."
export JWT_SECRET="dev-secret-change-me"
export ADMIN_SECRET="admin123"
export INITIAL_CODES="TOPTALK-TEST:3"

cd backend && uvicorn main:app --reload --port 8765
```

打开 http://localhost:8765 → 注册账户 → 兑换口令 `TOPTALK-TEST` → 开始领晤。

## 管理员：创建口令

```bash
curl -X POST http://localhost:8765/api/admin/codes \
  -H "Content-Type: application/json" \
  -d '{"admin_secret":"admin123","code":"VIP-001","credits":5,"max_uses":100}'
```

用户在前端点击「兑换口令」输入 `VIP-001` 即可获得 5 次领晤机会。

## 部署到公网

### 方式一：Render（推荐）

1. 把仓库推到 GitHub
2. [Render](https://render.com) → New → Web Service → 选仓库 → Runtime 选 **Docker**
3. 环境变量：

| Key | 说明 |
|-----|------|
| `OPENAI_API_KEY` | 你的 OpenAI Key（必填） |
| `JWT_SECRET` | 随机长字符串（必填） |
| `ADMIN_SECRET` | 管理员密钥，用于创建口令（必填） |
| `INITIAL_CODES` | 可选，如 `TOPTALK-TEST:3` |
| `DEFAULT_MODEL` | 可选，默认 `gpt-4o-mini` |
| `RATE_LIMIT_PER_HOUR` | 可选，默认 20 |

4. Deploy

详见 [DEPLOY.md](./DEPLOY.md)。

### 方式二：Docker

```bash
docker build -t toptalk .
docker run -p 8765:8765 \
  -e OPENAI_API_KEY="sk-..." \
  -e JWT_SECRET="..." \
  -e ADMIN_SECRET="..." \
  -e INITIAL_CODES="DEMO:5" \
  toptalk
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 是 | 服务端 Key，所有领晤计费走此 Key |
| `JWT_SECRET` | 是 | JWT 签名密钥 |
| `ADMIN_SECRET` | 是 | 创建口令接口的密钥 |
| `INITIAL_CODES` | 否 | 启动时预置口令，格式 `CODE:次数,CODE:次数` |
| `DEFAULT_MODEL` | 否 | 默认 `gpt-4o-mini` |
| `RATE_LIMIT_PER_HOUR` | 否 | 每 IP 每小时上限，默认 20 |
| `DATABASE_PATH` | 否 | SQLite 路径，默认 `./data/toptalk.db` |

## 技术说明

- 人物设定：`data/masters.json` + `data/prompts.json`（内置，不依赖 nuwa）
- 后端：FastAPI + SQLite + JWT + OpenAI API
- 前端：静态 HTML/CSS/JS

## 费用控制建议

1. 用 `gpt-4o-mini` 而非 gpt-4o
2. 通过口令控制每人领晤次数
3. 设置 `RATE_LIMIT_PER_HOUR=10~20`
4. 监控 OpenAI 用量仪表盘
