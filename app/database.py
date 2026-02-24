"""
Módulo de conexión a Azure SQL Database usando pyodbc con pool de conexiones.

El pool evita abrir una conexión nueva en cada request (costoso en tiempo y
recursos de Azure SQL). Las conexiones se reutilizan y se validan antes de
devolverse al caller.
"""

import pyodbc
import threading
import logging
from contextlib import contextmanager
from .config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pool de conexiones simple y thread-safe
# ---------------------------------------------------------------------------
_pool: list = []
_pool_lock = threading.Lock()
_MAX_POOL_SIZE = 5  # Máximo de conexiones simultáneas


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


def _is_connection_alive(conn: pyodbc.Connection) -> bool:
    """Verifica si una conexión del pool sigue activa."""
    try:
        conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return False


def _get_from_pool() -> pyodbc.Connection:
    """
    Intenta obtener una conexión reutilizable del pool.
    Si el pool está vacío o todas las conexiones están muertas, crea una nueva.
    """
    with _pool_lock:
        while _pool:
            conn = _pool.pop()
            if _is_connection_alive(conn):
                logger.debug("Conexión reutilizada del pool.")
                return conn
            else:
                logger.debug("Conexión muerta descartada del pool.")
                try:
                    conn.close()
                except Exception:
                    pass

    # No había conexiones válidas → crear una nueva
    logger.debug("Creando nueva conexión a la base de datos.")
    return pyodbc.connect(get_connection_string())


def _return_to_pool(conn: pyodbc.Connection) -> None:
    """Devuelve una conexión al pool si hay espacio; si no, la cierra."""
    with _pool_lock:
        if len(_pool) < _MAX_POOL_SIZE:
            _pool.append(conn)
            logger.debug("Conexión devuelta al pool.")
        else:
            conn.close()
            logger.debug("Pool lleno — conexión cerrada.")


# ---------------------------------------------------------------------------
# Context manager público (misma interfaz que antes)
# ---------------------------------------------------------------------------
@contextmanager
def get_db_connection():
    """
    Context manager para obtener una conexión del pool.
    Devuelve la conexión al pool automáticamente al salir del bloque.

    Uso (sin cambios respecto a la versión anterior):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dbo.MonedaValor")
    """
    conn = _get_from_pool()
    try:
        yield conn
    except Exception:
        # Si hubo un error, no devolver la conexión al pool (puede estar corrupta)
        try:
            conn.close()
        except Exception:
            pass
        raise
    else:
        _return_to_pool(conn)


def test_connection() -> bool:
    """Prueba la conexión a la base de datos. Retorna True si es exitosa."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception:
        return False
