"""
WebSocket connection manager for real-time scan progress.

Usage:
    manager = ConnectionManager()

    # In the WS endpoint:
    await manager.connect(scan_id, websocket)

    # From the scanner (sync context, called via asyncio):
    await manager.broadcast(scan_id, {"type": "progress", "percent": 42, "stage": "Hashing files..."})
"""

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # scan_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, scan_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[scan_id].append(ws)

    def disconnect(self, scan_id: str, ws: WebSocket) -> None:
        try:
            self._connections[scan_id].remove(ws)
        except ValueError:
            pass

    async def broadcast(self, scan_id: str, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections.get(scan_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(scan_id, ws)


# Singleton used by the router and scanner
manager = ConnectionManager()


def broadcast_sync(scan_id: str, message: dict[str, Any]) -> None:
    """
    Fire-and-forget broadcast from synchronous code.
    Schedules the coroutine on the running event loop.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.broadcast(scan_id, message))
    except RuntimeError:
        pass
