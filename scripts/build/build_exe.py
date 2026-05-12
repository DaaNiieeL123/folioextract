import os
import subprocess
import sys
import importlib.util
from pathlib import Path

def main():
    print("Building FolioExtract with PyInstaller...")
    repo_root = Path(__file__).resolve().parents[2]
    os.chdir(repo_root)
    frontend_dist = repo_root / "frontend" / "dist"
    spec_file = repo_root / "scripts" / "build" / "FolioExtract.spec"
    if not frontend_dist.exists():
        raise SystemExit("frontend/dist no existe. Ejecuta `npm --prefix frontend run build` antes de empaquetar.")
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit("PyInstaller no esta instalado en este entorno. Instala dependencias con `python -m pip install -r backend/requirements.txt`.")
    if not spec_file.exists():
        raise SystemExit(f"No se encontro el spec de PyInstaller: {spec_file}")
    
    # Run PyInstaller using the checked-in spec for deterministic builds.
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        str(spec_file),
    ]
    
    subprocess.check_call(cmd)
    print("\nBuild complete. You can find the executable at: dist/FolioExtract/FolioExtract.exe")

if __name__ == '__main__':
    main()
