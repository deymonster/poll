#!/bin/bash

set -e


alembic upgrade head


if [[ DEBUG -eq 0 ]]; then
  echo "Use production settings"
  uvicorn main:app --host 0.0.0.0 --port 5000

else
  echo "Use development settings"
  uvicorn main:app --host 0.0.0.0 --port 5000 --reload
fi