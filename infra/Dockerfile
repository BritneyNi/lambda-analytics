# ─── Etapa 1: Dependencias ────────────────────────────────────────────────────
FROM python:3.11-slim AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para maximizar caché de capas
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# ─── Etapa 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias compiladas de la etapa anterior
COPY --from=deps /install /usr/local

# Crear usuario no-root
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

# Copiar código fuente
COPY --chown=appuser:appgroup . .

# collectstatic usando config mínima sin base de datos (settings_build.py).
# Si el archivo no existe, el error se ignora y el static se recolecta en startup.
RUN DJANGO_SECRET_KEY=build-time-secret \
    python manage.py collectstatic --noinput \
      --settings=config.settings_build 2>/dev/null || \
    echo "collectstatic se ejecutará en startup"

USER appuser

EXPOSE $PORT

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/ || exit 1

CMD ["sh", "-c", \
    "python manage.py migrate --noinput && \
     gunicorn config.wsgi:application \
       --bind 0.0.0.0:${PORT} \
       --workers 4 \
       --worker-class gthread \
       --threads 2 \
       --worker-tmp-dir /dev/shm \
       --timeout 60 \
       --access-logfile - \
       --error-logfile -"]
