# TopTalk × 发卡平台对接指南

## 核心原理

TopTalk **不会自动识别**发卡软件里随便生成的字符串。

只有当卡密**已经登记在 TopTalk 数据库**里，用户才能在网站「兑换口令」成功。

```
发卡软件生成卡密 → 同步到 TopTalk → 用户购买拿到卡密 → 来网站兑换 → 获得领晤次数
```

---

## 独角数卡专用部署包

已为你准备好完整发卡网目录：`/Users/Amber/dujiaoka-shop/`

包含 Docker 一键部署、TopTalk 卡密生成脚本、支付配置教程。详见 **`dujiaoka-shop/DUJIAOKA.md`**。

---

## 推荐方案 A：TopTalk 生成，导入发卡网（最简单）

适合：独角数卡、晴玖发卡、萌次元等支持「批量导入卡密」的平台。

### 第 1 步：在 TopTalk 批量生成卡密

```bash
curl -X POST https://你的域名/api/admin/codes/generate \
  -H "Content-Type: application/json" \
  -d '{
    "admin_secret": "你的ADMIN_SECRET",
    "count": 100,
    "credits": 5,
    "prefix": "TT"
  }'
```

返回示例：

```json
{
  "ok": true,
  "count": 100,
  "credits": 5,
  "codes": [
    "TT-A1B2C3D4E5F67890",
    "TT-FEDCBA0987654321"
  ]
}
```

### 第 2 步：导入发卡网

1. 在发卡网新建商品，例如「TopTalk 领晤 5 次」
2. 选择「卡密发货」
3. 把上一步的 `codes` 列表粘贴进卡密库存（一行一个）
4. 配置微信/支付宝收款

### 第 3 步：用户购买流程

```
用户付款 → 发卡网自动发出 TT-XXXX 卡密 → 用户注册 TopTalk → 兑换口令 → 成功
```

每张卡密 `max_uses=1`，只能被一个人兑换一次。

---

## 方案 B：发卡网生成，再导入 TopTalk

适合：卡密已经在发卡软件里生成好了。

```bash
curl -X POST https://你的域名/api/admin/codes/batch \
  -H "Content-Type: application/json" \
  -d '{
    "admin_secret": "你的ADMIN_SECRET",
    "codes": [
      "a68008ad795a4bdf800f3c6677a3b65b",
      "f3e2d1c0b9a88776655443322110099"
    ],
    "credits": 10,
    "max_uses": 1
  }'
```

把发卡网里**还没卖出去**的卡密批量导入 TopTalk，再上架销售。

---

## 方案 C：API 自动对接（高级）

适合：发卡平台支持「API 对接发货 / Webhook 回调」。

### 配置

在 Render 环境变量添加：

```
FAKA_WEBHOOK_SECRET=一段随机密钥
```

### 发卡网发货时调用

```
POST https://你的域名/api/webhooks/faka
Content-Type: application/json

{
  "webhook_secret": "你的FAKA_WEBHOOK_SECRET",
  "code": "买家拿到的卡密",
  "credits": 5,
  "order_id": "发卡网订单号"
}
```

TopTalk 收到后自动把卡密登记进数据库，用户即可兑换。

### 可选签名校验

若担心伪造请求，可附带 `signature`：

```
signature = HMAC-SHA256(FAKA_WEBHOOK_SECRET, "卡密|次数|订单号")
```

例如卡密 `ABC123`、5 次、订单 `ORDER001`：

```
payload = "ABC123|5|ORDER001"
signature = hmac_sha256(FAKA_WEBHOOK_SECRET, payload) 的 hex 值
```

---

## 商品对应关系建议

| 发卡网商品名 | credits 值 | 说明 |
|-------------|-----------|------|
| TopTalk 体验包 | 1 | 试玩 |
| TopTalk 标准包 | 5 | 主力 SKU |
| TopTalk 专业包 | 20 | 重度用户 |

不同商品导入/生成时设置不同的 `credits` 即可。

---

## 常见问题

**Q：用户说口令无效？**
- 卡密还没导入 TopTalk
- 卡密已被别人兑换过（一卡一人）
- 用户输入有空格，网站会自动去空格并转大写

**Q：发卡网和 TopTalk 的卡密必须一样吗？**
- 是的，买家在发卡网拿到的字符串，必须和 TopTalk 数据库里登记的完全一致。

**Q：JWT_SECRET / ADMIN_SECRET 要给买家吗？**
- 不要。这些是服务器内部密钥。买家只需要发卡网发给他的卡密。
