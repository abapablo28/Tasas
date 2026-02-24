# Protección de Endpoints con API Key en FastAPI

## ¿Por qué no puedes poner la API Key en la URL?
- Los headers HTTP (como `X-API-Key`) no se pueden enviar desde la barra de direcciones del navegador, solo desde herramientas que permiten modificar los headers (Postman, Swagger UI, extensiones, código, etc).
- Esto es por seguridad: las API Keys no deben ir en la URL porque pueden quedar expuestas en logs, historial, etc.

## ¿Cómo funciona la protección con API Key en tu código?

En tu archivo `app/auth.py` (o similar) tienes algo como esto:
```python
from fastapi import Header, HTTPException, status

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "sap_connect":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
```
Y en los endpoints protegidos:
```python
@app.get("/api/moneda-valor")
async def list_moneda_valor(..., _api_key: str = Depends(verify_api_key)):
    # ...código...
```
Esto hace que cualquier petición a `/api/moneda-valor` requiera el header `X-API-Key: sap_connect`.

## ¿Cómo probarlo tú mismo?

### a) Usando Swagger UI (más fácil)
1. Ve a https://trmpythonback-mx.azurewebsites.net/docs
2. Haz clic en "Authorize" (ícono de candado).
3. Escribe `sap_connect` y haz clic en "Authorize".
4. Prueba los endpoints protegidos.

### b) Usando Postman
1. Descarga [Postman](https://www.postman.com/downloads/).
2. Crea una nueva petición GET a:  
   `https://trmpythonback-mx.azurewebsites.net/api/moneda-valor`
3. Ve a la pestaña "Headers" y agrega:
   - Key: `X-API-Key`
   - Value: `sap_connect`
4. Haz clic en "Send".

### c) Usando extensiones de navegador
- Instala [ModHeader](https://modheader.com/)
- Agrega el header `X-API-Key: sap_connect`
- Navega a la URL protegida.

## Recursos para aprender más

- **FastAPI Security Docs:**  
  https://fastapi.tiangolo.com/advanced/security/
- **Autenticación con API Key en FastAPI:**  
  https://fastapi.tiangolo.com/advanced/security/api-key/
- **Postman (cómo usar headers):**  
  https://learning.postman.com/docs/sending-requests/requests/#headers
- **ModHeader (extensión para Chrome/Edge/Firefox):**  
  https://modheader.com/
- **Video: FastAPI Security with API Key**  
  https://www.youtube.com/watch?v=6Qmnh5C4Pmo

## Explicación del código de seguridad

- El decorador `Depends(verify_api_key)` hace que FastAPI ejecute la función `verify_api_key` antes de ejecutar el endpoint.
- Si la API Key es incorrecta, lanza un error 401 y no ejecuta el endpoint.
- Si es correcta, el endpoint se ejecuta normalmente.

---

¿Dudas? Puedes modificar el valor de la API Key en tu código para mayor seguridad, o implementar autenticación más avanzada según tus necesidades.
