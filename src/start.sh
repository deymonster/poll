#!/bin/bash

set -e


alembic upgrade head

if [[ "$POPULATE_DB" = "true" ]]; then
  echo "Populating the database with fake data..."
  python populate_db.py
fi


if [[ DEBUG -eq 0 ]]; then
  echo "Use production settings"
  uvicorn main:app --host 0.0.0.0 --port 5000

else
  echo "Use development settings"
  uvicorn main:app --host 0.0.0.0 --port 5000 --reload
fi
