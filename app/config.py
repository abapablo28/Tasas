"""
Configuración de la aplicación.
Carga variables de entorno para la conexión a Azure SQL y autenticación.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración cargada desde variables de entorno o archivo .env"""

    # Azure SQL Database
    DB_SERVER: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"

    # Autenticación (opcional)
    API_KEY: str = ""

    # Aplicación
    APP_TITLE: str = "MonedaValor API"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Retorna la configuración cacheada (singleton)."""
    return Settings()
