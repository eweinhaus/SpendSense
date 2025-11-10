#!/bin/bash
# Startup script for Render deployment
# Set PYTHONPATH to include the repository's src directory (module lives in src/spendsense)
export PYTHONPATH=/opt/render/project/src/src:$PYTHONPATH
# Change to repository root
cd /opt/render/project/src
# Run gunicorn - it will find spendsense because PYTHONPATH includes src
exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT

