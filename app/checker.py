# app/checker.py
import asyncio
import time
from typing import Dict, Tuple

import httpx

from app.settings import settings

# ===== OpenTelemetry (métricas a Grafana Cloud) =====
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

# Configurar proveedor de métricas si hay endpoint/token
_meter = None
_status_cache: Dict[str, bool] = {}       # Último estado (True=up, False=down)
_notified_down: Dict[str, bool] = {}      # Para notificar una sola vez por transición
_last_latency_ms: Dict[str, float] = {}   # Última latencia por URL

def setup_metrics():
    global _meter, gauge_up, hist_latency

    if settings.OTLP_ENDPOINT and settings.GRAFANA_CLOUD_API_TOKEN:
        resource = Resource.create({"service.name": settings.SERVICE_NAME})
        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=settings.OTLP_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.GRAFANA_CLOUD_API_TOKEN}"},
                timeout=10_000,
            ),
            export_interval_millis=15000,  # 15s
        )
        provider = MeterProvider(metric_readers=[reader], resource=resource)
        metrics.set_meter_provider(provider)
    else:
        provider = MeterProvider(resource=Resource.create({"service.name": settings.SERVICE_NAME}))
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

async def _notify_telegram(text: str):
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID):
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": True},
            )
    except Exception:
        # Si falla, no rompemos el loop de monitoreo.
        pass

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
        _notified_down[url] = False
        _last_latency_ms[url] = 0.0

    while True:
        tasks = [asyncio.create_task(_check_one(url)) for url in settings.TARGETS]
        results = await asyncio.gather(*tasks)

        for url, (ok, ms, code) in zip(settings.TARGETS, results):
            _status_cache[url] = ok
            _last_latency_ms[url] = ms
            # Registra latencia
            hist_latency.record(ms, {"target": url, "status_code": code})

            # Alertas a Telegram por transición
            if not ok and not _notified_down.get(url, False):
                _notified_down[url] = True
                await _notify_telegram(f"⚠️ Caída detectada: {url} (status={code}, {ms:.0f} ms)")
            elif ok and _notified_down.get(url, False):
                _notified_down[url] = False
                await _notify_telegram(f"✅ Recuperado: {url} (status={code}, {ms:.0f} ms)")

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
