from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class DocumentParser:
    supported_types = {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/markdown": ".md",
    }

    async def parse(self, file_path: Path, content_type: str) -> list[dict]:
        if content_type == "application/pdf":
            return self._parse_pdf(file_path)
        if content_type in {"text/plain", "text/markdown"}:
            return self._parse_text(file_path)
        raise ValueError(f"Unsupported content type: {content_type}")

    def _parse_pdf(self, file_path: Path) -> list[dict]:
        reader = PdfReader(str(file_path))
        pages: list[dict] = []
        for index, page in enumerate(reader.pages, start=1):
            pages.append({"text": page.extract_text() or "", "page_number": index})
        return pages

    def _parse_text(self, file_path: Path) -> list[dict]:
        return [{"text": file_path.read_text(encoding="utf-8"), "page_number": None}]
