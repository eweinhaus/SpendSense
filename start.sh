#!/bin/bash
# Startup script for Render deployment
export PYTHONPATH=/opt/render/project/src:$PYTHONPATH
cd /opt/render/project/src
exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT

