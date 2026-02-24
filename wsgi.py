"""
ASGI entry point para Gunicorn con Uvicorn
FastAPI es ASGI, no WSGI
"""
from app.main import app
