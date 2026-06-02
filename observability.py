import os
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

_instrumented = False


def init_tracing():
    """Initialise Phoenix cloud tracing. Call once at app startup."""
    global _instrumented

    api_key = os.environ.get("PHOENIX_API_KEY")
    if not api_key:
        raise EnvironmentError("PHOENIX_API_KEY is not set. Add it to your .env file.")

    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        raise EnvironmentError("PHOENIX_COLLECTOR_ENDPOINT is not set. Add it to your .env file.")

    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(
                endpoint=endpoint,
                headers={"api_key": api_key},
            )
        )
    )

    if not _instrumented:
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        _instrumented = True
