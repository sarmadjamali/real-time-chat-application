from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[id] = websocket

    def disconnect(self, id: int):
        if id in self.active_connections:
            del self.active_connections[id]

    async def send_personal_message(self, message: str, id: int):
        if id in self.active_connections:
            websocket = self.active_connections[id]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        for websocket in self.active_connections.values():
            await websocket.send_text(message)

manager = ConnectionManager()
