# Guía de Aprendizaje en Profundidad: MonedaValor API

Este documento explica **línea por línea** y **archivo por archivo** todo el código implementado. El objetivo es que entiendas no solo *qué* hace el código, sino *por qué* se escribió así y qué conceptos de Python + FastAPI + Azure hay detrás.

---

## 1. El Corazón del Proyecto (`requirements.txt`)

Este archivo le dice a Python (y a Azure) qué librerías externas necesitamos.

```text
fastapi==0.115.0      # Framework web moderno y rapidísimo para APIs
uvicorn==0.30.0       # Servidor web (ASGI) que "ejecuta" FastAPI
pyodbc==5.1.0         # Driver estándar para conectar Python con SQL Server / Azure SQL
pydantic-settings     # Manejo robusto de configuración y variables de entorno
python-dotenv         # Lee archivos .env (para desarrollo local)
```

**Concepto Clave**: Sin este archivo, el código fallaría en la primera línea porque no encontraría `fastapi` ni `pyodbc`.

---

## 2. Configuración (`app/config.py`)

Aquí centralizamos toda la configuración. Si cambia la base de datos o la clave, solo tocamos aquí (o las variables de entorno), nunca el código principal.

```python
from pydantic_settings import BaseSettings  # Clase base para manejar config
from functools import lru_cache             # Para optimizar (cache)

class Settings(BaseSettings):
    """
    Define qué variables necesitamos. Pydantic las busca automáticamente
    en las variables de entorno del sistema o en el archivo .env.
    """
    
    # Variables obligatorias (si faltan, la app no arranca)
    DB_SERVER: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"  # Valor por defecto

    API_KEY: str  # La contraseña para que SAP nos hable

    # Metadatos de la API
    APP_TITLE: str = "MonedaValor API"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"          # Busca en .env si existe
        env_file_encoding = "utf-8"

@lru_cache()  # Decorador de optimización
def get_settings() -> Settings:
    """
    Crea la configuración UNA sola vez y la reutiliza.
    Así no leemos el archivo .env 100 veces por segundo.
    """
    return Settings()
```

---

## 3. Conexión a Base de Datos (`app/database.py`)

El puente entre Python y Azure SQL.

```python
import pyodbc
from contextlib import contextmanager  # Herramienta mágica para usar "with"
from .config import get_settings       # Importamos nuestra config

def get_connection_string() -> str:
    """Fabrica el texto largo que pyodbc necesita para conectar."""
    settings = get_settings()
    # f-string: forma moderna de insertar variables en texto
    return (
        f"DRIVER={{{settings.DB_DRIVER}}};"
        f"SERVER={settings.DB_SERVER};"
        f"DATABASE={settings.DB_NAME};"
        f"UID={settings.DB_USER};"
        f"PWD={settings.DB_PASSWORD};"
        f"Encrypt=yes;"                # Azure EXIGE encriptación
        f"TrustServerCertificate=no;"  # Seguridad extra
        f"Connection Timeout=30;"
    )

@contextmanager
def get_db_connection():
    """
    Esto es un Context Manager. Nos permite usar:
    
    with get_db_connection() as conn:
        ...Hacer cosas...
    
    Y cuando termine el bloque 'with', la conexión se cierra AUTOMÁTICAMENTE,
    incluso si hubo un error. ¡Crucial para no tumbar la base de datos!
    """
    conn = pyodbc.connect(get_connection_string())
    try:
        yield conn  # "Presta" la conexión al código que la pidió
    finally:
        conn.close()  # Se asegura de cerrarla siempre
```

---

## 4. Modelos de Datos (`app/models.py`)

Usamos **Pydantic** para definir la forma de nuestros datos. Esto garantiza que la API siempre responda con la estructura correcta (validación automática).

```python
from pydantic import BaseModel
from decimal import Decimal  # Usamos Decimal para dinero, float pierde precisión

class MonedaValor(BaseModel):
    """Define cómo se ve UNA fila de la tabla."""
    id: int
    tipo_moneda: str
    valor: Decimal

class MonedaValorListResponse(BaseModel):
    """
    Define la respuesta completa de la lista.
    Mejor práctica: Envolver la lista en un objeto 'data'
    para poder agregar metadatos (como 'count') en el futuro.
    """
    count: int
    data: list[MonedaValor]  # Lista de objetos MonedaValor
```

---

## 5. Seguridad (`app/auth.py`)

El portero de la discoteca.

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from .config import get_settings

# Le dice a Swagger UI que debe pedir un header llamado "X-API-Key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: str = Security(api_key_header),  # Inyecta el valor del header
) -> str:
    """
    Esta función se ejecuta ANTES que el endpoint.
    Si la clave está mal, lanza un error 401 y detiene todo.
    """
    if api_key is None:
        raise HTTPException(...)  # Error 401: Falta la clave

    settings = get_settings()
    if api_key != settings.API_KEY:
        raise HTTPException(...)  # Error 401: Clave incorrecta

    return api_key  # Si todo bien, deja pasar
```

---

## 6. La Aplicación Principal (`app/main.py`)

Donde todo se une.

```python
from fastapi import FastAPI, Depends, ...  # Importamos herramientas
from .database import get_db_connection    # Nuestra conexión
from .models import MonedaValor...         # Nuestros modelos
from .auth import verify_api_key           # Nuestro portero

# Inicializamos la app
app = FastAPI(...)

# Configuración CORS (Cross-Origin Resource Sharing)
# Permite que navegadores o apps externas (como un frontend React o SAP)
# hagan peticiones a nuestra API sin ser bloqueados.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir a todo el mundo (en prod podría restringirse)
    ...
)

# --- Endpoint 1: Health Check ---
@app.get("/health")
async def health_check():
    """
    Endpoint público (sin clave) para ver si la API vive.
    Útil para que Azure sepa si reiniciar el servidor.
    """
    ...

# --- Endpoint 2: Listar Monedas ---
@app.get(
    "/api/moneda-valor",
    response_model=MonedaValorListResponse,  # Valida que respondamos bien
)
async def list_moneda_valor(
    # Parámetro opcional (?tipo_moneda=USD)
    tipo_moneda: Optional[str] = Query(None),
    
    # Inyección de dependencia: ¡Aquí llamamos al portero!
    # Si verify_api_key falla, este código NUNCA se ejecuta.
    _api_key: str = Depends(verify_api_key),
):
    try:
        with get_db_connection() as conn:  # Abre conexión
            cursor = conn.cursor()

            # SQL Parametrizado: "?" evita inyección SQL. NUNCA concatenes strings.
            if tipo_moneda:
                cursor.execute(
                    "SELECT ... WHERE TipoMoneda = ?", 
                    (tipo_moneda.strip(),)
                )
            else:
                cursor.execute("SELECT ...")

            rows = cursor.fetchall()

            # Convertimos filas crudas de SQL a nuestros objetos Pydantic
            data = [
                MonedaValor(
                    id=row.Id, 
                    tipo_moneda=row.TipoMoneda.strip(), 
                    valor=row.Valor
                )
                for row in rows
            ]

            return MonedaValorListResponse(count=len(data), data=data)

    except Exception as e:
        # Si algo explota (DB caída), devolvemos 500
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 7. Despliegue (`Dockerfile` y `startup.sh`)

### `Dockerfile`
Es la receta de cocina para construir el servidor en la nube.
1.  Usa Python 3.11 liviano (`slim`).
2.  Instala herramientas de sistema (`curl`, `gcc`) necesarias para compilar drivers.
3.  **Instala el driver ODBC de Microsoft** (la parte más difícil, ya resuelta).
4.  Instala las librerías de `requirements.txt`.
5.  Copia el código y lanza el servidor.

### `startup.sh`
Comando que le dice a Azure cómo arrancar en producción.
```bash
gunicorn app.main:app ...
```
Usa `gunicorn` (Google Unicorn) como servidor de procesos robusto, que a su vez usa `uvicorn` (para la velocidad asíncrona). Es la combinación estándar industrial para Python.
