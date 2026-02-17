"""
MonedaValor API — Backend para exponer datos de Azure SQL a SAP.

Endpoints:
    GET /api/moneda-valor          — Lista todas las monedas (filtro opcional por tipo_moneda)
    GET /api/moneda-valor/{id}     — Obtiene una moneda por Id
    GET /health                    — Health check
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from .config import get_settings
from .database import get_db_connection, test_connection
from .models import MonedaValor, MonedaValorListResponse, HealthResponse, ErrorResponse
from .auth import verify_api_key

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="API REST para exponer la tabla dbo.MonedaValor de Azure SQL. Diseñada para ser consumida por SAP.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permitir acceso desde SAP y otros orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------------------------
@app.get(
    "/",
    tags=["Root"],
    summary="Información de la API",
)
async def root():
    """Retorna información básica de la API."""
    return {
        "nombre": settings.APP_TITLE,
        "version": settings.APP_VERSION,
        "descripcion": "API REST para exponer la tabla dbo.MonedaValor de Azure SQL",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "endpoints": {
            "listar": "/api/moneda-valor",
            "obtener": "/api/moneda-valor/{id}",
        },
    }


# ---------------------------------------------------------------------------
# Health Check (sin autenticación)
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Verificar estado de la API y la base de datos",
)
async def health_check():
    """Retorna el estado de la API y la conexión a la base de datos."""
    db_ok = test_connection()
    return HealthResponse(
        status="healthy",
        database="connected" if db_ok else "disconnected",
    )


# ---------------------------------------------------------------------------
# GET /api/moneda-valor  —  Listar monedas
# ---------------------------------------------------------------------------
@app.get(
    "/api/moneda-valor",
    response_model=MonedaValorListResponse,
    tags=["MonedaValor"],
    summary="Listar todas las monedas",
    responses={401: {"model": ErrorResponse}},
)
async def list_moneda_valor(
    tipo_moneda: Optional[str] = Query(
        None,
        description="Filtrar por tipo de moneda (ej: USD, EUR, MXN)",
        example="USD",
    ),
    _api_key: str = Depends(verify_api_key),
):
    """
    Retorna todas las filas de la tabla dbo.MonedaValor.

    - Si se envía el parámetro `tipo_moneda`, filtra por ese tipo.
    - Requiere header `X-API-Key` con una key válida.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if tipo_moneda:
                cursor.execute(
                    "SELECT Id, TipoMoneda, Valor FROM dbo.MonedaValor WHERE TipoMoneda = ?",
                    (tipo_moneda.strip(),),
                )
            else:
                cursor.execute("SELECT Id, TipoMoneda, Valor FROM dbo.MonedaValor")

            rows = cursor.fetchall()

            data = [
                MonedaValor(
                    id=row.Id,
                    tipo_moneda=row.TipoMoneda.strip(),
                    valor=row.Valor,
                )
                for row in rows
            ]

            return MonedaValorListResponse(count=len(data), data=data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la base de datos: {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /api/moneda-valor/{id}  —  Obtener por Id
# ---------------------------------------------------------------------------
@app.get(
    "/api/moneda-valor/{id}",
    response_model=MonedaValor,
    tags=["MonedaValor"],
    summary="Obtener una moneda por su Id",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_moneda_valor(
    id: int,
    _api_key: str = Depends(verify_api_key),
):
    """
    Retorna una fila de la tabla dbo.MonedaValor por su Id.

    - Requiere header `X-API-Key` con una key válida.
    - Retorna 404 si el Id no existe.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Id, TipoMoneda, Valor FROM dbo.MonedaValor WHERE Id = ?",
                (id,),
            )
            row = cursor.fetchone()

            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"MonedaValor con Id={id} no encontrada.",
                )

            return MonedaValor(
                id=row.Id,
                tipo_moneda=row.TipoMoneda.strip(),
                valor=row.Valor,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la base de datos: {str(e)}",
        )
