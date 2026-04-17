import asyncio
import os
from pathlib import Path

import httpx

DEMO_DATA_DIR = Path(__file__).resolve().parents[2] / "docs" / "demo-data"
DEFAULT_BASE_URL = os.getenv("KNOWLEDGE_HUB_BASE_URL", "http://localhost:8000")
BEARER_TOKEN = os.getenv("KNOWLEDGE_HUB_BEARER_TOKEN")


async def main() -> None:
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"} if BEARER_TOKEN else None
    async with httpx.AsyncClient(base_url=DEFAULT_BASE_URL.rstrip("/"), timeout=120.0, headers=headers) as client:
        for path in sorted(DEMO_DATA_DIR.glob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".pdf"}:
                continue
            files = {"file": (path.name, path.read_bytes(), content_type_for(path.suffix.lower()))}
            response = await client.post("/api/documents/upload", files=files)
            response.raise_for_status()
            payload = response.json()
            print(f"Indexed {payload['original_name']} ({payload['status']})")


def content_type_for(suffix: str) -> str:
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
    }.get(suffix, "application/octet-stream")


if __name__ == "__main__":
    asyncio.run(main())
