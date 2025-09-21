# Documentación de Despliegue y Uso

Este documento describe los pasos para desplegar la aplicación "n8n Advanced Promoter" usando Docker y cómo integrarla con n8n para automatizar la generación de contenido de productos.

## 1. Despliegue de la Aplicación (Docker)

La aplicación está contenedorizada para facilitar su despliegue. El contenedor incluye tanto el frontend de Next.js como el backend de Python (FastAPI).

### Requisitos

- Tener [Docker](https://www.docker.com/get-started) instalado y en ejecución en tu sistema.

### Pasos para el Despliegue

**1. Construir la Imagen de Docker**

Abre una terminal en la raíz del proyecto y ejecuta el siguiente comando. Esto creará una imagen de Docker llamada `n8n-maikado` con todo lo necesario para ejecutar la aplicación.

```bash
docker build -t n8n-maikado .
```

**2. Ejecutar el Contenedor**

Una vez construida la imagen, puedes iniciar un contenedor a partir de ella con el siguiente comando:

```bash
docker run -d -p 3000:3000 -p 8000:8000 --name n8n-maikado-app n8n-maikado
```

- `-d`: Ejecuta el contenedor en segundo plano (detached mode).
- `-p 3000:3000`: Mapea el puerto 3000 de tu máquina al puerto 3000 del contenedor (para el frontend).
- `-p 8000:8000`: Mapea el puerto 8000 de tu máquina al puerto 8000 del contenedor (para el backend).
- `--name n8n-maikado-app`: Asigna un nombre fácil de recordar al contenedor.

**3. Verificar el Funcionamiento**

- **Frontend:** Abre tu navegador y visita [http://localhost:3000](http://localhost:3000). Deberías ver la interfaz de usuario de la aplicación.
- **Backend:** Puedes acceder a la API en [http://localhost:8000](http://localhost:8000).

### Gestión del Contenedor

- **Ver logs en tiempo real:**
  ```bash
  docker logs -f n8n-maikado-app
  ```

- **Detener el contenedor:**
  ```bash
  docker stop n8n-maikado-app
  ```

- **Eliminar el contenedor** (debe estar detenido primero):
  ```bash
  docker rm n8n-maikado-app
  ```

---

## 2. Integración con n8n

n8n puede orquestar todo el flujo de trabajo, desde la detección de un nuevo producto hasta la actualización de su contenido generado por esta aplicación.

### Flujo de Trabajo General

El objetivo es que n8n llame al endpoint del backend de nuestra aplicación para crear un "trabajo" de generación de contenido. Una vez que el trabajo se completa (lo cual puede ser un proceso asíncrono), n8n puede recuperar los resultados y usarlos en otros sistemas (como Shopify).

### Pasos en n8n

**Paso 1: Iniciar el Workflow (Trigger)**

Elige un trigger que se ajuste a tus necesidades. Algunos ejemplos:

- **Shopify Trigger:** Nodo `Shopify Trigger` configurado en "Product Created". Puedes añadir un filtro para que solo se active si el campo de descripción está vacío.
- **Webhook:** Nodo `Webhook` para iniciar el proceso desde cualquier sistema externo que pueda hacer una llamada HTTP.
- **Schedule:** Nodo `Schedule` para buscar productos sin contenido cada cierto tiempo.

**Paso 2: Crear el Trabajo de Generación (HTTP Request)**

Usa el nodo `HTTP Request` para enviar la información del producto al backend.

- **Method:** `POST`
- **URL:** `http://localhost:8000/create-job`
  *(Si n8n y esta aplicación se ejecutan en la misma red de Docker, puedes usar el nombre del servicio de Docker en lugar de `localhost`)*.
- **Body Content Type:** `JSON`
- **Body Parameters:**
  - Añade un parámetro y usa una expresión para construir el cuerpo de la solicitud. El frontend envía el siguiente formato, que puedes replicar:

    ```json
    {
      "productName": "{{ $json.body.title }}",
      "productPrice": "{{ $json.body.variants[0].price }}",
      "productUrl": "https://tu-tienda.myshopify.com/products/{{ $json.body.handle }}",
      "language": "es",
      "currency": "USD",
      "numImages": 3,
      "numVideos": 1,
      "figmaTemplate": "URL_DE_TU_PLANTILLA_FIGMA",
      "painPoints": "Puntos de dolor del cliente"
    }
    ```
    *Nota: Las expresiones `{{ ... }}` deben ajustarse según los datos que provea tu nodo de trigger (ej. Shopify).* 

La respuesta de este nodo te dará un `job_id`.

**Paso 3: Esperar y Verificar el Estado del Trabajo**

La generación de contenido puede tardar. Debes esperar un tiempo y luego verificar el estado del trabajo.

1.  **Wait Node:** Añade un nodo `Wait` para esperar un tiempo prudencial (ej. 1 o 2 minutos).
2.  **HTTP Request (Get Status):** Añade otro nodo `HTTP Request` para consultar el estado del trabajo.
    - **Method:** `GET`
    - **URL:** `http://localhost:8000/jobs/{{ $json.job_id }}`
      *(Usa la expresión para obtener el `job_id` del nodo anterior)*.
3.  **IF Node:** Añade un nodo `IF` para comprobar si el campo `status` en la respuesta es `completed`.
    - Si no está completado, puedes usar un bucle o esperar más tiempo.

**Paso 4: Usar el Contenido Generado**

Una vez que el trabajo está completado, la respuesta del `GET` al endpoint `/jobs/{job_id}` contendrá las URLs del contenido generado (ej. `output_shopify_url`).

- **Shopify Node:** Usa el nodo `Shopify` con la operación `Product -> Update` para actualizar la descripción del producto con el nuevo contenido.
- **Otras Acciones:** Envía una notificación por Slack, guarda los resultados en Google Drive, etc.

### Ejemplo Visual del Workflow en n8n

```
(Trigger: Shopify) ==> (HTTP Request: POST /create-job) ==> (Wait: 1 min) ==> (HTTP Request: GET /jobs/{id}) ==> (IF: status == 'completed'?) ==> (Shopify: Update Product)
```
