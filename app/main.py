# app/main.py
import asyncio
from fastapi import FastAPI
from app.checker import monitor_loop, get_snapshot

app = FastAPI(title="Site Monitor", version="1.0.0")

@app.on_event("startup")
async def _startup():
    asyncio.create_task(monitor_loop())

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/targets")
def targets():
    return {"data": get_snapshot()}
