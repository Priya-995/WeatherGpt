"""
WebSocket endpoint for real-time alert push.

Endpoint
--------
WS  /ws/alerts   → subscribe to live alert broadcasts

Protocol
--------
- Client connects.  Server immediately sends a "connected" handshake JSON.
- When a new alert is ingested (via POST /api/alerts/ingest or the IMD feed),
  all connected clients receive a JSON message:
    {"event": "new_alert", "alert": <Alert as dict>}
- Clients can optionally send a JSON ping:
    {"action": "ping"}
  Server replies:
    {"event": "pong", "connected_clients": <int>}
- On disconnect the client is cleanly removed.

Connection manager
------------------
A simple in-memory ConnectionManager tracks active WebSocket connections.
Section 8: for multi-process deployments, replace the in-memory set with a
Redis pub/sub channel so broadcasts reach clients on all worker processes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.alert import Alert

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# ---------------------------------------------------------------------------
# Connection manager
# TODO (Section 8): replace with Redis pub/sub for multi-process support
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Tracks active WebSocket connections and handles broadcast."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def send_json(self, ws: WebSocket, payload: dict) -> None:
        """Send to a single client; silently drop if connection is dead."""
        try:
            await ws.send_json(payload)
        except Exception as exc:
            logger.debug("WS send failed (client likely gone): %s", exc)
            self.disconnect(ws)

    async def broadcast(self, payload: dict) -> None:
        """Broadcast a JSON payload to all connected clients concurrently."""
        if not self._connections:
            return
        dead: Set[WebSocket] = set()
        results = await asyncio.gather(
            *[ws.send_json(payload) for ws in self._connections],
            return_exceptions=True,
        )
        for ws, result in zip(list(self._connections), results):
            if isinstance(result, Exception):
                logger.debug("Dropping dead WS connection: %s", result)
                dead.add(ws)
        self._connections -= dead

    @property
    def client_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Public helper — called by alerts.py router after ingesting a new alert
# ---------------------------------------------------------------------------

async def broadcast_alert(alert: Alert) -> None:
    """Broadcast a new alert to all connected /ws/alerts subscribers."""
    payload = {
        "event": "new_alert",
        "alert": alert.model_dump(mode="json"),
    }
    await manager.broadcast(payload)
    logger.info(
        "Alert %s broadcast to %d WS client(s)", alert.id, manager.client_count
    )


# ---------------------------------------------------------------------------
# WebSocket route
# ---------------------------------------------------------------------------

@router.websocket("/ws/alerts")
async def alerts_websocket(ws: WebSocket) -> None:
    """
    WebSocket endpoint — subscribe to live alert broadcasts.

    Send {"action": "ping"} to check connectivity.
    Receive {"event": "new_alert", "alert": {...}} when alerts are issued.
    """
    await manager.connect(ws)

    # Send immediate handshake
    await ws.send_json({
        "event": "connected",
        "message": "Subscribed to WeatherGPT alert stream.",
        "connected_clients": manager.client_count,
    })

    try:
        while True:
            # Wait for messages from the client (ping, etc.)
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"event": "error", "detail": "Invalid JSON"})
                continue

            if msg.get("action") == "ping":
                await ws.send_json({
                    "event": "pong",
                    "connected_clients": manager.client_count,
                })
            else:
                await ws.send_json({
                    "event": "error",
                    "detail": f"Unknown action: {msg.get('action')}",
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)
