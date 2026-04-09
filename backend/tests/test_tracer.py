import pytest

from app.services.observability import tracer


class FakeRunTree:
    def __init__(self, *args, **kwargs):
        self.created = {"args": args, "kwargs": kwargs}
        self.ended_with = None
        self.patched = False

    def post(self):
        return None

    def create_child(self, *args, **kwargs):
        return FakeRunTree(*args, **kwargs)

    def end(self, **kwargs):
        self.ended_with = kwargs

    def patch(self):
        self.patched = True


@pytest.mark.anyio
async def test_trace_service_disabled_degrades_cleanly(monkeypatch) -> None:
    monkeypatch.setattr(tracer.settings, "langsmith_tracing", False)
    service = tracer.TraceService()

    async with service.trace("disabled-trace") as span:
        span.add_metadata(example=True)
        span.set_outputs(status="ok")

    assert service.enabled is False


@pytest.mark.anyio
async def test_trace_service_enabled_records_run(monkeypatch) -> None:
    monkeypatch.setattr(tracer.settings, "langsmith_tracing", True)
    monkeypatch.setattr(tracer.settings, "langsmith_api_key", "test-key")
    monkeypatch.setattr(tracer, "Client", lambda **kwargs: object())
    monkeypatch.setattr(tracer, "RunTree", FakeRunTree)

    service = tracer.TraceService()

    async with service.trace("enabled-trace", metadata={"source": "test"}) as span:
        span.add_metadata(retrieval_count=2)
        span.set_outputs(status="ok")

    assert service.enabled is True
    assert span.run_tree is not None
    assert span.run_tree.ended_with is not None
    assert span.run_tree.ended_with["outputs"]["status"] == "ok"
    assert span.run_tree.patched is True
