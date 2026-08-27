# Aegis 2.0 Production Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code to /app/backend
COPY backend/ /app/backend/

# Set Python path so it resolves 'backend.app' imports
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Use Render's injected $PORT variable, fallback to 8000
CMD sh -c "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
