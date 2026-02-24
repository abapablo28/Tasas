"""
Modelos Pydantic para la serialización de respuestas de la API.
"""

from pydantic import BaseModel
from decimal import Decimal


class MonedaValor(BaseModel):
    """Modelo que representa una fila de la tabla dbo.MonedaValor (nueva estructura)."""
    ssinstrumnt: str
    mifeedname: str
    ratetype: str
    timestamp_valor: str
    currency: str

    class Config:
        json_schema_extra = {
            "example": {
                "ssinstrumnt": "USDCOPTRM",
                "mifeedname": "MIF",
                "ratetype": "MID",
                "timestamp_valor": "20260223140000+4235.500000",
                "currency": "COP"
            }
        }


class MonedaValorListResponse(BaseModel):
    """Respuesta con lista de monedas y conteo total."""
    count: int
    data: list[MonedaValor]


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str
    database: str


class ErrorResponse(BaseModel):
    """Respuesta de error."""
    detail: str


class TasaCambioSAP(BaseModel):
    """Formato fixed-width para TBD4/RINID de SAP (238 caracteres exactos)."""
    linea: str

    class Config:
        json_schema_extra = {
            "example": {
                "linea": "USDCOPTRM           MIF            MID                20260223140000+        4235.50000COP                                          "
            }
        }
