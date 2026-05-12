# FolioExtract - Open Source Document Extraction

![FolioExtract banner](assets/branding/github_banner.png)

FolioExtract es una herramienta open-source de escritorio para extraer y convertir contenido PDF a formatos editables como Markdown, TXT y DOCX. Combina backend FastAPI, frontend React/Vite y una arquitectura por capas con foco en mantenibilidad, trazabilidad y experiencia de usuario.

## Features

- Conversion de PDF a formatos `.md`, `.txt` y `.docx`.
- Procesamiento por lotes con progreso en tiempo real via SSE.
- Historial persistente de jobs con estado por archivo.
- Cancelacion y reintento de jobs desde la UI.
- Apertura de carpeta de salida y archivos convertidos.
- Recuperacion de jobs interrumpidos al reiniciar la app.
- API documentada y desacoplada del frontend.
- Pipeline de calidad para mejorar salida Markdown, texto plano y DOCX.
- Arquitectura limpia con capas explicitas y dependencias inyectadas.
- Shell desktop liviano con `pywebview` para empaquetado en `.exe`.

## Flujo Completo Del Sistema

1. El usuario selecciona archivos PDF o una carpeta desde el frontend React.
2. El frontend sube los PDFs al backend via `POST /api/convert/upload`.
3. El backend valida la solicitud y crea un job persistente.
4. El caso de uso de aplicacion ejecuta conversiones en paralelo.
5. El backend emite eventos SSE por job (`/api/jobs/{job_id}/progress`) con avance y estado.
6. El frontend actualiza barra de progreso, resumen y errores por archivo.
7. El usuario puede cancelar, reintentar fallidos y abrir resultados desde la UI.
8. Al finalizar, el job queda disponible en `GET /api/jobs` y `GET /api/jobs/{job_id}`.

## Estructura Del Proyecto

```text
pdf_converter/
  backend/
    server.py
    requirements.txt
    desktop/
      FolioExtract.py
    app/
      api/
      application/
      domain/
      infrastructure/
  frontend/
    src/
      components/
      services/api/
      store/
    public/
  tests/
    backend/
  docs/
    ARCHITECTURE.md
    REFACTOR_NOTES.md
    CONVERSION_EXAMPLES.md
  scripts/
    build/
    tools/
  .env.example
```

## Capas Backend

- `backend/app/domain`: entidades, errores y contratos (ports).
- `backend/app/application`: casos de uso y coordinadores de flujo.
- `backend/app/infrastructure`: conversion, persistencia, observabilidad, config y adaptadores.
- `backend/app/api`: contratos de entrada/salida para FastAPI.

Detalles: `docs/ARCHITECTURE.md`.

## Configuracion

El proyecto incluye `.env.example` para estandarizar variables de entorno.

Variables:

- `VITE_API_URL`: URL base del backend usada por el frontend. En desktop empaquetado no es necesaria; el frontend usa el mismo origen del shell `pywebview`.
- `UVICORN_HOST`: host de ejecucion sugerido para el backend.
- `UVICORN_PORT`: puerto de ejecucion sugerido para el backend.
- `FOLIOEXTRACT_HOME`: directorio opcional para settings, logs e historial de jobs. Si se omite, FolioExtract usa `~/.folioextract` o un fallback local de plataforma.

## Ejecucion Local

### Backend

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

Nota: ejecutar desde la raiz del repositorio para que el paquete `backend` sea resoluble.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Desktop (`.exe`)

```bash
cd frontend
npm install
npm run build
cd ..
python scripts/build/build_exe.py
```

La build desktop usa `pywebview` y hospeda FastAPI internamente; no requiere `uvicorn` manual una vez empaquetada.

## Ejemplos De Uso

### Conversion por rutas (modo API/backoffice)

Request:

```bash
curl -X POST http://127.0.0.1:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["C:/docs/a.pdf", "C:/docs/b.pdf"],
    "output_dir": "C:/docs/convertidos",
    "extension": ".md"
  }'
```

Respuesta esperada:

```json
{
  "message": "Conversion started in background",
  "job_id": "<uuid>"
}
```

### Seguimiento de job

```bash
curl http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/jobs/<job_id>
```

## Endpoints Principales

- `POST /api/convert`
- `POST /api/convert/upload`
- `GET /api/jobs/{job_id}/progress`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/retry`
- `POST /api/system/open`
- `GET /api/metrics`
- `GET /api/health`

## Pruebas

```bash
python -m pytest -q
```

## Documentacion

- Arquitectura: `docs/ARCHITECTURE.md`
- Notas de refactor: `docs/REFACTOR_NOTES.md`
- Ejemplos de conversion: `docs/CONVERSION_EXAMPLES.md`
