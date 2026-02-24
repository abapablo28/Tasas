# Integración con SAP (Consumo de API REST)

Para consumir esta API desde SAP, el método más común es utilizar la clase estándar **`CL_HTTP_CLIENT`** en ABAP.

## Configuración de Conexión

### 1. URL del Endpoint
La URL base que desplegamos es:
`http://trmpythonback-mx.azurewebsites.net/api/moneda-valor`

### 2. Autenticación (Header)
Es obligatorio enviar la API Key en el header de la petición HTTP:
- **Header Name:** `X-API-Key`
- **Value:** `sap_connect` (o el valor que hayas configurado en Azure)

---

## Ejemplo de Código ABAP (Snippet)

Este es un ejemplo simplificado de cómo llamar a la API desde un programa ABAP:

```abap
DATA: lo_http_client TYPE REF TO if_http_client,
      lv_url         TYPE string,
      lv_api_key     TYPE string,
      lv_response    TYPE string,
      lv_code        TYPE i.

" 1. Configurar la URL
lv_url = 'http://trmpythonback-mx.azurewebsites.net/api/moneda-valor'.
lv_api_key = 'sap_connect'.

" 2. Crear el cliente HTTP
cl_http_client=>create_by_url(
  EXPORTING
    url                = lv_url
  IMPORTING
    client             = lo_http_client
  EXCEPTIONS
    argument_not_found = 1
    plugin_not_active  = 2
    internal_error     = 3
    OTHERS             = 4 ).

IF sy-subrc <> 0.
  " Manejar error de creación
  RETURN.
ENDIF.

" 3. Configurar el método GET
lo_http_client->request->set_method( if_http_entity=>co_request_method_get ).

" 4. Agregar el Header de Seguridad (X-API-Key)
lo_http_client->request->set_header_field(
  name  = 'X-API-Key'
  value = lv_api_key ).

" 5. Enviar la petición
lo_http_client->send(
  EXCEPTIONS
    http_communication_failure = 1
    http_invalid_state        = 2
    http_processing_failed    = 3
    OTHERS                    = 4 ).

IF sy-subrc = 0.
  " 6. Recibir la respuesta
  lo_http_client->receive(
    EXCEPTIONS
      http_communication_failure = 1
      http_invalid_state        = 2
      http_http_error           = 3
      OTHERS                    = 4 ).
ENDIF.

" 7. Obtener el cuerpo de la respuesta (el JSON)
IF sy-subrc = 0.
  lv_response = lo_http_client->response->get_cst_data( ).
  lo_http_client->response->get_status( IMPORTING code = lv_code ).
  
  WRITE: / 'Status Code:', lv_code.
  WRITE: / 'Response JSON:', lv_response.
ELSE.
  " Manejar errores de comunicación
ENDIF.

" 8. Cerrar conexión
lo_http_client->close( ).
```

## Recomendaciones Técnicas

1. **SM59:** Es mejor práctica crear un Destino RFC tipo 'G' (HTTP Connection to External Server) en la transacción `SM59`. Esto permite gestionar la URL y certificados de forma centralizada sin "quemar" la URL en el código ABAP.
2. **JSON Parsing:** Una vez recibas el `lv_response`, puedes usar la clase `/UI2/CL_JSON` para convertir el JSON directamente a una estructura o tabla interna ABAP.
3. **Capa de Seguridad:** Si vas a consumir la API mediante HTTPS (recomendado), deberás importar el certificado de Azure en la transacción `STRUST` de tu sistema SAP.
