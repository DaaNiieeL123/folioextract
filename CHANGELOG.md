# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- Fix CORS misconfiguration: restrict origins to localhost instead of wildcard with credentials
- Add file path validation for PowerShell automation to prevent command injection
- Restrict `/api/system/open` endpoint to allowed directories only
- Add upload size limit (2 GB) to prevent disk exhaustion attacks
- Fix `os.chdir()` race condition in Markdown converter with thread lock
- Replace silent exception swallowing with proper logging in settings, job store, and logger

### Added

- `FOLIOEXTRACT_CORS_ORIGINS` environment variable for configurable CORS origins
- `CONTRIBUTING.md` with development setup and guidelines
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
- `SECURITY.md` with vulnerability reporting policy
- `CHANGELOG.md`

### Changed

- Improve error visibility for corrupted settings and job store read failures

## [0.1.0] - Initial Release

### Added

- PDF to Markdown, TXT, and DOCX conversion
- Batch processing with real-time SSE progress
- Persistent job history with cancel and retry support
- Multi-strategy conversion pipeline with automatic fallbacks
- Clean architecture backend (FastAPI + Pydantic)
- React + TypeScript + Vite frontend
- Desktop packaging via pywebview + PyInstaller (Windows)
