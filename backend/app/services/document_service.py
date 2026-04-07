from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


class DocumentService:
    SUPPORTED_TEXT_TYPES = {
        "text/plain",
        "text/markdown",
        "application/json",
    }

    def extract_text(self, filename: str, content_type: str | None, payload: bytes) -> str:
        lowered = filename.lower()
        declared_type = (content_type or "").lower()

        if lowered.endswith(".pdf") or declared_type == "application/pdf":
            return self._extract_pdf_text(payload)

        if (
            lowered.endswith((".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".java", ".html", ".css"))
            or declared_type in self.SUPPORTED_TEXT_TYPES
        ):
            return payload.decode("utf-8", errors="ignore")

        raise ValueError("Unsupported file type. Upload PDF, TXT, MD, JSON, CSV, or code/text files.")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
        cleaned = " ".join(text.split()).strip()
        if not cleaned:
            return []
        words = cleaned.split(" ")
        chunks: list[str] = []
        start = 0
        total = len(words)
        while start < total:
            end = min(total, start + chunk_size)
            chunk = " ".join(words[start:end]).strip()
            if chunk:
                chunks.append(chunk)
            if end >= total:
                break
            start = max(end - overlap, start + 1)
        return chunks

    @staticmethod
    def _extract_pdf_text(payload: bytes) -> str:
        reader = PdfReader(BytesIO(payload))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(part.strip() for part in parts if part.strip())
