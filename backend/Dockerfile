FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN pip install uv && uv sync

COPY backend/ ./backend/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
