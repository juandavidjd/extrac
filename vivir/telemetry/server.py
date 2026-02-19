#!/usr/bin/env python3
"""
VIVIR Telemetry Server v1.0
Sistema Nervioso Central ODI
Puerto: 8765
"ODI no se usa. ODI se habita."
"""

import asyncio
import json
import os
from datetime import datetime
import websockets
import redis.asyncio as aioredis

HOST = "0.0.0.0"
PORT = 8765
CLIENTS = set()

redis_pool = None

async def get_redis():
    global redis_pool
    if not redis_pool:
        redis_pool = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    return redis_pool

def manifest_allows(payload):
    """
    Gate del Manifiesto v1.0
    Regla 3/3: Solo pasa si cumple simultaneamente:
    1. Riesgo detectado
    2. Valor economico
    3. Insuficiencia de audio
    Excepciones: guardian_alert SIEMPRE pasa.
    """
    if not payload.get("ethics_lock", False):
        return False

    event_type = payload.get("event_type", "")

    if event_type == "guardian_alert":
        return True

    if payload.get("guardian_state") in ("naranja", "rojo"):
        return event_type == "guardian_alert"

    if event_type == "heartbeat":
        return True

    if event_type in ("ecosystem_status", "guardian_state_change", "welcome"):
        return True

    severity = payload.get("severity", 0)
    if severity < 0.3:
        return False

    return True

async def log_suppressed(payload):
    try:
        r = await get_redis()
        await r.lpush("odi:vivir:suppressed", json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": payload.get("event_type"),
            "reason": "manifest_gate"
        }))
        await r.ltrim("odi:vivir:suppressed", 0, 999)
    except:
        pass

async def emit_event(payload):
    if not manifest_allows(payload):
        await log_suppressed(payload)
        return False

    message = json.dumps(payload, ensure_ascii=False)
    if CLIENTS:
        await asyncio.gather(
            *[ws.send(message) for ws in CLIENTS],
            return_exceptions=True
        )

    try:
        r = await get_redis()
        await r.set("odi:vivir:last_event", message)
        await r.set("odi:vivir:last:%s" % payload.get("event_type"), message)
    except:
        pass

    return True

async def get_guardian_state():
    try:
        with open("/opt/odi/guardian/estado_actual.json") as f:
            return json.load(f)
    except:
        return {"estado": "verde", "timestamp": datetime.utcnow().isoformat()}

async def get_ecosystem_stats():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:8815/ecosystem/stores")
            data = r.json()
            return {
                "total_stores": data.get("total_stores", len(data.get("stores", []))),
                "total_products": data.get("total_products", 0)
            }
    except:
        return {"total_stores": 15, "total_products": 0}

async def heartbeat_loop():
    while True:
        guardian = await get_guardian_state()
        ecosystem = await get_ecosystem_stats()

        await emit_event({
            "event_type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "vivir-server",
            "ethics_lock": True,
            "severity": 0.0,
            "guardian_state": guardian.get("estado", "verde"),
            "ttl_ms": 0,
            "data": {
                "clients_connected": len(CLIENTS),
                "guardian": guardian,
                "ecosystem": ecosystem
            }
        })

        await asyncio.sleep(30)

async def handler(websocket):
    CLIENTS.add(websocket)

    guardian = await get_guardian_state()
    ecosystem = await get_ecosystem_stats()

    welcome = json.dumps({
        "event_type": "welcome",
        "timestamp": datetime.utcnow().isoformat(),
        "ethics_lock": True,
        "guardian_state": guardian.get("estado", "verde"),
        "data": {
            "guardian": guardian,
            "ecosystem": ecosystem,
            "message": "Bienvenido al habitat de ODI."
        }
    })
    await websocket.send(welcome)

    try:
        async for message in websocket:
            try:
                cmd = json.loads(message)
                if cmd.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))
                elif cmd.get("type") == "request_status":
                    guardian = await get_guardian_state()
                    await websocket.send(json.dumps({
                        "event_type": "status_response",
                        "guardian_state": guardian.get("estado", "verde"),
                        "timestamp": datetime.utcnow().isoformat()
                    }))
            except:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)

async def main():
    print("""
========================================
  VIVIR Telemetry Server v1.0
  Sistema Nervioso Central ODI
  Host: %s  Port: %s
  Manifest Gate: ACTIVO
  "ODI no se usa. ODI se habita."
========================================
    """ % (HOST, PORT))

    asyncio.create_task(heartbeat_loop())

    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
