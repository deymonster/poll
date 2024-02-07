#!/bin/bash

set -e


alembic upgrade head


if [[ DEBUG -eq 0 ]]; then
  echo "Use production settings"
  uvicorn new_main:main --host 0.0.0.0 --port 5000

else
  echo "Use development settings"
  uvicorn new_main:main --host 0.0.0.0 --port 5000 --reload
fi
