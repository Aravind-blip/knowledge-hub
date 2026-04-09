import hashlib
import re
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings

settings = get_settings()

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
}


def build_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def estimate_token_count(text: str) -> int:
    return max(1, len(text.split()))


def keyword_tokens(text: str) -> set[str]:
    tokens = {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}
    return {token for token in tokens if token not in STOPWORDS}


def keyword_overlap(query: str, content: str) -> int:
    query_tokens = keyword_tokens(query)
    if not query_tokens:
        return 0
    content_tokens = keyword_tokens(content)
    return len(query_tokens & content_tokens)


def stable_hash_embedding(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for index in range(dimensions):
        byte = digest[index % len(digest)]
        values.append((byte / 255.0) * 2 - 1)
    return values


def compact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value is not None}
