# app/checker.py
import asyncio
import time
import logging
import base64
from typing import Dict, Tuple

import httpx

from app.settings import settings

# ===== OpenTelemetry (métricas a Grafana Cloud) =====
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_meter = None
_status_cache: Dict[str, bool] = {}       # Último estado (True=up, False=down)
_last_latency_ms: Dict[str, float] = {}   # Última latencia por URL

def setup_metrics():
    """
    Configura el proveedor de métricas.
    - Si hay vars de Grafana Cloud: exporta por OTLP/HTTP usando Basic Auth (instance_id:api_key) a /v1/metrics
    - Si no: crea un proveedor local (las métricas no salen de la app)
    """
    global _meter, gauge_up, hist_latency

    resource = Resource.create({"service.name": settings.SERVICE_NAME})

    readers = []
    if (
        settings.OTLP_ENDPOINT_BASE
        and settings.GRAFANA_CLOUD_INSTANCE_ID
        and settings.GRAFANA_CLOUD_API_TOKEN
    ):
        # Basic Auth = base64(instance_id:api_key)
        raw = f"{settings.GRAFANA_CLOUD_INSTANCE_ID}:{settings.GRAFANA_CLOUD_API_TOKEN}"
        basic = base64.b64encode(raw.encode()).decode()
        base = settings.OTLP_ENDPOINT_BASE.rstrip("/")

        exporter = OTLPMetricExporter(
            endpoint=f"{base}/v1/metrics",
            headers={"Authorization": f"Basic {basic}"},
            timeout=10_000,
        )
        readers.append(PeriodicExportingMetricReader(exporter, export_interval_millis=15000))

    if readers:
        provider = MeterProvider(metric_readers=readers, resource=resource)
    else:
        provider = MeterProvider(resource=resource)

    metrics.set_meter_provider(provider)
    _meter = metrics.get_meter("site-monitor")

    # Métrica observable de disponibilidad: 1=up, 0=down
    def _observe_up_callback(options):
        from opentelemetry.metrics import Observation  # type: ignore
        out = []
        for url in settings.TARGETS:
            val = 1 if _status_cache.get(url, False) else 0
            out.append(Observation(val, {"target": url}))
        return out

    global gauge_up
    gauge_up = _meter.create_observable_gauge(
        name="target_up",
        callbacks=[_observe_up_callback],
        unit="1",
        description="Disponibilidad por target (1 up, 0 down)",
    )

    # Histograma de latencia en ms
    global hist_latency
    hist_latency = _meter.create_histogram(
        name="target_latency_ms",
        unit="ms",
        description="Latencia HTTP por target",
    )

async def _check_one(url: str) -> Tuple[bool, float, int]:
    t0 = time.perf_counter()
    code = 0
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            code = resp.status_code
            ok = 200 <= code < 400
    except Exception:
        ok = False
    ms = (time.perf_counter() - t0) * 1000.0
    return ok, ms, code

async def monitor_loop():
    setup_metrics()
    # Inicializa caches
    for url in settings.TARGETS:
        _status_cache[url] = False
        _last_latency_ms[url] = 0.0

    while True:
        tasks = [asyncio.create_task(_check_one(url)) for url in settings.TARGETS]
        results = await asyncio.gather(*tasks)

        for url, (ok, ms, code) in zip(settings.TARGETS, results):
            old = _status_cache.get(url, None)
            _status_cache[url] = ok
            _last_latency_ms[url] = ms

            # Registra latencia
            hist_latency.record(ms, {"target": url, "status_code": code})

            # Loguea transición
            if old is not None and old != ok:
                if ok:
                    logging.info("RECUPERADO %s (status=%s, %.0f ms)", url, code, ms)
                else:
                    logging.warning("CAÍDA %s (status=%s, %.0f ms)", url, code, ms)

        await asyncio.sleep(settings.CHECK_INTERVAL_SECONDS)

def get_snapshot():
    # Para endpoints de API
    out = []
    for url in settings.TARGETS:
        out.append({
            "target": url,
            "up": _status_cache.get(url, False),
            "last_latency_ms": round(_last_latency_ms.get(url, 0.0), 2),
        })
    return out
