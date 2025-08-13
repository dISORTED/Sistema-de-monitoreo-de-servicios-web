Sistema de Monitoreo de Servicios Web con OpenTelemetry, Prometheus y Grafana Cloud

Este proyecto tiene como objetivo construir una solución de monitoreo simple, eficiente y de bajo costo para evaluar el rendimiento de distintos sitios web mediante el uso de herramientas modernas de observabilidad. La implementación utiliza un exportador personalizado en Python (con FastAPI), OpenTelemetry para la instrumentación, Prometheus como base de datos de series temporales y Grafana Cloud para la visualización de métricas.

🌍 Tecnologías utilizadas

Herramienta

Propósito principal

Python + FastAPI

Exportador de métricas personalizado (medición de latencia HTTP)

OpenTelemetry SDK (Python)

Instrumentación de la aplicación y exportación de métricas

Prometheus (Grafana Cloud)

Recolección de métricas OTLP HTTP (time-series database)

Grafana Cloud

Visualización de dashboards y configuración de alertas

Railway

Plataforma de despliegue cloud para el exportador (gratuito)

GitHub Actions

Automatización CI/CD: test, despliegue y limpieza de secretos

🔄 Arquitectura general

graph TD
    A[Usuario/Desarrollador] --> B[FastAPI App (Railway)]
    B --> C[OpenTelemetry SDK]
    C --> D[OTLP Exporter]
    D --> E[Grafana Cloud Prometheus]
    E --> F[Dashboard Grafana (Latencia p95)]

🔢 Funcionamiento del exportador (FastAPI + OTEL)

Cada cierto intervalo (configurable), la aplicación realiza peticiones HTTP a sitios definidos.

Se registra el tiempo de respuesta de cada sitio, clasificándolo en buckets de latencia en milisegundos (histogram).

Las métricas generadas incluyen:

target_latency_ms_milliseconds_bucket

target_info

Estas se exportan en tiempo real a Grafana Cloud (Prometheus) usando el protocolo OTLP (HTTP).

📊 Dashboard en Grafana: Latencia p95 por sitio

Descripción del panel

Nombre: Latencia p95 por sitio (ultimos 5 minutos)

Query:

histogram_quantile(0.95, sum(rate(target_latency_ms_milliseconds_bucket[5m])) by (le, target))

Actualización: Cada 30 segundos

Etiquetas utilizadas: target, status_code, service_name

Visualización: Panel de líneas por sitio web monitoreado

Objetivo del panel

Este dashboard permite visualizar la latencia p95 (percentil 95) por cada uno de los sitios registrados. Este valor indica que el 95% de las respuestas HTTP fueron menores o iguales a ese tiempo, mostrando tendencias de degradación o mejoras en tiempo real.

Ejemplo de comportamiento observado

https://homer.sii.cl/ con latencias p95 cercanas a 5s

https://sence.gob.cl/ promedio estable cercano a 1s

https://www.stochile.com/ extremadamente rápido, alrededor de 100ms

🚨 Configuración de alertas

Se ha definido una alerta que se dispara cuando la latencia p95 supera un umbral crítico:

Regla de alerta:

Métrica: Latencia p95 por target

Condición: mayor a 3000 ms (3s)

Evaluación: Cada 1 minuto

Persistencia del estado: Al menos 1m consecutivo en condición de alerta

Resultado:

Permite identificar rápidamente cuando un sitio está funcionando lentamente

Se puede extender fácilmente para enviar notificaciones a Slack, correo u otros canales

🛠️ Configuración en Railway

La aplicación está desplegada en Railway como contenedor Docker

Variables de entorno utilizadas:

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT

OTEL_EXPORTER_OTLP_METRICS_ENDPOINT

GRAFANA_CLOUD_API_TOKEN

SERVICE_NAME

🔄 Repositorio y despliegue

Repositorio: https://github.com/dISORTED/Sistema-de-monitoreo-de-servicios-web

CI/CD:

Validaciones automáticas

Push protegido (secret scanning habilitado)

🔧 Posibles mejoras futuras

Agregar métrica de disponibilidad por target (usando up o equivalente)

Exportar status codes por tipo: 2xx, 4xx, 5xx

Implementar trazas (OpenTelemetry Traces)

Registrar visitas reales si se controla el backend (no aplicable para sitios externos)

Integrar con Grafana OnCall para alertas reales

📅 Licencia y uso

Proyecto realizado con fines educativos y de portafolio personal DevOps/Backend.

✅ Autor: Sebastián

✅ Instancia Grafana: https://disorted.grafana.net

✅ Monitoreo en tiempo real: Railway + OTEL + Grafana Cloud
