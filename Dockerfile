# Multi-purpose production Dockerfile for Supply Chain Disruption Assistant
FROM python:3.12-slim

# Enforce UTF-8 and offline resilience flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8 \
    LITELLM_LOCAL_MODEL_COST_MAP=True \
    LITELLM_DISABLE_TELEMETRY=True

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt requirements-eval.txt ./

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Expose FastAPI (8000) and Streamlit (8501) ports
EXPOSE 8000 8501

# Healthcheck against FastAPI endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: launch FastAPI service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
