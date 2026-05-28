from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core import TokenService
from app.models import UserModel
from app.utilities import DebugMixin

class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        
        try:
            await websocket.close()
        except RuntimeError:
            pass

    async def broadcast(self, data: dict):
        dead = []

        for ws in list(self.connections):
            try:
                await ws.send_json(data)
            except:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

class LivePredictController(DebugMixin):

    def __init__(self, manager):
        self.router = APIRouter(
            prefix = "/ws/v1",
            tags   = ["Live Predict"]
        )

        self.manager = manager
        self.router.add_api_websocket_route(
            "/live-predict",
            self.websocket_endpoint
        )

    # ======================
    # AUTH
    # ======================
    async def _authorize(self, websocket: WebSocket) -> bool:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008)
            return False

        try:
            payload = TokenService().decode_token(token)
        except Exception as e:
            await websocket.close(code=1008)
            return False

        user_id   = payload.get("user_id")
        username  = payload.get("username")
        role_name = payload.get("role")

        self.printDebug(f"WebSocket connection attempt with token payload: {payload}")

        if not user_id or not username or not role_name:
            await websocket.close(code=1008)
            return False

        db   = websocket.app.state.db
        user = UserModel.get_auth_by_id(db, user_id)

        if not user:
            await websocket.close(code=1008)
            return False

        is_matched = (
            user["id"]        == user_id and
            user["username"]  == username and
            user["role_name"] == role_name
        )

        if not is_matched:
            await websocket.close(code=1008)
            return False

        return True

    # ======================
    # WS ENDPOINT
    # ======================
    async def websocket_endpoint(self, websocket: WebSocket):

        is_ok = await self._authorize(websocket)
        if not is_ok:
            return

        await self.manager.connect(websocket)

        try:
            while True:
                data = await websocket.receive_json()

                # keep-alive
                if data.get("type") == "noop":
                    self.printDebug("Received keep-alive")
                    continue

        except WebSocketDisconnect:
            await self.manager.disconnect(websocket)
            self.printDebug("Disconnected")

        except Exception as e:
            await self.manager.disconnect(websocket)
            self.printDebug(f"Error: {e}")
