# Explicación del Código FastAPI y Recursos para Aprender

## ¿Qué hace tu código principal?

- Define una API REST con FastAPI para exponer datos de la tabla `dbo.MonedaValor` de Azure SQL.
- Usa autenticación por API Key para proteger los endpoints principales.
- Permite consultar todas las monedas o una moneda por ID.
- Incluye endpoints de salud (`/health`) y documentación interactiva (`/docs`).

## Estructura básica del código

```python
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from .config import get_settings
from .database import get_db_connection, test_connection
from .models import MonedaValor, MonedaValorListResponse, HealthResponse, ErrorResponse
from .auth import verify_api_key

settings = get_settings()
app = FastAPI(...)

app.add_middleware(CORSMiddleware, ...)

@app.get("/health")
async def health_check():
    ...

@app.get("/api/moneda-valor")
async def list_moneda_valor(..., _api_key: str = Depends(verify_api_key)):
    ...

@app.get("/api/moneda-valor/{id}")
async def get_moneda_valor(id: int, _api_key: str = Depends(verify_api_key)):
    ...
```

## ¿Cómo funciona la autenticación?
- La función `verify_api_key` revisa que el header `X-API-Key` sea igual a `sap_connect`.
- Si no es correcto, retorna un error 401 (no autorizado).
- Si es correcto, permite el acceso al endpoint.

## ¿Cómo se conecta a la base de datos?
- Usa la función `get_db_connection()` para abrir una conexión a Azure SQL.
- Ejecuta consultas SQL para obtener los datos de la tabla `MonedaValor`.

## ¿Cómo probar la API?
- Usa `/docs` para probar desde el navegador (con el botón Authorize para la API Key).
- Usa Postman, curl o extensiones de navegador para enviar la API Key en el header.

## Recursos para aprender FastAPI y APIs seguras

- [Documentación oficial de FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI Security (API Key)](https://fastapi.tiangolo.com/advanced/security/api-key/)
- [Curso gratuito de FastAPI (YouTube)](https://www.youtube.com/watch?v=7t2alSnE2-I)
- [Postman: cómo usar headers](https://learning.postman.com/docs/sending-requests/requests/#headers)
- [ModHeader: extensión para Chrome/Edge/Firefox](https://modheader.com/)
- [Video: FastAPI Security with API Key](https://www.youtube.com/watch?v=6Qmnh5C4Pmo)

---

¿Quieres ejemplos de código para otros casos o necesitas ayuda con otro tema de FastAPI?