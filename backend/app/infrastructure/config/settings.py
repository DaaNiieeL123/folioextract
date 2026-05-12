import json
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class AppSettings:
    theme: str = "System"
    last_output_dir: str = ""
    
    @classmethod
    def load(cls, path: Path) -> 'AppSettings':
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Filter only fields that exist in the dataclass
                    valid_keys = cls.__dataclass_fields__.keys()
                    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
                    return cls(**filtered_data)
        except Exception:
            pass # Return default if corrupted
        return cls()
        
    def save(self, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception:
            pass # Fail gracefully if permissions issue


