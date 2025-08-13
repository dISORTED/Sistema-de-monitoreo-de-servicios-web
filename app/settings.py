# app/settings.py
import os
from typing import List

def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]

class Settings:
    # Lista de URLs a monitorear (separadas por comas)
    TARGETS: List[str] = _split_csv(os.getenv("TARGETS", "https://www.google.com"))

    # Intervalo entre rondas de chequeo
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

    # OpenTelemetry / Grafana Cloud OTLP
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "site-monitor")
    OTLP_ENDPOINT: str = os.getenv("GRAFANA_CLOUD_OTLP_ENDPOINT", "")  # p.ej. https://otlp-gateway-<tu-stack>.grafana.net/otlp
    GRAFANA_CLOUD_API_TOKEN: str = os.getenv("GRAFANA_CLOUD_API_TOKEN", "")

    # Telegram (opcional: alertas directas)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

settings = Settings()
