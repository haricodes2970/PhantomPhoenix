FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU wheel for reproducible, fast container builds
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements-api.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt -r requirements-ml.txt

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
