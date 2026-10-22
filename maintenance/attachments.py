"""Untrusted file attachment extraction and handling."""

import hashlib
from typing import Any
from uuid import uuid4


class AttachmentService:
    def __init__(self, max_bytes: int = 5 * 1024 * 1024, max_chars: int = 50000):
        self.max_bytes = max_bytes
        self.max_chars = max_chars

    async def process_file(
        self,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> dict[str, Any]:
        if len(content) > self.max_bytes:
            raise ValueError(f"File exceeds maximum allowed size ({self.max_bytes} bytes).")

        content_hash = hashlib.sha256(content).hexdigest()
        extracted_text = ""
        status = "extracted"

        if mime_type in {"text/plain", "text/markdown"} or filename.endswith((".txt", ".md")):
            try:
                extracted_text = content.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = content.decode("latin-1", errors="replace")
        elif mime_type == "application/pdf" or filename.endswith(".pdf"):
            try:
                import io

                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(content))
                pages_text = []
                for p in reader.pages:
                    t = p.extract_text()
                    if t:
                        pages_text.append(t)
                extracted_text = "\n\n".join(pages_text)
                if not extracted_text.strip():
                    status = "empty_or_scanned_pdf"
            except Exception as exc:
                status = f"pdf_extraction_failed: {type(exc).__name__}"
                extracted_text = ""
        else:
            raise ValueError(f"Unsupported file MIME type: {mime_type}")

        # Enforce text character limit
        if len(extracted_text) > self.max_chars:
            extracted_text = extracted_text[: self.max_chars]

        return {
            "attachment_id": uuid4(),
            "content_hash": content_hash,
            "mime": mime_type,
            "extraction_status": status,
            "storage_key": f"uploads/{content_hash}_{filename}",
            "trust_type": "user_input",
            "extracted_text": extracted_text,
            "filename": filename,
        }
