# TopTalk领晤 · 公网部署指南（Render）

## 第一步：推到 GitHub

```bash
cd /Users/Amber/roundtable-web
git add -A && git commit -m "TopTalk领晤：账户+口令体系"
git push origin main
```

仓库：https://github.com/guoamber798-ux/roundtable-web

## 第二步：Render 部署

1. 打开 https://render.com 登录
2. **New +** → **Web Service** → 连接 `roundtable-web` 仓库
3. **Runtime**: Docker，**Instance**: Free
4. **Environment Variables**：

| Key | Value | 说明 |
|-----|-------|------|
| `OPENAI_API_KEY` | `sk-...` | 你的 Key，所有用户领晤计费走这里 |
| `JWT_SECRET` | 随机 32+ 字符 | 登录令牌签名，生产环境务必随机 |
| `ADMIN_SECRET` | 随机字符串 | 创建口令用的管理员密钥 |
| `INITIAL_CODES` | `TOPTALK-TEST:3` | 可选，启动时预置测试口令 |
| `DEFAULT_MODEL` | `gpt-4o-mini` | 可选 |
| `RATE_LIMIT_PER_HOUR` | `20` | 可选，防刷 |

5. **Create Web Service**，等待 3–5 分钟

6. 访问 `https://你的服务.onrender.com`

## 第三步：创建售卖口令

部署完成后，用 curl 创建口令（把域名和 `ADMIN_SECRET` 换成你的）：

```bash
curl -X POST https://你的服务.onrender.com/api/admin/codes \
  -H "Content-Type: application/json" \
  -d '{"admin_secret":"你的ADMIN_SECRET","code":"VIP-2024","credits":10,"max_uses":500}'
```

把 `VIP-2024` 发给购买用户，他们在网站注册后点击「兑换口令」即可。

## 用户使用流程

1. 打开网站 → **注册**账户
2. 点击 **兑换口令** → 输入购买的口令
3. 右上角显示剩余次数（如 `10 次`）
4. 选择 2–4 位大师 → 输入问题 → **开始领晤**（扣 1 次）

## 更换 API Key

Render Dashboard → 你的服务 → **Environment** → 改 `OPENAI_API_KEY` → **Save Changes**

## 注意事项

- **Render 免费档**：15 分钟无访问会休眠，首次打开需等约 30 秒唤醒
- **SQLite 数据**：免费档重启可能丢失用户/口令数据；如需持久化可升级 Render Disk 或换外部数据库
- **费用**：每次领晤约 ¥0.1–0.3（gpt-4o-mini），由你的 `OPENAI_API_KEY` 承担
