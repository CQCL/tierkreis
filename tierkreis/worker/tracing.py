from contextlib import AbstractContextManager, contextmanager, nullcontext
from importlib.util import find_spec
from typing import Iterator

try:
    _TRACING = (
        find_spec("opentelemetry.context") and find_spec("opentelemetry.trace")
    ) is not None
except ModuleNotFoundError:
    _TRACING = False


def span(_tracer, **kwargs) -> AbstractContextManager:
    if _TRACING:
        return _tracer.start_as_current_span(**kwargs)
    else:
        return nullcontext()


@contextmanager
def context_token(context) -> Iterator[None]:
    if context is None:
        yield
        return
    else:
        import opentelemetry.context

        token = opentelemetry.context.attach(context)
        try:
            yield
        finally:
            opentelemetry.context.detach(token)


def get_tracer(_name: str):
    if _TRACING:
        import opentelemetry.trace

        return opentelemetry.trace.get_tracer(_name)
    return None
