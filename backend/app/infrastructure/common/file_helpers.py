import os
from pathlib import Path

def ensure_dir(path: Path) -> Path:
    """Ensures a directory exists and returns its Path."""
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_unique_filename(path: Path) -> Path:
    """Returns a unique path by appending a counter if the file already exists."""
    if not path.exists():
        return path
        
    base = path.stem
    ext = path.suffix
    directory = path.parent
    counter = 1
    
    while True:
        new_path = directory / f"{base}_{counter}{ext}"
        if not new_path.exists():
            return new_path
        counter += 1


