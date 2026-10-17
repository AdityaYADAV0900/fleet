# ==============================================================================
# AeroPulse - Multi-Stage Dockerfile (Frontend SPA + Python Backend)
# ==============================================================================

# --- Stage 1: Build Frontend Assets (React + Vite + TypeScript) ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Production Python Backend Runtime ---
FROM python:3.11-slim

# Install system libraries needed by LightGBM, scientific packages, and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade packaging tools and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code and modules
COPY backend/ ./backend/
COPY data_gen/ ./data_gen/
COPY ml/ ./ml/
COPY scripts/ ./scripts/
COPY database/ ./database/
COPY alembic.ini .
COPY pyproject.toml .

# Copy pre-compiled frontend SPA assets from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure Python modules are accessible on PYTHONPATH
ENV PYTHONPATH=/app/backend:/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

EXPOSE 8000

# Run automated database migrations, data seeding, scoring, and start FastAPI
CMD ["python", "scripts/start_cloud.py"]
