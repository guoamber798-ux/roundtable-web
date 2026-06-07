#!/bin/bash
# 一键：创建 GitHub 仓库 → 推送 → 触发 Render 部署说明
# 用法：
#   export GITHUB_TOKEN="ghp_..."
#   export OPENAI_API_KEY="sk-..."
#   bash scripts/deploy-all.sh

set -euo pipefail
cd "$(dirname "$0")/.."

REPO_NAME="${REPO_NAME:-roundtable-web}"
GITHUB_USER="${GITHUB_USER:-guoamber798-ux}"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "❌ 请设置 GITHUB_TOKEN"
  echo "   GitHub → Settings → Developer settings → Personal access tokens"
  echo "   权限：repo（完整仓库权限）"
  exit 1
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "⚠️  未设置 OPENAI_API_KEY，Render 部署后需在 Dashboard 手动添加"
fi

echo ">>> 1/3 创建 GitHub 仓库 ${GITHUB_USER}/${REPO_NAME} ..."
CREATE_RESP=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/user/repos" \
  -d "{\"name\":\"${REPO_NAME}\",\"private\":false,\"description\":\"思维圆桌 Web\"}")

HTTP_CODE=$(echo "$CREATE_RESP" | tail -1)
BODY=$(echo "$CREATE_RESP" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
  echo "✓ 仓库已创建"
elif [ "$HTTP_CODE" = "422" ]; then
  echo "✓ 仓库已存在，继续推送"
else
  echo "❌ 创建仓库失败 (HTTP $HTTP_CODE)"
  echo "$BODY" | head -5
  exit 1
fi

REMOTE="https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"

echo ">>> 2/3 推送到 GitHub ..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
git push "https://${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git" main --force

echo "✓ 代码已推送: https://github.com/${GITHUB_USER}/${REPO_NAME}"

echo ""
echo ">>> 3/3 Render 部署"
echo ""
echo "请打开（已关联 GitHub 后一键部署）："
echo "  https://dashboard.render.com/select-repo?type=web"
echo ""
echo "选择仓库: ${REPO_NAME}"
echo "Runtime: Docker"
echo "环境变量:"
echo "  OPENAI_API_KEY = (你的 sk-...)"
echo "  DEFAULT_MODEL = gpt-4o-mini"
echo "  RATE_LIMIT_PER_HOUR = 8"
echo ""

if [ -n "${RENDER_API_KEY:-}" ]; then
  echo "检测到 RENDER_API_KEY，尝试通过 API 创建服务..."
  # Render 需先在 Dashboard 绑定 GitHub，API 创建较复杂，此处留扩展
fi

echo "完成！仓库地址: https://github.com/${GITHUB_USER}/${REPO_NAME}"
