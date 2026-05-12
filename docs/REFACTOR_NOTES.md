# Refactor Notes (FolioExtract)

## Scope

- Refactor incremental without breaking existing features.
- Current behavior treated as source of truth.
- Functional names preserved unless required for bug fixing.

## Backend Improvements

- Normalized converter extension handling in `ConverterFactory`:

  - Accepts `md`, `.md`, `.MD` consistently.
  - Keeps existing converter contracts intact.

- Improved batch conversion flow in `BatchService`:

  - Fixed progress reporting to use processed count (completion order), not submit index.
  - Added early return for empty batches.
  - Right-sized process workers per batch (`1..4`) to reduce unnecessary process overhead.

- Refactored FastAPI dialog endpoints in `backend/server.py`:
  - This approach was later retired when the project standardized on `React + FastAPI + pywebview`.
  - Native file dialogs were removed in favor of browser-side file and folder selection.

## Frontend Improvements

- `App.tsx`:

  - Fixed "Convertir carpeta" no-op by integrating folder-to-PDF selection flow.
  - Added SSE subscription cleanup to prevent stale listeners/memory leaks.
  - Added processing guard to avoid overlapping conversion sessions.

- `services/api/client.ts`:

  - Introduced typed `requestJson` helper to remove fetch duplication.
  - Added robust EventSource parsing/error handling.
  - Centralized backend route construction for conversion, jobs, settings and system actions.

## Quality and Test Coverage

- Added factory tests for extension normalization:

  - without dot (`md`)
  - case-insensitive (`.MD`)

- Existing tests still pass after refactor.

## Dependency Review

- Current stack is valid and maintained for project goals.
- No dependency was replaced to avoid compatibility risk during this refactor pass.

### Evaluated alternatives (not applied in this pass)

- `orjson` for faster JSON serialization in FastAPI responses.
- `httpx` for structured API clients if backend-to-backend calls are added later.
- `pydantic-settings` if settings become environment-driven and more complex.

## Next Safe Refactor Candidates

- Introduce a shared conversion job state service to support cancellation/retry.
- Add structured logging context (job id, source file, converter) for production diagnostics.
- Expand tests for batch progress edge cases and API endpoints.
- Redesign SSE and progress tracking to be per-`job_id` instead of a single global queue.
