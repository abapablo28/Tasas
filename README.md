# MonedaValor API

API REST en Python (FastAPI) que expone la tabla `dbo.MonedaValor` de Azure SQL Database para consumo desde SAP.

## Requisitos

- Python 3.10+
- ODBC Driver 18 for SQL Server ([descargar aquí](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server))

## Configuración Local

### 1. Crear entorno virtual

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y completa con tus credenciales reales:

```bash
copy .env.example .env
```

Edita `.env`:
```env
DB_SERVER=sltrm.database.windows.net
DB_NAME=tu_base_de_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
API_KEY=tu_clave_secreta
```

> **Tip:** Genera una API Key segura con:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

### 4. Ejecutar la API

```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`

## Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/health` | ❌ | Health check |
| GET | `/api/moneda-valor` | ✅ | Listar todas las monedas |
| GET | `/api/moneda-valor?tipo_moneda=USD` | ✅ | Filtrar por tipo |
| GET | `/api/moneda-valor/{id}` | ✅ | Obtener por Id |

## Autenticación

Los endpoints protegidos requieren el header `X-API-Key`:

```bash
curl -H "X-API-Key: tu_clave_secreta" http://localhost:8000/api/moneda-valor
```

## Ejemplo de Respuesta

```json
{
  "count": 2,
  "data": [
    { "id": 1, "tipo_moneda": "USD", "valor": 4150.25 },
    { "id": 2, "tipo_moneda": "EUR", "valor": 4520.80 }
  ]
}
```

## Documentación Interactiva

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Despliegue en Azure App Service

### Opción 1: Despliegue directo desde VS Code

1. Instalar extensión **Azure App Service** en VS Code
2. Click derecho en la carpeta del proyecto → **Deploy to Web App**
3. Seleccionar o crear un App Service (Python 3.11)
4. Configurar variables de entorno en **Azure Portal → App Service → Configuration → Application Settings**

### Opción 2: Despliegue con Docker

```bash
# Construir imagen
docker build -t moneda-valor-api .

# Ejecutar localmente
docker run -p 8000:8000 --env-file .env moneda-valor-api
```

### Opción 3: Azure CLI

```bash
# Login
az login

# Crear grupo de recursos (si no existe)
az group create --name TRMGRUPOMEX --location "Mexico Central"

# Crear App Service Plan
az appservice plan create --name moneda-valor-plan --resource-group TRMGRUPOMEX --sku B1 --is-linux

# Crear Web App
az webapp create --resource-group TRMGRUPOMEX --plan moneda-valor-plan --name moneda-valor-api --runtime "PYTHON:3.11"

# Configurar variables de entorno
az webapp config appsettings set --resource-group TRMGRUPOMEX --name moneda-valor-api --settings \
  DB_SERVER=sltrm.database.windows.net \
  DB_NAME=tu_db \
  DB_USER=tu_user \
  DB_PASSWORD=tu_pass \
  API_KEY=tu_api_key

# Configurar startup command
az webapp config set --resource-group TRMGRUPOMEX --name moneda-valor-api --startup-file "gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"

# Desplegar
az webapp up --resource-group TRMGRUPOMEX --name moneda-valor-api
```

## Configuración en SAP

Para consumir este endpoint desde SAP (RFC/ABAP), configura:

1. **URL**: `https://moneda-valor-api.azurewebsites.net/api/moneda-valor`
2. **Método**: GET
3. **Header**: `X-API-Key: <tu_api_key>`
4. **Content-Type**: `application/json`
