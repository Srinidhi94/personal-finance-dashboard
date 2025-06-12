#!/bin/bash
set -e

echo "Starting Personal Finance Dashboard..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "Database is ready!"

# Set environment variables for Flask
export FLASK_APP=app.py

# Check if we're in development or production mode
if [ "${FLASK_ENV}" = "development" ]; then
    echo "Starting in development mode..."
    python app.py
else
    echo "Starting in production mode with gunicorn..."
    exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --threads 4 --timeout 120 app:app
fi 