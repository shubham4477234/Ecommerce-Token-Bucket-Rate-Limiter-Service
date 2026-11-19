
# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip wheel \
       --no-cache-dir \
       --wheel-dir=/wheels \
       -r requirements.txt


# ==========================================
# STAGE 2: RUNTIME
# ==========================================
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user
RUN groupadd --system django \
    && useradd --system --gid django --create-home django

# Install dependencies
COPY --from=builder /wheels /wheels
COPY requirements.txt .

RUN python -m pip install --no-cache-dir --no-index \
    --find-links=/wheels \
    -r requirements.txt \
    && rm -rf /wheels

# Copy application source
COPY --chown=django:django . .

# Copy startup script
COPY --chown=django:django entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8000

USER django

# Only start Gunicorn
ENTRYPOINT ["/entrypoint.sh"]
