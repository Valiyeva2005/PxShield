# =========================================
# PixelShield – Dockerfile
# Multi-stage build for a minimal, secure image
# =========================================

# ---------- Build stage ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Runtime stage ----------
FROM python:3.12-slim AS runtime

# Security: run as non-root
RUN groupadd -r pixelshield && useradd -r -g pixelshield pixelshield

WORKDIR /app

# Runtime OS dependencies for OpenCV + Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=pixelshield:pixelshield . /app/

# Create required directories
RUN mkdir -p /app/output /app/logs \
    && chown -R pixelshield:pixelshield /app/output /app/logs

# Switch to non-root user
USER pixelshield

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

ENTRYPOINT ["python", "pixelshield.py"]
CMD ["--help"]
