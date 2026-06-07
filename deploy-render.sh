#!/bin/bash
# Render 公网部署辅助脚本
set -e
cd "$(dirname "$0")"

echo "════════════════════════════════════════"
echo "  思维圆桌 · Render 公网部署"
echo "════════════════════════════════════════"
echo ""
echo "本脚本无法代替你登录 Render，但会检查本地准备情况。"
echo ""

# 检查 git
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "❌ 未初始化 git"
  exit 1
fi
echo "✓ Git 仓库已就绪"

# 检查是否已推送到 remote
if git remote get-url origin >/dev/null 2>&1; then
  echo "✓ Remote: $(git remote get-url origin)"
  echo ""
  echo "下一步："
  echo "  1. git push -u origin main"
  echo "  2. 打开 https://dashboard.render.com/select-repo?type=web"
  echo "  3. 选择 roundtable-web 仓库，Runtime 选 Docker"
  echo "  4. 添加环境变量 OPENAI_API_KEY=sk-..."
  echo "  5. Deploy"
else
  echo ""
  echo "尚未关联 GitHub，请按顺序执行："
  echo ""
  echo "  # 1. 在 github.com 新建空仓库 roundtable-web"
  echo "  git remote add origin https://github.com/你的用户名/roundtable-web.git"
  echo "  git push -u origin main"
  echo ""
  echo "  # 2. 打开 Render 部署"
  echo "  open https://dashboard.render.com/select-repo?type=web"
  echo ""
  echo "  # 3. 环境变量（Deploy 前添加）"
  echo "  OPENAI_API_KEY    = sk-你的密钥"
  echo "  DEFAULT_MODEL     = gpt-4o-mini"
  echo "  RATE_LIMIT_PER_HOUR = 8"
fi

echo ""
echo "更换 Key：Render Dashboard → Environment → 改 OPENAI_API_KEY → Save"
echo "详细说明见 DEPLOY.md"
echo ""
