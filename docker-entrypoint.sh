#!/usr/bin/env bash
set -euo pipefail

# Number of retries for DB migrations
: "${MIGRATE_RETRIES:=5}"
: "${MIGRATE_RETRY_DELAY:=3}"  # seconds between retries

echo "Starting entrypoint: $(date)"

# Activate venv if exists
if [ -d "/venv" ]; then
  # shellcheck disable=SC1091
  source /venv/bin/activate
fi

# Optional: collectstatic if desired (enable ENABLE_COLLECTSTATIC=1)
if [ "${ENABLE_COLLECTSTATIC:-0}" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Entrypoint finished. Exec: $@"
# exec the container's main process (what's in CMD)
exec "$@"
