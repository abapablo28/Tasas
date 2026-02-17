#!/bin/bash
# Script de inicio para Azure App Service
# Azure App Service ejecuta este script al iniciar la aplicación

gunicorn app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
