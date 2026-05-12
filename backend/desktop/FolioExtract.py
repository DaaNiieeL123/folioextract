import json
import socket
import sys
import threading
import time
import urllib.request
from multiprocessing import freeze_support
from pathlib import Path

import uvicorn
import webview
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.infrastructure.common.logger import logger
from backend.server import app

# Required on Windows to prevent recursive fork bombs in PyInstaller EXEs
if __name__ == "__main__":
    freeze_support()


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _ensure_frontend_routes(frontend_dist: Path) -> None:
    if any(getattr(route, "path", None) == "/" for route in app.routes):
        return

    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(str(frontend_dist / "index.html"))

    @app.get("/{catchall:path}")
    def serve_fallback(catchall: str):
        if catchall.startswith("api/"):
            return {"error": "Not found"}
        return FileResponse(str(frontend_dist / "index.html"))


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "ok":
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"El backend interno no respondió a tiempo: {last_error}")


def main():
    logger.info("Iniciando FolioExtract...")

    bundle_dir = _bundle_dir()
    frontend_dist = bundle_dir / "frontend" / "dist"
    if not frontend_dist.exists():
        raise SystemExit(f"frontend/dist no encontrado en: {frontend_dist}")

    logger.info(f"Sirviendo Frontend React desde: {frontend_dist}")
    _ensure_frontend_routes(frontend_dist)

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info", access_log=True)
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True, name="folioextract-backend")
    server_thread.start()
    _wait_for_server(base_url)

    window = webview.create_window("FolioExtract", base_url, width=1280, height=860, min_size=(980, 680))
    webview.start()

    server.should_exit = True
    server_thread.join(timeout=5)


if __name__ == "__main__":
    main()
