class ConversionError(Exception):
    """Base exception for all conversion errors."""
    pass

class UnsupportedFormatError(ConversionError):
    """Raised when an unsupported format is requested."""
    pass

class CorruptedPdfError(ConversionError):
    """Raised when a PDF cannot be opened or is corrupted."""
    pass


