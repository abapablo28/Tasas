"""
Modelos Pydantic para la serialización de respuestas de la API.
"""

from pydantic import BaseModel
from decimal import Decimal


class MonedaValor(BaseModel):
    """Modelo que representa una fila de la tabla dbo.MonedaValor."""
    id: int
    tipo_moneda: str
    valor: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "tipo_moneda": "USD",
                "valor": 4150.25
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
