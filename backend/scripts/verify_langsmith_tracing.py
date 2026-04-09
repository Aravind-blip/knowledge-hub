import asyncio
import json

from app.services.observability.tracer import get_trace_service


async def main() -> None:
    trace_service = get_trace_service()
    async with trace_service.trace(
        "manual_trace_verification",
        metadata={"verification": True},
        inputs={"step": "langsmith"},
    ) as span:
        span.add_metadata(stage="script")
        span.set_outputs(status="ok")

    print(json.dumps({"langsmith_enabled": trace_service.enabled, "verification_run": "manual_trace_verification"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
