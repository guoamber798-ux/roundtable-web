#!/bin/bash
set -e
cd "$(dirname "$0")"
pip install -q -r requirements.txt
echo ">>> 思维圆桌启动中 http://localhost:8765"
echo ">>> 提示：设置 OPENAI_API_KEY 后访客无需自备 Key"
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8765
