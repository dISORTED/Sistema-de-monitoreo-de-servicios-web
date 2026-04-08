import asyncio
from contextlib import asynccontextmanager, suppress
from html import escape
from statistics import fmean

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.checker import get_last_checked_at, get_snapshot, monitor_loop, run_checks
from app.settings import settings


def _needs_refresh(snapshot: list[dict]) -> bool:
    return not snapshot or not any(item["checked_at"] for item in snapshot)


async def _load_snapshot(refresh: bool) -> list[dict]:
    snapshot = get_snapshot()
    if refresh or _needs_refresh(snapshot):
        snapshot = await run_checks()
    return snapshot


def _cron_is_authorized(request: Request) -> bool:
    if not settings.CRON_SECRET:
        return True
    return request.headers.get("authorization") == f"Bearer {settings.CRON_SECRET}"


def _render_dashboard(snapshot: list[dict]) -> str:
    total = len(snapshot)
    up_count = sum(1 for item in snapshot if item["up"])
    down_count = total - up_count
    avg_latency = round(fmean(item["last_latency_ms"] for item in snapshot), 2) if snapshot else 0.0
    checked_at = snapshot[0]["checked_at"] if snapshot else None

    rows = []
    for item in snapshot:
        state_label = "UP" if item["up"] else "DOWN"
        state_class = "up" if item["up"] else "down"
        status_code = item["status_code"] or "-"
        rows.append(
            """
            <tr>
              <td class="target">{target}</td>
              <td><span class="pill {state_class}">{state_label}</span></td>
              <td>{status_code}</td>
              <td>{latency} ms</td>
            </tr>
            """.format(
                target=escape(item["target"]),
                state_class=state_class,
                state_label=state_label,
                status_code=status_code,
                latency=item["last_latency_ms"],
            )
        )

    empty_state = """
        <tr>
          <td colspan="4">No targets configured. Set the TARGETS environment variable.</td>
        </tr>
    """

    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Site Monitor</title>
        <style>
          :root {{
            --bg: #f6f1e8;
            --panel: rgba(255, 252, 246, 0.85);
            --text: #1b1f23;
            --muted: #5e6a72;
            --line: rgba(27, 31, 35, 0.12);
            --up: #1d7f5f;
            --down: #c24d2c;
            --accent: #0f766e;
          }}
          * {{
            box-sizing: border-box;
          }}
          body {{
            margin: 0;
            min-height: 100vh;
            font-family: "Aptos", "Segoe UI", sans-serif;
            color: var(--text);
            background:
              radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 28%),
              radial-gradient(circle at right center, rgba(194, 77, 44, 0.12), transparent 22%),
              linear-gradient(160deg, #f7f0e4 0%, #f3f6f1 100%);
          }}
          main {{
            width: min(1100px, calc(100% - 32px));
            margin: 40px auto;
          }}
          .hero {{
            padding: 32px;
            border: 1px solid var(--line);
            border-radius: 28px;
            background: var(--panel);
            backdrop-filter: blur(12px);
            box-shadow: 0 24px 60px rgba(27, 31, 35, 0.08);
          }}
          .eyebrow {{
            margin: 0 0 10px;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-size: 12px;
            color: var(--accent);
          }}
          h1 {{
            margin: 0;
            font-size: clamp(34px, 6vw, 62px);
            line-height: 0.96;
          }}
          .subcopy {{
            margin: 14px 0 0;
            max-width: 720px;
            color: var(--muted);
            font-size: 17px;
            line-height: 1.6;
          }}
          .meta {{
            margin-top: 18px;
            color: var(--muted);
            font-size: 14px;
          }}
          .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-top: 24px;
          }}
          .card {{
            padding: 18px;
            border-radius: 20px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.58);
          }}
          .label {{
            display: block;
            margin-bottom: 8px;
            color: var(--muted);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }}
          .value {{
            font-size: 30px;
            font-weight: 700;
          }}
          .table-wrap {{
            margin-top: 18px;
            overflow: hidden;
            border-radius: 24px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.8);
          }}
          table {{
            width: 100%;
            border-collapse: collapse;
          }}
          th,
          td {{
            padding: 16px 20px;
            border-bottom: 1px solid var(--line);
            text-align: left;
          }}
          th {{
            font-size: 13px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
          }}
          tr:last-child td {{
            border-bottom: none;
          }}
          .target {{
            font-weight: 600;
            word-break: break-word;
          }}
          .pill {{
            display: inline-flex;
            align-items: center;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.08em;
          }}
          .pill.up {{
            color: var(--up);
            background: rgba(29, 127, 95, 0.12);
          }}
          .pill.down {{
            color: var(--down);
            background: rgba(194, 77, 44, 0.12);
          }}
          .actions {{
            display: flex;
            gap: 12px;
            margin-top: 22px;
            flex-wrap: wrap;
          }}
          .action {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 18px;
            border-radius: 999px;
            color: white;
            background: var(--accent);
            text-decoration: none;
            font-weight: 600;
          }}
          .action.secondary {{
            color: var(--text);
            background: rgba(15, 118, 110, 0.1);
          }}
          @media (max-width: 720px) {{
            main {{
              width: min(100% - 20px, 1100px);
              margin: 20px auto;
            }}
            .hero {{
              padding: 22px;
              border-radius: 22px;
            }}
            th,
            td {{
              padding: 14px;
              font-size: 14px;
            }}
          }}
        </style>
      </head>
      <body>
        <main>
          <section class="hero">
            <p class="eyebrow">Observability Snapshot</p>
            <h1>Site Monitor</h1>
            <p class="subcopy">
              FastAPI + OpenTelemetry + Grafana Cloud. This view is designed to help you
              validate targets quickly and capture clean screenshots for your portfolio.
            </p>
            <p class="meta">
              Last check: {escape(checked_at or "Pending first run")}<br />
              Mode: {"background loop" if settings.ENABLE_BACKGROUND_MONITOR else "on-demand / Vercel ready"}
            </p>

            <div class="summary">
              <article class="card">
                <span class="label">Targets</span>
                <span class="value">{total}</span>
              </article>
              <article class="card">
                <span class="label">Up</span>
                <span class="value">{up_count}</span>
              </article>
              <article class="card">
                <span class="label">Down</span>
                <span class="value">{down_count}</span>
              </article>
              <article class="card">
                <span class="label">Average latency</span>
                <span class="value">{avg_latency} ms</span>
              </article>
            </div>

            <div class="actions">
              <a class="action" href="/dashboard?refresh=true">Refresh live check</a>
              <a class="action secondary" href="/targets?refresh=true">View JSON</a>
              <a class="action secondary" href="/docs">Open API docs</a>
            </div>

            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Target</th>
                    <th>Status</th>
                    <th>Status code</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {''.join(rows) if rows else empty_state}
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </body>
    </html>
    """


@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor_task = None

    if settings.ENABLE_BACKGROUND_MONITOR:
        monitor_task = asyncio.create_task(monitor_loop())
        app.state.monitor_task = monitor_task

    try:
        yield
    finally:
        if monitor_task:
            monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await monitor_task


app = FastAPI(title="Site Monitor", version="2.0.0", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(refresh: bool = False):
    snapshot = await _load_snapshot(refresh=refresh)
    return HTMLResponse(_render_dashboard(snapshot))


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(refresh: bool = False):
    snapshot = await _load_snapshot(refresh=refresh)
    return HTMLResponse(_render_dashboard(snapshot))


@app.get("/health")
def health():
    return {
        "ok": True,
        "mode": "background" if settings.ENABLE_BACKGROUND_MONITOR else "on-demand",
        "targets": len(settings.TARGETS),
        "last_checked_at": get_last_checked_at(),
    }


@app.get("/targets")
async def targets(refresh: bool = False):
    snapshot = await _load_snapshot(refresh=refresh)
    return {"data": snapshot, "last_checked_at": get_last_checked_at()}


@app.get("/api/check")
async def run_scheduled_check(request: Request):
    if not _cron_is_authorized(request):
        raise HTTPException(status_code=401, detail="Unauthorized cron request")

    snapshot = await run_checks()
    return {"ok": True, "count": len(snapshot), "last_checked_at": get_last_checked_at(), "data": snapshot}
