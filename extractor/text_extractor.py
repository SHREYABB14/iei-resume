import os
from typing import Optional


def extract_text_from_file(path: str) -> str:
    """Extract text from PDF or DOCX file. Returns empty string on failure."""
    path = str(path)
    if not os.path.exists(path):
        return ''
    _, ext = os.path.splitext(path.lower())
    try:
        if ext == '.pdf':
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(path)
                parts = []
                for page in doc:
                    parts.append(page.get_text())
                return '\n'.join(parts)
            except Exception:
                # fallback to pdfplumber if installed
                try:
                    import pdfplumber
                    parts = []
                    with pdfplumber.open(path) as pdf:
                        for p in pdf.pages:
                            parts.append(p.extract_text() or '')
                    return '\n'.join(parts)
                except Exception:
                    return ''
        elif ext in ('.docx', '.doc'):
            try:
                from docx import Document
                doc = Document(path)
                parts = [p.text for p in doc.paragraphs]
                return '\n'.join(parts)
            except Exception:
                return ''
        else:
            return ''
    except Exception:
        return ''
