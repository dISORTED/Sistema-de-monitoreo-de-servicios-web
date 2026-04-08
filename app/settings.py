import os
from typing import List


def _split_csv(value: str | None) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()] if value else []


def _get_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    TARGETS: List[str] = _split_csv(os.getenv("TARGETS", "https://www.google.com"))
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

    # Preserva el modo antiguo fuera de Vercel y lo apaga por defecto en Vercel.
    ENABLE_BACKGROUND_MONITOR: bool = _get_bool(
        "ENABLE_BACKGROUND_MONITOR",
        default=os.getenv("VERCEL") is None,
    )
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")

    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "site-monitor")
    # Acepta tanto el nombre propio del proyecto como la variable exacta que entrega Grafana.
    OTLP_ENDPOINT_BASE: str = os.getenv(
        "GRAFANA_CLOUD_OTLP_ENDPOINT",
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
    )
    OTLP_HEADERS: str = os.getenv(
        "GRAFANA_CLOUD_OTLP_HEADERS",
        os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""),
    )
    GRAFANA_CLOUD_INSTANCE_ID: str = os.getenv("GRAFANA_CLOUD_INSTANCE_ID", "")
    GRAFANA_CLOUD_API_TOKEN: str = os.getenv("GRAFANA_CLOUD_API_TOKEN", "")


settings = Settings()
