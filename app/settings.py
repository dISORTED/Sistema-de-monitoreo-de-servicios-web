# app/settings.py
import os
from typing import List

def _split_csv(v: str | None) -> List[str]:
    return [x.strip() for x in v.split(",")] if v else []

class Settings:
    TARGETS: List[str] = _split_csv(os.getenv("TARGETS", "https://www.google.com"))
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "site-monitor")
    # Endpoint base por región (sin / al final). Ej: https://otlp-gateway-prod-sa-east-1.grafana.net
    OTLP_ENDPOINT_BASE: str = os.getenv("GRAFANA_CLOUD_OTLP_ENDPOINT", "")
    GRAFANA_CLOUD_INSTANCE_ID: str = os.getenv("GRAFANA_CLOUD_INSTANCE_ID", "")
    GRAFANA_CLOUD_API_TOKEN: str = os.getenv("GRAFANA_CLOUD_API_TOKEN", "")

settings = Settings()

