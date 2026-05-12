# Professional Architecture Overview

## Layered Architecture

The backend is organized in four explicit layers:

1. api
   - FastAPI request/response contracts.
2. domain
   - Entities, business errors, and ports.
3. application
   - Use cases and orchestration flow.
4. infrastructure
   - Concrete adapters: conversion engines, persistence, observability, notifications.

## Desktop Runtime

- The desktop distribution uses `backend/desktop/FolioExtract.py` as the only shell entrypoint.
- `pywebview` hosts the React build and the FastAPI application in a single lightweight Windows executable.
- Legacy Tk / `customtkinter` UI was retired to avoid maintaining two desktop surfaces.

## Naming Consistency

- Application orchestration is centered on use-case semantics (`conversion_use_case.py`).
- Ambiguous folders (`core`, `services`, `utils`, `ui`, `config`) were consolidated into clear infrastructure/application modules.
- API and domain remain framework-agnostic from a dependency perspective.

## Backend Structure

```text
backend/
  desktop/
    FolioExtract.py
  app/
    api/
      schemas.py
    application/
      batch_service.py
      conversion_use_case.py
    domain/
      entities.py
      errors.py
      ports.py
    infrastructure/
      common/
        file_helpers.py
        logger.py
      config/
        settings.py
      conversion/
        base_converter.py
        converter_factory.py
        docx_converter.py
        docx_quality.py
        exceptions.py
        extraction_pipeline.py
        markdown_quality.py
        md_converter.py
        md_fusion_repair.py
        plain_text_formatter.py
        text_cleaner.py
        txt_converter.py
      notifications/
        notification_service.py
      di/
        container.py
      observability/
        metrics.py
        structured_logger.py
      dynamic_factory.py
      job_store.py
```

## Runtime Observability

- Structured logs include context fields (`job_id`, `file`, `converter`).
- Metrics endpoint: `GET /api/metrics`.
- Health endpoint: `GET /api/health`.
- Unified error envelope for API failures.
