"""
UrbanPulse — WebSocket Broadcast Hub

Rewritten with per-client bounded queues for backpressure isolation.
A slow client fills its own queue (maxsize=20) and drops messages
instead of blocking every other client.

A central accumulator / throttle loop runs at ~33ms (30fps) and
batches messages before fanning out to clients.
"""
import asyncio
import logging
import time
from typing import Set, Dict

logger = logging.getLogger(__name__)

# Throttle: maximum broadcast rounds per second
BROADCAST_HZ = 30
BROADCAST_INTERVAL_S = 1.0 / BROADCAST_HZ  # ~33ms

# Per-client queue depth — slow clients drop instead of blocking everyone
CLIENT_QUEUE_MAXSIZE = 20


class ClientConnection:
    """Wraps a WebSocket with its own bounded message queue."""

    def __init__(self, websocket):
        self.ws = websocket
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=CLIENT_QUEUE_MAXSIZE)
        self._send_task: asyncio.Task = None

    async def send_loop(self):
        """Background task: drain queue and send to client."""
        try:
            while True:
                msg = await self.queue.get()
                try:
                    await self.ws.send_json(msg)
                except Exception as e:
                    logger.warning("WebSocket send error (client dropped): %s", e)
                    return  # exit loop — caller will clean up
                finally:
                    self.queue.task_done()
        except asyncio.CancelledError:
            pass

    async def enqueue(self, msg: dict) -> bool:
        """Push a message to this client's queue. Returns False if dropped."""
        try:
            self.queue.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            # Client is slow — drop oldest message, push new one
            try:
                self.queue.get_nowait()  # discard oldest
                self.queue.put_nowait(msg)
            except asyncio.QueueEmpty:
                pass
            return False


class BroadcastHub:
    """Throttled hub with per-client bounded queues."""

    def __init__(self):
        self._clients: Dict[int, ClientConnection] = {}
        self._next_id: int = 0
        self._accumulator: list = []
        self._broadcast_task: asyncio.Task = None

    async def connect(self, websocket):
        """Register a new WebSocket client and start its send loop."""
        client = ClientConnection(websocket)
        cid = self._next_id
        self._next_id += 1
        self._clients[cid] = client

        await websocket.accept()

        # Start the per-client send loop as a background task
        client._send_task = asyncio.create_task(
            self._client_send_guard(cid, client),
            name=f"ws-send-{cid}"
        )
        logger.info("WebSocket client %d connected. Total: %d", cid, len(self._clients))

    async def _client_send_guard(self, cid: int, client: ClientConnection):
        """Wrapper that cleans up on any send loop exit."""
        try:
            await client.send_loop()
        except asyncio.CancelledError:
            pass
        finally:
            # Client disconnected — remove from hub
            if cid in self._clients:
                del self._clients[cid]
            logger.info("WebSocket client %d removed. Total: %d", cid, len(self._clients))

    def disconnect(self, websocket):
        """Immediate disconnect — cancel the send task."""
        for cid, client in list(self._clients.items()):
            if client.ws == websocket:
                if client._send_task and not client._send_task.done():
                    client._send_task.cancel()
                if cid in self._clients:
                    del self._clients[cid]
                logger.info("WebSocket client %d disconnected. Total: %d", cid, len(self._clients))
                return

    async def broadcast(self, message: dict):
        """Add a message to the accumulator. Actual send is throttled by the loop."""
        self._accumulator.append(message)

    async def _throttled_loop(self, app_state):
        """Background task: every ~33ms, flush accumulator to all clients."""
        logger.info("Broadcast throttle loop started (target: %d/s)", BROADCAST_HZ)
        try:
            while True:
                await asyncio.sleep(BROADCAST_INTERVAL_S)

                # Snapshot and clear accumulator
                batch = self._accumulator
                self._accumulator = []

                if not batch:
                    # No data to send — pump nothing
                    continue

                # If more than one reading for the same node in this batch,
                # keep only the latest (throttle reduces redundant updates)
                latest_per_node = {}
                for msg in batch:
                    if msg.get("type") == "reading":
                        node_id = msg.get("data", {}).get("node_id")
                        if node_id:
                            latest_per_node[node_id] = msg
                    else:
                        # Alerts and node_status always pass through
                        latest_per_node.setdefault(f"__{msg.get('type')}__{id(msg)}", msg)

                deduped = list(latest_per_node.values())

                # Fan out to all clients
                for msg in deduped:
                    dropped = 0
                    for cid, client in list(self._clients.items()):
                        ok = await client.enqueue(msg)
                        if not ok:
                            dropped += 1
                    if dropped:
                        logger.debug("Broadcast: %d slow client(s) dropped frame", dropped)

        except asyncio.CancelledError:
            logger.info("Broadcast throttle loop stopped.")

    async def start_throttle(self, app_state):
        """Start the background throttle loop (called from lifespan)."""
        self._broadcast_task = asyncio.create_task(
            self._throttled_loop(app_state),
            name="ws-throttle"
        )

    async def stop_throttle(self):
        """Stop the background throttle loop (called from shutdown)."""
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

    @property
    def client_count(self) -> int:
        return len(self._clients)


# Singleton
hub = BroadcastHub()
