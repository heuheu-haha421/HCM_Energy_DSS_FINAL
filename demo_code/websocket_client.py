import asyncio
import json
from urllib.parse import urlencode

import requests
import websockets


API_BASE_URL   = "http://localhost:8000"
WS_URL         = "ws://localhost:8000/ws/v1/live-predict"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def get_backend_message(response):
    try:
        data = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

    for key in ("error", "message", "detail"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                return first.get("msg") or str(first)
            return str(first)
        if isinstance(value, dict) and value:
            return value.get("msg") or str(value)

    return f"HTTP {response.status_code}"


def login_admin():
    response = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        },
        timeout=10,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {get_backend_message(response)}")

    data  = response.json().get("data") or {}
    token = data.get("access_token")

    if not token:
        raise RuntimeError("Login response missing access token")

    print(f"Logged in as {ADMIN_USERNAME}.")
    return token


class PredictionClient:
    def __init__(self, ws_url: str, reconnect_delay: int = 5):
        self.base_ws_url     = ws_url
        self.connection      = None
        self.running         = False
        self.reconnect_delay = reconnect_delay
        self.token           = None

    async def run_forever(self):
        """Keep the client alive and reconnect when the connection drops."""
        self.running = True
        while self.running:
            try:
                await self._connect_and_handle()
            except websockets.exceptions.ConnectionClosed as e:
                print(f"\n=> [DISCONNECTED] Server closed the connection (code: {e.code}).")
                if e.code == 1008:
                    self.token = None
            except Exception as e:
                print(f"\n=> [ERROR] {e}")

            if self.running:
                print(f"-> Reconnecting in {self.reconnect_delay} seconds...\n")
                await asyncio.sleep(self.reconnect_delay)

    async def _connect_and_handle(self):
        """Open one websocket session and handle its lifecycle."""
        if not self.token:
            self.token = await asyncio.to_thread(login_admin)

        ws_url = self._build_ws_url()
        print(f"Connecting to {ws_url}...")

        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            self.connection = websocket
            print("Connected. Listening for data and sending keep-alive messages.")

            receive_task   = asyncio.create_task(self._receive_data())
            keepalive_task = asyncio.create_task(self._keep_alive())

            done, pending = await asyncio.wait(
                [receive_task, keepalive_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if receive_task in done and receive_task.exception():
                raise receive_task.exception()
            if keepalive_task in done and keepalive_task.exception():
                raise keepalive_task.exception()

    def _build_ws_url(self):
        return f"{self.base_ws_url}?{urlencode({'token': self.token})}"

    async def _receive_data(self):
        """Listen for data from the server."""
        async for message in self.connection:
            data = json.loads(message)
            self._handle_prediction(data)

    async def _keep_alive(self):
        """Send noop messages to keep the connection active."""
        print("Sending keep-alive messages every 10 seconds...")
        while self.running:
            await asyncio.sleep(10)
            if self.connection:
                payload = json.dumps({"type": "noop"})
                await self.connection.send(payload)

    def _handle_prediction(self, data: dict):
        """Handle prediction data from the server."""
        print(f"[DATA] {data.get('predicted_at')} | Data: {data}")

    def stop(self):
        """Stop the client."""
        print("Stopping client...")
        self.running = False


if __name__ == "__main__":
    client = PredictionClient(WS_URL)

    try:
        asyncio.run(client.run_forever())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Stopped by user (Ctrl+C).")
        client.stop()
