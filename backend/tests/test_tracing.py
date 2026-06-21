from app.services.tracing import LangSmithTracer, TraceConfig


def test_tracer_runs_function_when_disabled() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=False,
            project_name="test-project",
            endpoint=None,
            api_key=None,
        )
    )

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={"input": "value"},
        metadata={"env": "test"},
        function=lambda: "ok",
    )

    assert result == "ok"


def test_tracer_runs_function_when_enabled_without_api_key() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=True,
            project_name="test-project",
            endpoint=None,
            api_key=None,
        )
    )

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={"input": "value"},
        metadata={"env": "test"},
        function=lambda: "ok",
    )

    assert result == "ok"


def test_tracer_propagates_function_error_when_disabled() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=False,
            project_name="test-project",
            endpoint=None,
            api_key=None,
        )
    )

    def fail() -> str:
        raise ValueError("boom")

    try:
        tracer.trace(
            name="test",
            run_type="chain",
            inputs={},
            metadata={},
            function=fail,
        )
    except ValueError as error:
        assert str(error) == "boom"
    else:
        raise AssertionError("Expected ValueError")


def test_tracer_updates_run_outputs_when_enabled() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=True,
            project_name="test-project",
            endpoint=None,
            api_key="fake-key",
        )
    )

    class FakeClient:
        def __init__(self) -> None:
            self.created_run_id = None
            self.updated_run_id = None
            self.outputs = None

        def create_run(self, **kwargs: object) -> None:
            self.created_run_id = kwargs["id"]

        def update_run(self, run_id: object, **kwargs: object) -> None:
            self.updated_run_id = run_id
            self.outputs = kwargs.get("outputs")

    fake_client = FakeClient()
    tracer.client = fake_client  # type: ignore[assignment]

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={"input": "value"},
        metadata={"env": "test"},
        function=lambda: {"answer": "ok"},
    )

    assert result == {"answer": "ok"}
    assert fake_client.created_run_id == fake_client.updated_run_id
    assert fake_client.outputs is not None
    assert fake_client.outputs["output"] == {"answer": "ok"}


def test_tracer_continues_when_create_run_fails() -> None:
    tracer = LangSmithTracer(
        TraceConfig(
            enabled=True,
            project_name="test-project",
            endpoint=None,
            api_key="fake-key",
        )
    )

    class FakeClient:
        def create_run(self, **kwargs: object) -> None:
            raise RuntimeError("langsmith unavailable")

    tracer.client = FakeClient()  # type: ignore[assignment]

    result = tracer.trace(
        name="test",
        run_type="chain",
        inputs={},
        metadata={},
        function=lambda: "ok",
    )

    assert result == "ok"
