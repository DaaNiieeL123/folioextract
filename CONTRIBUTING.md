# Contributing to FolioExtract

Thank you for your interest in contributing to FolioExtract! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **npm** 9+

### Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/folioextract.git
   cd folioextract
   ```

2. **Set up the backend**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. **Set up the frontend**

   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. **Copy environment variables**

   ```bash
   cp .env.example .env
   ```

5. **Run the backend**

   ```bash
   python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **Run the frontend** (in a separate terminal)

   ```bash
   cd frontend
   npm run dev
   ```

The frontend will be available at `http://localhost:5173` and the backend at `http://127.0.0.1:8000`.

## Project Structure

```
folioextract/
├── backend/                 # Python FastAPI backend
│   ├── server.py           # API routes and app factory
│   ├── app/
│   │   ├── api/            # Request/response schemas
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
├── docs/                   # Documentation
└── scripts/                # Build and utility scripts
```

## Architecture

The backend follows **Clean Architecture** with four layers:

1. **API** (`backend/app/api/`) — FastAPI request/response contracts (Pydantic models)
2. **Domain** (`backend/app/domain/`) — Entities, business errors, and port interfaces
3. **Application** (`backend/app/application/`) — Use cases and batch orchestration
4. **Infrastructure** (`backend/app/infrastructure/`) — Concrete adapters: converters, job store, config, logging

For detailed architecture documentation, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Making Changes

### Branch Naming

- `feat/description` — New features
- `fix/description` — Bug fixes
- `docs/description` — Documentation changes
- `refactor/description` — Code refactoring
- `test/description` — Test additions or fixes

### Commit Messages

Use clear, descriptive commit messages:

```
type(scope): description

[optional body]
```

Examples:
- `feat(converter): add EPUB output format support`
- `fix(upload): validate file size before processing`
- `docs(readme): add Docker setup instructions`

### Code Style

**Backend (Python):**
- Follow PEP 8
- Use type hints for function signatures
- Keep functions focused and small
- Add docstrings for public functions

**Frontend (TypeScript/React):**
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use Tailwind CSS for styling
- Keep components focused on a single responsibility

## Testing

### Run Backend Tests

```bash
python -m pytest -q
```

### Run Backend Tests with Coverage

```bash
python -m pytest --cov=backend --cov-report=term-missing
```

### Run Frontend Lint

```bash
cd frontend
npm run lint
```

### Run Frontend Build (TypeScript check)

```bash
cd frontend
npm run build
```

## Pull Request Process

1. **Fork** the repository and create your branch from `main`
2. **Write tests** for any new functionality
3. **Ensure all tests pass** and lint checks are clean
4. **Update documentation** if your changes affect the API or user-facing behavior
5. **Submit a pull request** with a clear description of what changed and why
6. **Respond to review feedback** promptly

### PR Checklist

- [ ] Code follows the project's style guidelines
- [ ] Self-review of the code completed
- [ ] Comments added for complex logic (if needed)
- [ ] Documentation updated (if applicable)
- [ ] Tests added or updated
- [ ] All tests pass locally
- [ ] No new warnings introduced

## Reporting Bugs

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- Steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (OS, Python version, Node version)
- Screenshots or logs if applicable

## Suggesting Features

Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:

- Problem description (what problem does this solve?)
- Proposed solution
- Alternatives considered
- Any relevant examples or mockups

## Known Limitations

- **DOCX conversion via Word automation** is Windows-only (requires Microsoft Word installed)
- **Desktop packaging** (`.exe`) is Windows-only via PyInstaller
- The project currently supports PDF input only; other formats are not yet supported

## Questions?

Open a [Discussion](https://github.com/YOUR_USERNAME/folioextract/discussions) on GitHub.

Thank you for contributing!
