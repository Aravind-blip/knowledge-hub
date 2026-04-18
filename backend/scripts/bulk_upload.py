from __future__ import annotations

import argparse
import asyncio
import statistics
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from test_harness import (
    build_backend_headers,
    sign_in_with_supabase,
    slugify,
    write_json_report,
)

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parents[2] / "docs" / "demo-data"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "artifacts" / "uploads" / "latest.json"


@dataclass(frozen=True)
class UploadResult:
    file_name: str
    status_code: int
    duration_ms: float
    success: bool
    document_status: str | None
    detail: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk-upload many files into Knowledge Hub and report indexing outcomes.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL.")
    parser.add_argument("--email", required=True, help="Supabase test user email.")
    parser.add_argument("--password", required=True, help="Supabase test user password.")
    parser.add_argument("--count", type=int, default=10, help="How many files to upload.")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent upload workers.")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR), help="Directory containing source templates.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write the JSON upload report.")
    parser.add_argument("--supabase-url", default=None, help="Override Supabase URL.")
    parser.add_argument("--supabase-anon-key", default=None, help="Override Supabase anon key.")
    return parser.parse_args()


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def _load_templates(source_dir: Path) -> list[tuple[Path, str]]:
    templates: list[tuple[Path, str]] = []
    for path in sorted(source_dir.glob("*")):
        if path.suffix.lower() not in {".md", ".txt", ".pdf"}:
            continue
        if path.suffix.lower() == ".pdf":
            templates.append((path, "binary"))
            continue
        templates.append((path, path.read_text(encoding="utf-8")))
    if not templates:
        raise RuntimeError(f"No supported templates found in {source_dir}.")
    return templates


def _build_generated_files(count: int, templates: list[tuple[Path, str]], temp_dir: Path) -> list[Path]:
    generated: list[Path] = []
    for index in range(count):
        template_path, content = templates[index % len(templates)]
        destination = temp_dir / f"{template_path.stem}-{index + 1:03d}{template_path.suffix.lower()}"
        if template_path.suffix.lower() == ".pdf":
            destination.write_bytes(template_path.read_bytes())
        else:
            assert isinstance(content, str)
            destination.write_text(
                (
                    f"# Knowledge Hub Bulk Upload Fixture {index + 1}\n\n"
                    f"Source template: {template_path.name}\n"
                    f"Generated batch key: {slugify(template_path.stem)}-{index + 1:03d}\n\n"
                    f"{content}\n"
                ),
                encoding="utf-8",
            )
        generated.append(destination)
    return generated


async def _upload_file(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    token: str,
    file_path: Path,
    semaphore: asyncio.Semaphore,
) -> UploadResult:
    async with semaphore:
        started = perf_counter()
        content_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else (
            "text/markdown" if file_path.suffix.lower() == ".md" else "text/plain"
        )
        files = {"file": (file_path.name, file_path.read_bytes(), content_type)}
        response = await client.post(
            f"{base_url.rstrip('/')}/api/documents/upload",
            headers=build_backend_headers(token),
            files=files,
        )
        duration_ms = (perf_counter() - started) * 1000
        detail: str | None = None
        document_status: str | None = None
        try:
            payload = response.json()
            detail = payload.get("detail")
            document_status = payload.get("status")
        except Exception:
            detail = response.text[:200]
        return UploadResult(
            file_name=file_path.name,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            success=response.status_code == 201 and document_status == "indexed",
            document_status=document_status,
            detail=detail,
        )


async def run_bulk_upload(args: argparse.Namespace) -> dict[str, Any]:
    source_dir = Path(args.source_dir)
    templates = _load_templates(source_dir)
    auth = await sign_in_with_supabase(
        email=args.email,
        password=args.password,
        supabase_url=args.supabase_url,
        supabase_anon_key=args.supabase_anon_key,
    )

    with tempfile.TemporaryDirectory(prefix="knowledge-hub-bulk-") as temp_directory:
        temp_dir = Path(temp_directory)
        generated_files = _build_generated_files(args.count, templates, temp_dir)
        semaphore = asyncio.Semaphore(max(1, args.concurrency))
        async with httpx.AsyncClient(timeout=120.0) as client:
            results = await asyncio.gather(
                *[
                    _upload_file(
                        client,
                        base_url=args.base_url,
                        token=auth.access_token,
                        file_path=file_path,
                        semaphore=semaphore,
                    )
                    for file_path in generated_files
                ]
            )

    durations = [result.duration_ms for result in results]
    successes = [result for result in results if result.success]
    failures = [result for result in results if not result.success]
    status_breakdown: dict[str, int] = {}
    for result in results:
        key = result.document_status or f"http_{result.status_code}"
        status_breakdown[key] = status_breakdown.get(key, 0) + 1

    metrics = {
        "requested_files": args.count,
        "uploaded_files": len(successes),
        "failed_files": len(failures),
        "upload_success_rate": round(len(successes) / len(results), 4) if results else 0.0,
        "indexing_success_rate": round(
            sum(1 for result in results if result.document_status == "indexed") / len(results), 4
        )
        if results
        else 0.0,
        "average_upload_time_ms": round(statistics.fmean(durations), 2) if durations else 0.0,
        "p95_upload_time_ms": round(_percentile(durations, 0.95), 2),
        "status_breakdown": status_breakdown,
    }
    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "source_dir": str(source_dir),
        "metrics": metrics,
        "results": [result.__dict__ for result in results],
    }
    write_json_report(Path(args.output), artifact)
    return artifact


def print_summary(artifact: dict[str, Any]) -> None:
    metrics = artifact["metrics"]
    print("Knowledge Hub bulk upload summary")
    print(f"- Requested files: {metrics['requested_files']}")
    print(f"- Successful uploads: {metrics['uploaded_files']}")
    print(f"- Failed uploads: {metrics['failed_files']}")
    print(f"- Upload success rate: {metrics['upload_success_rate'] * 100:.1f}%")
    print(f"- Indexing success rate: {metrics['indexing_success_rate'] * 100:.1f}%")
    print(f"- Average upload time: {metrics['average_upload_time_ms']:.1f} ms")
    print(f"- p95 upload time: {metrics['p95_upload_time_ms']:.1f} ms")
    print(f"- Status breakdown: {metrics['status_breakdown']}")


async def main() -> None:
    args = parse_args()
    artifact = await run_bulk_upload(args)
    print_summary(artifact)


if __name__ == "__main__":
    asyncio.run(main())
