# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps: build tools + postgres libs (psycopg), plus curl for debugging/health
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 django

# Install Python deps first (better caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Prepare writable dirs (staticfiles is used by collectstatic, logs for FileHandler)
RUN mkdir -p /app/staticfiles /app/logs \
 && chown -R django:django /app

USER django

# Collect static at build-time for WhiteNoise manifest storage.
# This requires env vars that allow Django settings import:
# - SECRET_KEY can be dummy for collectstatic
# - DB env is not required for collectstatic unless your code hits DB at import time
ENV SECRET_KEY="build-time-secret-key" \
    DEBUG="False"

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# WSGI module is "conf.wsgi.application" as in your settings.
CMD ["gunicorn", "conf.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
