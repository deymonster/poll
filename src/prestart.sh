#!/bin/sh

echo "Running prestart script..."

echo "Setting permissions to media directory..."
chown -R ${UID}:${GID} /app/media

find /app/media -type d -exec chmod 775 {} \;
find /app/media -type f -exec chmod 664 {} \;

echo "Updating database..."

alembic upgrade head

echo "Starting application..."

