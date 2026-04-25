"""
Aegis — SSE Event Bus

Replaces the old DB-polling SSE approach (1 DB query/second per client)
with a push-based in-memory queue.

How it works:
- The orchestrator calls event_bus.publish(scan_data) after every status change
- Each connected SSE client has its own asyncio.Queue
- The SSE generator just waits on its queue — zero DB reads
- A 30-second keepalive ping prevents connection timeouts

This means:
- Updates are instant (no 1-second delay)
- No DB load from SSE clients
- All browser tabs receive updates simultaneously
"""

import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ScanEventBus:
    """
    In-memory pub/sub bus for scan status updates.

    Publishers: orchestrator (calls publish after every DB write)
    Subscribers: SSE endpoint (one Queue per connected browser tab)
    """

    def __init__(self):
        # Global subscribers receive ALL scan updates
        self._global_queues: List[asyncio.Queue] = []
        # Per-scan subscribers receive updates for one specific scan
        self._scan_queues: Dict[int, List[asyncio.Queue]] = {}

    def subscribe(self, scan_id: Optional[int] = None) -> asyncio.Queue:
        """
        Register a new SSE client and return its queue.
        Call unsubscribe() when the client disconnects.

        Args:
            scan_id: if provided, only receive updates for this scan.
                     if None, receive all scan updates.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        if scan_id is not None:
            self._scan_queues.setdefault(scan_id, []).append(queue)
        else:
            self._global_queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue, scan_id: Optional[int] = None):
        """Remove a client's queue when they disconnect."""
        if scan_id is not None:
            if scan_id in self._scan_queues:
                self._scan_queues[scan_id] = [
                    q for q in self._scan_queues[scan_id] if q is not queue
                ]
        else:
            self._global_queues = [q for q in self._global_queues if q is not queue]

    async def publish(self, scan_data: dict):
        """
        Push a scan update to all relevant subscribers.
        Drops the event silently if a client's queue is full (slow consumer).
        """
        scan_id = scan_data.get("id")

        # Notify global subscribers (dashboard live feed)
        for queue in list(self._global_queues):
            try:
                queue.put_nowait(scan_data)
            except asyncio.QueueFull:
                pass  # slow consumer — drop oldest, keep newest

        # Notify scan-specific subscribers (scan detail page)
        if scan_id and scan_id in self._scan_queues:
            for queue in list(self._scan_queues[scan_id]):
                try:
                    queue.put_nowait(scan_data)
                except asyncio.QueueFull:
                    pass


# Single global instance — shared across the whole app
event_bus = ScanEventBus()
