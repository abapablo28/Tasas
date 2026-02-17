"""
Módulo de autenticación por API Key.
SAP debe enviar el header X-API-Key en cada request protegido.
"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from .config import get_settings

# Definir el esquema de seguridad — SAP envía la key en este header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str = Security(api_key_header),
) -> str:
    """
    Dependency de FastAPI que valida la API Key.

    Uso en un endpoint:
        @app.get("/ruta", dependencies=[Depends(verify_api_key)])

    Retorna la API key si es válida, lanza 401 si no.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Envía el header X-API-Key.",
        )

    settings = get_settings()
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida.",
        )

    return api_key
