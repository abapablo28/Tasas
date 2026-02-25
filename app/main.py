"""
MonedaValor API — Backend para exponer datos de Azure SQL a SAP.

Endpoints:
    GET /api/moneda-valor                    — Lista todas las monedas (filtro opcional por instrumento)
    GET /api/moneda-valor/formato-sap       — Obtiene tasa en formato fixed-width para TBD4 SAP
    GET /api/moneda-valor/{instrumento}     — Obtiene una moneda por instrumento
    GET /health                             — Health check

NOTA: /formato-sap debe estar ANTES de /{instrumento} para evitar conflicto de rutas.
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status, Response
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime

from .config import get_settings
from .database import get_db_connection, test_connection
from .models import MonedaValor, MonedaValorListResponse, HealthResponse, ErrorResponse, TasaCambioSAP
# from .auth import verify_api_key  # Deshabilitado para pruebas con SAP

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
        "descripcion": "API REST para exponer la tabla dbo.MonedaValor de Azure SQL (nueva estructura)",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "endpoints": {
            "listar": "/api/moneda-valor",
            "obtener_por_instrumento": "/api/moneda-valor/{instrumento}",
            "formato_sap_tbd4": "/api/moneda-valor/formato-sap",
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
    ssinstrumnt: Optional[str] = Query(
        None,
        description="Filtrar por instrumento (ej: USDCOPTRM)",
        example="USDCOPTRM",
    ),
):
    """
    Retorna todas las filas de la tabla dbo.MonedaValor (nueva estructura).

    - Si se envía el parámetro `ssinstrumnt`, filtra por ese instrumento.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if ssinstrumnt:
                cursor.execute(
                    "SELECT SSINSTRUMNT, MIFEEDNAME, RATETYPE, TIMESTAMP_VALOR, CURRENCY FROM dbo.MonedaValor WHERE SSINSTRUMNT = ?",
                    (ssinstrumnt.strip(),),
                )
            else:
                cursor.execute("SELECT SSINSTRUMNT, MIFEEDNAME, RATETYPE, TIMESTAMP_VALOR, CURRENCY FROM dbo.MonedaValor")

            rows = cursor.fetchall()

            data = [
                MonedaValor(
                    ssinstrumnt=row.SSINSTRUMNT.strip(),
                    mifeedname=row.MIFEEDNAME.strip(),
                    ratetype=row.RATETYPE.strip(),
                    timestamp_valor=row.TIMESTAMP_VALOR,
                    currency=row.CURRENCY.strip(),
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
# GET /api/moneda-valor/formato-sap  —  Formato fixed-width para TBD4
# IMPORTANTE: debe estar ANTES de /{instrumento} para que FastAPI no lo
# capture como si fuera un instrumento llamado "formato-sap".
# ---------------------------------------------------------------------------
@app.get(
    "/api/moneda-valor/formato-sap",
    tags=["MonedaValor"],
    summary="Obtener tasa de cambio en formato SAP fixed-width para TBD4",
    description="Retorna una línea de texto plano de 237 caracteres formateada para el datafeed de SAP.",
    responses={
        200: {"content": {"text/plain": {}}, "description": "Línea de 237 caracteres"},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse}
    },
)
async def get_tasa_cambio_sap():
    """
    Retorna la tasa de cambio en formato fixed-width (238 caracteres) compatible con TBD4/RINID de SAP.
    
    Lee de la tabla MonedaValor (nueva estructura) y genera el formato SAP.
    
    Formato:
    - Pos 1-20: RINID1 (SSINSTRUMNT)
    - Pos 21-35: RINID2 (MIFEEDNAME)
    - Pos 36-50: SPRPTY (RATETYPE)
    - Pos 51-52: SSTATS (espacios = OK)
    - Pos 53-132: ERROR (80 espacios)
    - Pos 133-142: RSUPID (espacios)
    - Pos 143-152: RCONID (espacios)
    - Pos 153-157: RCONCN (espacios)
    - Pos 158-165: DATE (YYYYMMDD desde TIMESTAMP_VALOR)
    - Pos 166-171: TIME (HHMMSS desde TIMESTAMP_VALOR)
    - Pos 172-191: VALUE (valor desde TIMESTAMP_VALOR, alineado a derecha)
    - Pos 192-196: CURRENCY
    - Pos 197-201: MKIND (espacios)
    - Pos 202-208: CFFACT (espacios)
    - Pos 209-215: CTFACT (espacios)
    - Pos 216-227: UNAME (espacios)
    - Pos 228-237: RZUSATZ (espacios)
    - Pos 238: NEWLINE
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Buscar la primera fila de la tabla
            cursor.execute(
                "SELECT SSINSTRUMNT, MIFEEDNAME, RATETYPE, TIMESTAMP_VALOR, CURRENCY FROM dbo.MonedaValor ORDER BY TIMESTAMP_VALOR DESC"
            )
            row = cursor.fetchone()

            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se encontraron datos en la tabla MonedaValor.",
                )

            ssinstrumnt = row.SSINSTRUMNT.strip()
            mifeedname = row.MIFEEDNAME.strip()
            ratetype = row.RATETYPE.strip()
            currency = row.CURRENCY.strip()
            
            # Parsear TIMESTAMP_VALOR: formato es YYYYMMDDHHMMSS+valor
            # Ejemplo: 20260223140000+4235.500000
            timestamp_valor = row.TIMESTAMP_VALOR
            
            # Extraer fecha (primeros 8 caracteres)
            # Extraer hora (siguientes 6 caracteres)
            # El resto es el valor (con signo)
            if len(timestamp_valor) < 14:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Formato TIMESTAMP_VALOR inválido: {timestamp_valor}",
                )
            
            fecha_str = timestamp_valor[0:8]  # YYYYMMDD
            hora_str = timestamp_valor[8:14]  # HHMMSS
            valor_str_raw = timestamp_valor[14:]  # +4235.500000

            # Construir la línea con formato fixed-width (238 caracteres)
            # Pos 1-20: RINID1 (SSINSTRUMNT)
            rinid1 = ssinstrumnt.ljust(20)
            
            # Pos 21-35: RINID2 (MIFEEDNAME)
            rinid2 = mifeedname.ljust(15)
            
            # Pos 36-50: SPRPTY (RATETYPE)
            sprpty = ratetype.ljust(15)
            
            # Pos 51-52: SSTATS (OK)
            sstats = "  "  # 2 espacios
            
            # Pos 53-132: ERROR (80 espacios)
            error = " " * 80
            
            # Pos 133-142: RSUPID (10 espacios)
            rsupid = " " * 10
            
            # Pos 143-152: RCONID (10 espacios)
            rconid = " " * 10
            
            # Pos 153-157: RCONCN (5 espacios)
            rconcn = " " * 5
            
            # Pos 158-165: DATE
            date_val = fecha_str  # 8 caracteres
            
            # Pos 166-171: TIME
            time_val = hora_str   # 6 caracteres
            
            # Pos 172-191: VALUE (20 caracteres, alineado a derecha)
            valor_str = valor_str_raw.rjust(20)
            
            # Pos 192-196: CURRENCY
            currency_val = currency.ljust(5)
            
            # Pos 197-201: MKIND (5 espacios)
            mkind = " " * 5
            
            # Pos 202-208: CFFACT (7 espacios)
            cffact = " " * 7
            
            # Pos 209-215: CTFACT (7 espacios)
            ctfact = " " * 7
            
            # Pos 216-227: UNAME (12 espacios)
            uname = " " * 12
            
            # Pos 228-237: RZUSATZ (10 espacios)
            rzusatz = " " * 10
            
            # Ensamblar la línea completa (sin newline al final aún)
            linea = (rinid1 + rinid2 + sprpty + sstats + error + rsupid + 
                    rconid + rconcn + date_val + time_val + valor_str + currency_val + 
                    mkind + cffact + ctfact + uname + rzusatz)
            
            # Verificar que tiene exactamente 237 caracteres (sin el newline)
            if len(linea) != 237:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error en formato: se generaron {len(linea)} caracteres en lugar de 237.",
                )
            
            # Retornar texto plano sin el newline al final
            return PlainTextResponse(content=linea)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la base de datos: {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /api/moneda-valor/{instrumento}  —  Obtener por Instrumento
# IMPORTANTE: debe estar DESPUÉS de /formato-sap para evitar conflicto.
# ---------------------------------------------------------------------------
@app.get(
    "/api/moneda-valor/{instrumento}",
    response_model=MonedaValor,
    tags=["MonedaValor"],
    summary="Obtener una moneda por su instrumento",
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_moneda_valor(
    instrumento: str,
):
    """
    Retorna una fila de la tabla dbo.MonedaValor por su SSINSTRUMNT.

    - Retorna 404 si el instrumento no existe.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SSINSTRUMNT, MIFEEDNAME, RATETYPE, TIMESTAMP_VALOR, CURRENCY FROM dbo.MonedaValor WHERE SSINSTRUMNT = ?",
                (instrumento.strip(),),
            )
            row = cursor.fetchone()

            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Instrumento {instrumento} no encontrado.",
                )

            return MonedaValor(
                ssinstrumnt=row.SSINSTRUMNT.strip(),
                mifeedname=row.MIFEEDNAME.strip(),
                ratetype=row.RATETYPE.strip(),
                timestamp_valor=row.TIMESTAMP_VALOR,
                currency=row.CURRENCY.strip(),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar la base de datos: {str(e)}",
        )
