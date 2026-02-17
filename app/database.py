"""
Módulo de conexión a Azure SQL Database usando pyodbc.
"""

import pyodbc
from contextlib import contextmanager
from .config import get_settings


def get_connection_string() -> str:
    """Construye el string de conexión para Azure SQL."""
    settings = get_settings()
    return (
        f"DRIVER={{{settings.DB_DRIVER}}};"
        f"SERVER={settings.DB_SERVER};"
        f"DATABASE={settings.DB_NAME};"
        f"UID={settings.DB_USER};"
        f"PWD={settings.DB_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
    )


@contextmanager
def get_db_connection():
    """
    Context manager para obtener una conexión a la base de datos.
    Cierra la conexión automáticamente al salir del bloque.

    Uso:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dbo.MonedaValor")
    """
    conn = pyodbc.connect(get_connection_string())
    try:
        yield conn
    finally:
        conn.close()


def test_connection() -> bool:
    """Prueba la conexión a la base de datos. Retorna True si es exitosa."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception:
        return False
