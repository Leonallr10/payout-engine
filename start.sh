#!/bin/bash

# Exit on error
set -e

echo "Starting Migrations..."
python manage.py migrate

echo "Collecting Static Files..."
python manage.py collectstatic --noinput

echo "Starting Celery Worker..."
# We use --pool=solo because Koyeb's Nano instance has limited RAM
celery -A core worker -l info --pool=solo &

echo "Starting Gunicorn..."
# Use PORT env var provided by Koyeb
gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000}
