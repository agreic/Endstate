FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN pip install uv && uv sync && uv pip install "opik==1.9.98" "langchain-openai>=0.2.0"

COPY backend/ ./backend/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
