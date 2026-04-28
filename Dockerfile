FROM python:3.12-slim

WORKDIR /app

# Install system deps + Node.js (for frontend build)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY frontend/package*.json frontend/
RUN cd frontend && npm ci --silent

COPY frontend/ frontend/
RUN cd frontend && npm run build

# Application source
COPY . .

ENV PLCT_DB_PATH=/data/app.db
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
