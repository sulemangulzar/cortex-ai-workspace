from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import cast

from docx import Document
import pymupdf

from app.core.exceptions import ServiceError


class UnsupportedDocumentError(ServiceError):
    status_code = 415
    detail = "Unsupported document type"


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return _extract_pdf(data)
    if extension == ".txt":
        return _extract_txt(data)
    if extension == ".docx":
        return _extract_docx(data)
    raise UnsupportedDocumentError("Only .pdf, .txt, and .docx files are supported")


def _extract_pdf(data: bytes) -> str:
    chunks: list[str] = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for page in document:
            text = cast(str, page.get_text("text")).strip()
            if text:
                chunks.append(text)
    return "\n\n".join(chunks).strip()


def _extract_txt(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore").strip()


def _extract_docx(data: bytes) -> str:
    document = Document(BytesIO(data))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs).strip()
