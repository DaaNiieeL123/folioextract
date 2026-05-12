from pydantic import BaseModel, Field
from typing import List, Optional

class ConversionRequest(BaseModel):
    paths: List[str] = Field(description="Lista de directorios absolutos a los PDFs")
    output_dir: str = Field(description="Directorio absoluto donde se guardará")
    extension: str = Field(description="Extensión de salida, ej. '.md', '.docx'")

class ConversionStatus(BaseModel):
    current: int
    total: int
    filename: str
    is_error: bool
    error_msg: Optional[str] = None
    
class BatchCompleteResponse(BaseModel):
    successes: int
    errors: int
    
class SettingsData(BaseModel):
    theme: str
    last_output_dir: str


class OpenPathRequest(BaseModel):
    path: str


class SelectFolderRequest(BaseModel):
    initial_path: Optional[str] = None


