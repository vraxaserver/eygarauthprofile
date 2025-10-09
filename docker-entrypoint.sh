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

# Optional: allow disabling migrations via env var
if [ "${DISABLE_MIGRATIONS:-0}" = "1" ]; then
  echo "Migrations disabled by DISABLE_MIGRATIONS=1"
else
  echo "Running migrations (up to ${MIGRATE_RETRIES} attempts)..."
  attempt=1
  until python manage.py migrate --noinput; do
    if [ "$attempt" -ge "$MIGRATE_RETRIES" ]; then
      echo "Migrations failed after $attempt attempts. Exiting." >&2
      exit 1
    fi
    echo "Migrate attempt $attempt failed — retrying in ${MIGRATE_RETRY_DELAY}s..."
    attempt=$((attempt+1))
    sleep "${MIGRATE_RETRY_DELAY}"
  done
  echo "Migrations applied."

  # --- START: Load initial data only if the database is new ---
  # Check if any users already exist in the database.
  python manage.py loaddata data/accounts_data.json
  python manage.py loaddata data/eygarprofile_data.json
  # --- END: Load initial data ---
fi

# Optional: collectstatic if desired (enable ENABLE_COLLECTSTATIC=1)
if [ "${ENABLE_COLLECTSTATIC:-0}" = "1" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

# Run any extra management command passed via environment variable (optional)
if [ -n "${DJANGO_MANAGEMENT_COMMAND:-}" ]; then
  echo "Running custom management command: ${DJANGO_MANAGEMENT_COMMAND}"
  eval "python manage.py ${DJANGO_MANAGEMENT_COMMAND}"
fi

echo "Entrypoint finished. Exec: $@"
# exec the container's main process (what's in CMD)
exec "$@"