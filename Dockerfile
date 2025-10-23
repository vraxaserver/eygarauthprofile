# ---------- Builder stage: build wheels ----------
FROM python:3.12-slim-bullseye AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    python3-dev \
    libffi-dev \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

COPY . /build/app


# ---------- Runtime stage: minimal runtime ----------
FROM python:3.12-slim-bullseye AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=conf.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tini \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

ARG APP_USER=appuser
ARG APP_UID=1000
RUN groupadd -g ${APP_UID} ${APP_USER} \
 && useradd -m -u ${APP_UID} -g ${APP_UID} ${APP_USER}

COPY --from=builder /wheels /wheels
COPY --from=builder --chown=${APP_USER}:${APP_USER} /build/app /app

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --no-index --find-links /wheels -r requirements.txt \
    || /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
 && rm -rf /wheels /root/.cache/pip

# 👇 Add this: collect static files during image build
RUN /opt/venv/bin/python manage.py collectstatic --noinput

# Copy entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN chown -R ${APP_USER}:${APP_USER} /app

USER root

EXPOSE 8000
STOPSIGNAL SIGTERM

# ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]

# Gunicorn serves via Whitenoise (no need for nginx if using Whitenoise)
CMD ["gunicorn", "conf.asgi:application", "-w", "3", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--log-level", "info"]
