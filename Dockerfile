FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data/ ./data/
COPY backend/ ./backend/
COPY frontend/ ./frontend/

ENV PORT=8765
EXPOSE 8765

WORKDIR /app/backend
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
