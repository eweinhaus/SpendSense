#!/bin/bash
# Startup script for Render deployment
# Set PYTHONPATH to include src directory
export PYTHONPATH=/opt/render/project/src/src:$PYTHONPATH
# Change to project root (not src) so gunicorn can find the module
cd /opt/render/project/src
# Run gunicorn - it will find spendsense because PYTHONPATH includes src
exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT

