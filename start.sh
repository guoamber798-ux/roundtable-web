#!/bin/bash
set -e
cd "$(dirname "$0")"
pip install -q -r requirements.txt
if [ -f ".env" ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

PORT="${PORT:-8765}"
echo ">>> 思维圆桌启动中 http://localhost:$PORT"
if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "在这里填入你的-sk-密钥" ]; then
  echo ">>> ✓ 已加载 OPENAI_API_KEY（访客无需自备 Key）"
else
  echo ">>> ⚠ 请在 .env 中设置 OPENAI_API_KEY"
fi
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port "$PORT"
