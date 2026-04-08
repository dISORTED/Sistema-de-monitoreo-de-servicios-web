import asyncio
import base64
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import httpx
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_meter = None
_provider: MeterProvider | None = None
_metrics_ready = False
_run_lock: asyncio.Lock | None = None

_status_cache: Dict[str, bool] = {}
_last_latency_ms: Dict[str, float] = {}
_last_status_code: Dict[str, int] = {}
_last_checked_at: str | None = None


def _get_run_lock() -> asyncio.Lock:
    global _run_lock
    if _run_lock is None:
        _run_lock = asyncio.Lock()
    return _run_lock


def setup_metrics() -> None:
    global _meter, _provider, _metrics_ready, gauge_up, hist_latency

    if _metrics_ready:
        return

    resource = Resource.create({"service.name": settings.SERVICE_NAME})
    readers = []

    if (
        settings.OTLP_ENDPOINT_BASE
        and settings.GRAFANA_CLOUD_INSTANCE_ID
        and settings.GRAFANA_CLOUD_API_TOKEN
    ):
        raw = f"{settings.GRAFANA_CLOUD_INSTANCE_ID}:{settings.GRAFANA_CLOUD_API_TOKEN}"
        basic = base64.b64encode(raw.encode()).decode()
        base = settings.OTLP_ENDPOINT_BASE.rstrip("/")

        exporter = OTLPMetricExporter(
            endpoint=f"{base}/v1/metrics",
            headers={"Authorization": f"Basic {basic}"},
            timeout=10_000,
        )
        readers.append(PeriodicExportingMetricReader(exporter, export_interval_millis=15_000))

    _provider = MeterProvider(metric_readers=readers, resource=resource)
    metrics.set_meter_provider(_provider)
    _meter = metrics.get_meter("site-monitor")

    def _observe_up_callback(options):
        from opentelemetry.metrics import Observation  # type: ignore

        observations = []
        for url in settings.TARGETS:
            value = 1 if _status_cache.get(url, False) else 0
            observations.append(Observation(value, {"target": url}))
        return observations

    gauge_up = _meter.create_observable_gauge(
        name="target_up",
        callbacks=[_observe_up_callback],
        unit="1",
        description="Availability by target (1 up, 0 down)",
    )

    hist_latency = _meter.create_histogram(
        name="target_latency_ms",
        unit="ms",
        description="HTTP latency by target",
    )

    _metrics_ready = True


def _ensure_target_state(urls: List[str]) -> None:
    for url in urls:
        _status_cache.setdefault(url, False)
        _last_latency_ms.setdefault(url, 0.0)
        _last_status_code.setdefault(url, 0)


async def _check_one(client: httpx.AsyncClient, url: str) -> Tuple[bool, float, int]:
    started = time.perf_counter()
    status_code = 0

    try:
        response = await client.get(url)
        status_code = response.status_code
        ok = 200 <= status_code < 400
    except Exception:
        ok = False

    latency_ms = (time.perf_counter() - started) * 1000.0
    return ok, latency_ms, status_code


async def run_checks(urls: List[str] | None = None) -> List[dict]:
    setup_metrics()
    target_urls = urls or settings.TARGETS

    if not target_urls:
        return []

    async with _get_run_lock():
        _ensure_target_state(target_urls)

        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            tasks = [_check_one(client, url) for url in target_urls]
            results = await asyncio.gather(*tasks)

        checked_at = datetime.now(timezone.utc).isoformat()

        for url, (ok, latency_ms, status_code) in zip(target_urls, results):
            previous_status = _status_cache.get(url)
            _status_cache[url] = ok
            _last_latency_ms[url] = latency_ms
            _last_status_code[url] = status_code

            hist_latency.record(latency_ms, {"target": url, "status_code": status_code})

            if previous_status is not None and previous_status != ok:
                if ok:
                    logging.info("RECOVERED %s (status=%s, %.0f ms)", url, status_code, latency_ms)
                else:
                    logging.warning("DOWN %s (status=%s, %.0f ms)", url, status_code, latency_ms)

        global _last_checked_at
        _last_checked_at = checked_at

        if _provider is not None:
            _provider.force_flush()

        return get_snapshot(target_urls)


async def monitor_loop() -> None:
    while True:
        await run_checks()
        await asyncio.sleep(settings.CHECK_INTERVAL_SECONDS)


def get_snapshot(urls: List[str] | None = None) -> List[dict]:
    target_urls = urls or settings.TARGETS
    snapshot = []

    for url in target_urls:
        snapshot.append(
            {
                "target": url,
                "up": _status_cache.get(url, False),
                "last_latency_ms": round(_last_latency_ms.get(url, 0.0), 2),
                "status_code": _last_status_code.get(url, 0),
                "checked_at": _last_checked_at,
            }
        )

    return snapshot


def get_last_checked_at() -> str | None:
    return _last_checked_at
