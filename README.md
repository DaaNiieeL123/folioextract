# FolioExtract

<div align="center">

**Open-source desktop PDF extraction tool**

Extract and convert PDF content to editable formats: Markdown, TXT, and DOCX

[English](#english) | [Español](#español)

---

</div>

## English

### Features

- **PDF to Markdown, TXT, and DOCX** conversion with high fidelity
- **Batch processing** with real-time progress tracking via SSE
- **Persistent job history** with cancel and retry support
- **Multi-strategy conversion pipeline** with automatic fallbacks (Docling, pymupdf4llm, pdfplumber, EasyOCR)
- **Clean architecture** backend (FastAPI + Pydantic) with explicit layers
- **Modern frontend** (React 19 + TypeScript + Vite + Tailwind CSS)
- **Desktop app** via pywebview + PyInstaller (Windows `.exe`)
- **Open source** under MIT License

### Installation

#### Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+

#### Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/folioextract.git
cd folioextract

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment variables
cp .env.example .env

# Start the backend
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000

# In another terminal, start the frontend
cd frontend && npm run dev
```

Visit `http://localhost:5173` to use FolioExtract.

#### Docker (Backend Only)

```bash
docker compose up -d
```

The backend API will be available at `http://localhost:8000`.

#### Desktop App (Windows)

```bash
# Build frontend
cd frontend && npm run build && cd ..

# Build .exe
python scripts/build/build_exe.py
```

The executable will be in `dist/FolioExtract.exe`.

### Usage

#### Web UI

1. Open `http://localhost:5173` in your browser
2. Select output format (`.md`, `.txt`, or `.docx`)
3. Choose output directory
4. Drag & drop PDFs or select a folder
5. Monitor progress in real-time
6. Open converted files from the history panel

#### API

**Convert local files:**

```bash
curl -X POST http://127.0.0.1:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["/path/to/document.pdf"],
    "output_dir": "/path/to/output",
    "extension": ".md"
  }'
```

**Upload and convert:**

```bash
curl -X POST http://127.0.0.1:8000/api/convert/upload \
  -F "files=@document.pdf" \
  -F "output_dir=/path/to/output" \
  -F "extension=.md"
```

**Track progress:**

```bash
curl http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/jobs/{job_id}
```

#### API Documentation

Interactive API docs available at `http://127.0.0.1:8000/docs` (Swagger UI).

### Architecture

```
folioextract/
├── backend/                 # Python FastAPI backend
│   ├── server.py           # API routes and app factory
│   ├── app/
│   │   ├── api/            # Request/response schemas (Pydantic)
│   │   ├── domain/         # Business entities, errors, ports
│   │   ├── application/    # Use cases and orchestration
│   │   └── infrastructure/ # Converters, persistence, config
│   └── desktop/            # pywebview desktop shell
├── frontend/               # React + Vite frontend
│   └── src/
│       ├── components/     # UI components
│       ├── services/api/   # API client layer
│       └── store/          # Zustand state management
├── tests/                  # pytest test suite
└── docs/                   # Documentation
```

The backend follows **Clean Architecture** with four explicit layers:
1. **API** — FastAPI contracts
2. **Domain** — Entities, errors, interfaces
3. **Application** — Use cases
4. **Infrastructure** — Concrete adapters

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

### Development

```bash
# Run tests
python -m pytest -q

# Run tests with coverage
python -m pytest --cov=backend --cov-report=term-missing

# Lint
ruff check backend/ tests/
cd frontend && npm run lint

# Format
ruff format backend/ tests/
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for detailed development guidelines.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend URL for frontend | `http://127.0.0.1:8000` |
| `UVICORN_HOST` | Backend host | `127.0.0.1` |
| `UVICORN_PORT` | Backend port | `8000` |
| `FOLIOEXTRACT_HOME` | Data directory (settings, logs, jobs) | `~/.folioextract` |
| `FOLIOEXTRACT_CORS_ORIGINS` | Comma-separated CORS origins | `http://127.0.0.1:8000,http://localhost:5173` |

### Known Limitations

- **DOCX via Word automation** is Windows-only (requires Microsoft Word)
- **Desktop packaging** (`.exe`) is Windows-only
- PDF input only; other formats not yet supported
- Large PDFs (>500 pages) may require significant memory

### Roadmap

- [ ] Cross-platform desktop builds (macOS, Linux)
- [ ] Additional output formats (EPUB, HTML)
- [ ] OCR language selection
- [ ] Batch configuration presets
- [ ] Plugin system for custom converters

### Contributing

Contributions are welcome! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before getting started.

### License

MIT License - see [`LICENSE`](LICENSE) file for details.

### Security

See [`SECURITY.md`](SECURITY.md) for vulnerability reporting guidelines.

---

## Español

### Características

- **Conversión de PDF a Markdown, TXT y DOCX** con alta fidelidad
- **Procesamiento por lotes** con seguimiento de progreso en tiempo real via SSE
- **Historial de jobs persistente** con soporte para cancelación y reintento
- **Pipeline de conversión multi-estrategia** con fallbacks automáticos (Docling, pymupdf4llm, pdfplumber, EasyOCR)
- **Backend con arquitectura limpia** (FastAPI + Pydantic) con capas explícitas
- **Frontend moderno** (React 19 + TypeScript + Vite + Tailwind CSS)
- **Aplicación de escritorio** via pywebview + PyInstaller (Windows `.exe`)
- **Código abierto** bajo licencia MIT

### Instalación

#### Requisitos previos

- Python 3.10+
- Node.js 18+
- npm 9+

#### Inicio rápido

```bash
# Clonar el repositorio
git clone https://github.com/YOUR_USERNAME/folioextract.git
cd folioextract

# Instalar dependencias del backend
pip install -r backend/requirements.txt

# Instalar dependencias del frontend
cd frontend && npm install && cd ..

# Copiar variables de entorno
cp .env.example .env

# Iniciar el backend
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000

# En otra terminal, iniciar el frontend
cd frontend && npm run dev
```

Visita `http://localhost:5173` para usar FolioExtract.

#### Docker (Solo Backend)

```bash
docker compose up -d
```

La API del backend estará disponible en `http://localhost:8000`.

#### Aplicación de Escritorio (Windows)

```bash
# Compilar frontend
cd frontend && npm run build && cd ..

# Compilar .exe
python scripts/build/build_exe.py
```

El ejecutable estará en `dist/FolioExtract.exe`.

### Uso

#### Interfaz Web

1. Abre `http://localhost:5173` en tu navegador
2. Selecciona el formato de salida (`.md`, `.txt` o `.docx`)
3. Elige el directorio de salida
4. Arrastra y suelta PDFs o selecciona una carpeta
5. Monitorea el progreso en tiempo real
6. Abre los archivos convertidos desde el panel de historial

#### API

**Convertir archivos locales:**

```bash
curl -X POST http://127.0.0.1:8000/api/convert \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["/ruta/al/documento.pdf"],
    "output_dir": "/ruta/de/salida",
    "extension": ".md"
  }'
```

**Subir y convertir:**

```bash
curl -X POST http://127.0.0.1:8000/api/convert/upload \
  -F "files=@documento.pdf" \
  -F "output_dir=/ruta/de/salida" \
  -F "extension=.md"
```

**Seguimiento de progreso:**

```bash
curl http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/jobs/{job_id}
```

#### Documentación de API

Documentación interactiva de API disponible en `http://127.0.0.1:8000/docs` (Swagger UI).

### Arquitectura

```
folioextract/
├── backend/                 # Backend Python FastAPI
│   ├── server.py           # Rutas de API y factory de app
│   ├── app/
│   │   ├── api/            # Schemas de request/response (Pydantic)
│   │   ├── domain/         # Entidades de negocio, errores, puertos
│   │   ├── application/    # Casos de uso y orquestación
│   │   └── infrastructure/ # Conversores, persistencia, config
│   └── desktop/            # Shell de escritorio pywebview
├── frontend/               # Frontend React + Vite
│   └── src/
│       ├── components/     # Componentes UI
│       ├── services/api/   # Capa cliente de API
│       └── store/          # Gestión de estado Zustand
├── tests/                  # Suite de tests pytest
└── docs/                   # Documentación
```

El backend sigue **Arquitectura Limpia** con cuatro capas explícitas:
1. **API** — Contratos FastAPI
2. **Domain** — Entidades, errores, interfaces
3. **Application** — Casos de uso
4. **Infrastructure** — Adaptadores concretos

Ver [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) para detalles.

### Desarrollo

```bash
# Ejecutar tests
python -m pytest -q

# Ejecutar tests con cobertura
python -m pytest --cov=backend --cov-report=term-missing

# Lint
ruff check backend/ tests/
cd frontend && npm run lint

# Formatear
ruff format backend/ tests/
```

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md) para guías detalladas de desarrollo.

### Variables de Entorno

| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `VITE_API_URL` | URL del backend para frontend | `http://127.0.0.1:8000` |
| `UVICORN_HOST` | Host del backend | `127.0.0.1` |
| `UVICORN_PORT` | Puerto del backend | `8000` |
| `FOLIOEXTRACT_HOME` | Directorio de datos (settings, logs, jobs) | `~/.folioextract` |
| `FOLIOEXTRACT_CORS_ORIGINS` | Orígenes CORS separados por comas | `http://127.0.0.1:8000,http://localhost:5173` |

### Limitaciones Conocidas

- **DOCX via automatización de Word** es solo para Windows (requiere Microsoft Word)
- **Empaquetado de escritorio** (`.exe`) es solo para Windows
- Solo entrada PDF; otros formatos aún no soportados
- PDFs grandes (>500 páginas) pueden requerir memoria significativa

### Roadmap

- [ ] Builds de escritorio multiplataforma (macOS, Linux)
- [ ] Formatos de salida adicionales (EPUB, HTML)
- [ ] Selección de idioma OCR
- [ ] Presets de configuración por lotes
- [ ] Sistema de plugins para conversores personalizados

### Contribuir

¡Las contribuciones son bienvenidas! Por favor lee [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) antes de comenzar.

### Licencia

Licencia MIT - ver archivo [`LICENSE`](LICENSE) para detalles.

### Seguridad

Ver [`SECURITY.md`](SECURITY.md) para guías de reporte de vulnerabilidades.
