from contextlib import AbstractContextManager, contextmanager, nullcontext
from typing import Iterator

try:
    import opentelemetry.context
    import opentelemetry.trace

    _TRACING = True
except ImportError:
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
        token = opentelemetry.context.attach(context)
        try:
            yield
        finally:
            opentelemetry.context.detach(token)


def get_tracer(_name: str):
    if _TRACING:
        return opentelemetry.trace.get_tracer(_name)
    return None
