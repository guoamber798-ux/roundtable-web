# 公网部署指南（Render · 5 分钟）

## 第一步：推到 GitHub

```bash
cd /Users/Amber/roundtable-web
git add -A && git commit -m "思维圆桌 Web 初版"

# 在 github.com 新建空仓库 roundtable-web，然后：
git remote add origin https://github.com/你的用户名/roundtable-web.git
git branch -M main
git push -u origin main
```

## 第二步：Render 部署

1. 打开 https://render.com 注册/登录（可用 GitHub 登录）
2. **New +** → **Web Service**
3. 连接你的 `roundtable-web` 仓库
4. 设置：
   - **Runtime**: Docker
   - **Instance**: Free
5. **Environment Variables** 添加：

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | `sk-...`（你的 Key，之后可随时在 Dashboard 改） |
| `DEFAULT_MODEL` | `gpt-4o-mini` |
| `RATE_LIMIT_PER_HOUR` | `8` |

6. 点击 **Create Web Service**，等 3–5 分钟

7. 得到公网地址，形如：`https://roundtable-web-xxxx.onrender.com`

## 第三步：更换 API Key

Render Dashboard → 你的服务 → **Environment** → 改 `OPENAI_API_KEY` → **Save Changes**（自动重新部署）

## 费用

- Render 免费档：服务 15 分钟无访问会休眠，首次打开需等 ~30 秒唤醒
- OpenAI：每次圆桌约 ¥0.1–0.3（gpt-4o-mini）
