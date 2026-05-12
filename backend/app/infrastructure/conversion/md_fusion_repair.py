"""
Hybrid fusion repairer for Markdown post-processing.

Strategy:
  1. pymupdf4llm extracts the full Markdown (preserving tables, headers, images)
  2. pdfplumber extracts each page as plain text with correct word spacing
  3. We scan the Markdown for "fused tokens" (long runs of letters without spaces)
  4. For each fused token, we search in pdfplumber's output for the matching
     span of words (character-matched, modulo spaces) and replace the token
     with the properly-spaced version.

This gives us the best of both worlds:
  - pymupdf4llm's rich Markdown structure (tables, headers, bold, images)
  - pdfplumber's geometrically-correct word separation
"""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path


# Regex: Spanish/Latin letter runs of 18+ chars without whitespace
_FUSED_TOKEN_RE = re.compile(r'[A-Za-záéíóúüñÁÉÍÓÚÜÑçÇàèìòùÀÈÌÒÙ]{18,}')


def _strip_accents(text: str) -> str:
    """Normalize accented chars to ASCII equivalents for comparison."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def _words_from_pdfplumber(source: Path) -> list[str]:
    """
    Extract a flat list of all words from the PDF using pdfplumber.
    This is our "ground truth" for where spaces should be.
    """
    try:
        import pdfplumber
        words = []
        with pdfplumber.open(str(source)) as pdf:
            for page in pdf.pages:
                raw = page.extract_text(x_tolerance=3, y_tolerance=3, layout=False) or ""
                words.extend(raw.split())
        return words
    except Exception:
        return []


def _try_unsplit(fused: str, ref_words: list[str]) -> str:
    """
    Given a fused token (e.g. "Eldesafíocentral"), try to find a
    contiguous run of words from `ref_words` that, when concatenated
    without spaces, matches the fused token.

    Returns the proper spaced string on success, or the original fused token.
    """
    fused_stripped = _strip_accents(fused).lower()
    n = len(fused_stripped)

    # Limit search window — fully fused lines can span ~20 words
    max_span = 30
    max_word_len = 30

    for i, word in enumerate(ref_words):
        if not word:
            continue
        # Quick reject: first word's start must match fused token's start
        w0 = _strip_accents(word).lower()
        if not fused_stripped.startswith(w0[:min(4, len(w0))]):
            continue

        # Try spans of increasing length
        accumulated = ""
        span_words = []
        for j in range(i, min(i + max_span, len(ref_words))):
            w = ref_words[j]
            if len(w) > max_word_len:
                break
            
            # Extract only letters/numbers from pdfplumber word (strip trailing punctuation like '.')
            w_clean = re.sub(r'[^\w]', '', w)
            if not w_clean:
                continue
                
            accumulated += _strip_accents(w_clean).lower()
            span_words.append(w_clean)

            if len(accumulated) == n and accumulated == fused_stripped:
                return ' '.join(span_words)  # ✅ perfect match
            if len(accumulated) > n:
                break  # overshot

    return fused  # no match found → keep original


def repair_fused_words(md_text: str, source: Path) -> str:
    """
    Scans markdown text for fused word tokens and repairs them using
    pdfplumber's geometrically-extracted word list as reference.
    """
    ref_words = _words_from_pdfplumber(source)
    if not ref_words:
        return md_text   # nothing to do if extraction failed

    def replace_token(match: re.Match) -> str:  # type: ignore[type-arg]
        fused = match.group(0)
        fixed = _try_unsplit(fused, ref_words)
        return fixed

    return _FUSED_TOKEN_RE.sub(replace_token, md_text)


