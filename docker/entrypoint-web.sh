#!/usr/bin/env sh
set -e

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Collecting static (noop by default)..."
uv run python manage.py collectstatic --noinput || true

echo "Starting gunicorn..."
exec uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120

