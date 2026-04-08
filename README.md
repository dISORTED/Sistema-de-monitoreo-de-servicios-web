# Sistema de monitoreo de servicios web

Proyecto de monitoreo simple para medir latencia y disponibilidad de sitios web usando FastAPI, OpenTelemetry y Grafana Cloud.

## Stack

- Python + FastAPI
- OpenTelemetry Metrics
- Grafana Cloud OTLP
- Docker
- Vercel o Railway

## Que cambio en esta version

La app ahora soporta dos modos:

- `background`: mantiene el loop continuo original y sirve bien en Railway, Docker o una VM.
- `on-demand`: ejecuta chequeos por request o por cron y queda lista para Vercel.

Tambien se agrego:

- Dashboard HTML en `/` y `/dashboard` para screenshots.
- Endpoint de chequeo programable en `/api/check`.
- Entrada `index.py` compatible con FastAPI en Vercel.
- Archivo `vercel.json` con un cron diario seguro para Hobby.

## Endpoints

- `/` dashboard HTML
- `/dashboard` dashboard HTML
- `/targets` snapshot JSON
- `/health` estado de la app
- `/api/check` ejecuta un chequeo y exporta metricas

## Variables de entorno

Puedes usar `.env.example` como base.

- `TARGETS`: lista CSV de URLs a monitorear
- `CHECK_INTERVAL_SECONDS`: intervalo del loop continuo
- `REQUEST_TIMEOUT_SECONDS`: timeout por request saliente
- `ENABLE_BACKGROUND_MONITOR`: `true` para Railway/Docker, `false` para Vercel
- `CRON_SECRET`: secreto opcional para proteger `/api/check`
- `SERVICE_NAME`: nombre del servicio OTEL
- `GRAFANA_CLOUD_OTLP_ENDPOINT`: endpoint base OTLP de Grafana Cloud
- `GRAFANA_CLOUD_INSTANCE_ID`: instance id de Grafana Cloud
- `GRAFANA_CLOUD_API_TOKEN`: token con permisos de metrics:write

## Ejecutar local

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Si quieres el comportamiento antiguo, deja `ENABLE_BACKGROUND_MONITOR=true`.

Para sacar screenshots rapidamente:

- abre `/dashboard?refresh=true`
- abre `/targets?refresh=true`
- usa `/docs` si quieres mostrar la API

## Deploy en Vercel

FastAPI puede desplegarse en Vercel usando `index.py` como entrypoint.

Pasos:

1. Importa el repo en Vercel.
2. Configura las variables de entorno del archivo `.env.example`.
3. Deja `ENABLE_BACKGROUND_MONITOR=false`.
4. Configura `CRON_SECRET` y usa el mismo valor como secret del cron si quieres proteger `/api/check`.
5. Despliega.

Notas importantes:

- El cron incluido en `vercel.json` corre una vez al dia para que el proyecto siga siendo compatible con Vercel Hobby.
- Si usas Vercel Pro, puedes cambiar el cron a algo como `*/5 * * * *` para acercarte mas al comportamiento original de Railway.
- En Vercel no conviene depender de memoria en proceso para mantener un loop infinito.

## Deploy en Railway

Si quieres seguir usando Railway, este repo tambien conserva ese camino:

1. Usa el `Dockerfile`.
2. Define `ENABLE_BACKGROUND_MONITOR=true`.
3. Configura las variables OTLP de Grafana Cloud.

## Tests

```bash
python -m unittest discover -s tests
```
