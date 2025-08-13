# Site Monitor (FastAPI + OTel + Docker + Railway)

Monitorea endpoints web (HTTP) en paralelo, expone un API con el estado y envía **métricas** a **Grafana Cloud** vía OTLP. Costo cero: GitHub + Docker + Railway (free) + Grafana Cloud (free).

## Características
- Chequeos concurrentes de URLs (status y latencia).
- API:
  - `GET /health` → estado del servicio.
  - `GET /targets` → snapshot de disponibilidad y latencia por URL.
- Métricas OpenTelemetry → Grafana Cloud:
  - `target_up` (1/0 por objetivo)
  - `target_latency_ms` (histograma ms)
- Contenedor Docker listo para Railway/Koyeb.
- Sin alertas por Telegram (clean).

## Estructura

## Variables de entorno
> No crees variables vacías. Si no usas Grafana, no declares las de OTLP.

Obligatorias:
- `TARGETS` → lista separada por comas  
  Ej: `https://httpstat.us/200,https://httpstat.us/503`
- `CHECK_INTERVAL_SECONDS` → `60` (recomendado 30–60)
- `SERVICE_NAME` → `site-monitor` (o el nombre que quieras)

Opcionales (Grafana Cloud):
- `GRAFANA_CLOUD_OTLP_ENDPOINT` → `https://otlp-gateway-<stack>.grafana.net/otlp`
- `GRAFANA_CLOUD_API_TOKEN` → API key con permisos de “MetricsPublisher”

## Ejecutar local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export TARGETS="https://httpstat.us/200,https://httpstat.us/503"
export CHECK_INTERVAL_SECONDS=15
# export GRAFANA_CLOUD_OTLP_ENDPOINT=...
# export GRAFANA_CLOUD_API_TOKEN=...

uvicorn app.main:app --reload
# http://127.0.0.1:8000/targets