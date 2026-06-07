#!/bin/bash
# 更新 Render 环境变量（Right Code + Claude）
# 用法：
#   export RENDER_API_KEY="rnd_..."
#   export RENDER_SERVICE_ID="srv_..."
#   export OPENAI_API_KEY="sk-..."
#   bash scripts/update-render-env.sh

set -euo pipefail

SERVICE_ID="${RENDER_SERVICE_ID:-}"
API_KEY="${RENDER_API_KEY:-}"
OPENAI_KEY="${OPENAI_API_KEY:-}"

if [ -z "$SERVICE_ID" ] || [ -z "$API_KEY" ]; then
  echo "══════════════════════════════════════════════════"
  echo "  手动在 Render Dashboard 添加以下环境变量："
  echo "══════════════════════════════════════════════════"
  echo ""
  echo "  OPENAI_API_KEY        = ${OPENAI_KEY:-（你的 Right Code sk-密钥）}"
  echo "  DEFAULT_MODEL         = claude-sonnet-4-5-20250929"
  echo "  API_PROVIDER          = anthropic"
  echo "  ANTHROPIC_BASE_URL    = https://www.right.codes/claude"
  echo ""
  echo "  路径：Render Dashboard → roundtable-web → Environment"
  echo "  改完后点 Save Changes，等待自动重新部署"
  echo ""
  echo "  若要用 API 自动更新，请设置："
  echo "    export RENDER_API_KEY=rnd_..."
  echo "    export RENDER_SERVICE_ID=srv_..."
  echo "    export OPENAI_API_KEY=sk-..."
  exit 0
fi

if [ -z "$OPENAI_KEY" ]; then
  echo "❌ 请设置 OPENAI_API_KEY"
  exit 1
fi

BODY=$(cat <<EOF
[
  {"key":"OPENAI_API_KEY","value":"${OPENAI_KEY}"},
  {"key":"DEFAULT_MODEL","value":"claude-sonnet-4-5-20250929"},
  {"key":"API_PROVIDER","value":"anthropic"},
  {"key":"ANTHROPIC_BASE_URL","value":"https://www.right.codes/claude"}
]
EOF
)

curl -s -X PUT \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  "https://api.render.com/v1/services/${SERVICE_ID}/env-vars" \
  -d "$BODY" | python3 -m json.tool 2>/dev/null || echo "✅ 已提交更新请求"

echo ""
echo "Render 正在重新部署，约 3–5 分钟完成。"
