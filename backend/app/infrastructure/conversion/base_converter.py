from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class ConversionResult:
    success: bool
    output_path: Optional[Path]
    error: Optional[str] = None
    pages_processed: int = 0

class BaseConverter(ABC):
    @property
    @abstractmethod
    def extension(self) -> str:
        """The output file extension for this converter, e.g. '.md'"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name for the UI."""
        pass

    @abstractmethod
    def convert(self, source: Path, destination: Path) -> ConversionResult:
        """Converts the source PDF to the destination file."""
        pass


