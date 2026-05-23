from fastapi import FastAPI
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.services.connection_manager import manager
from app.services.database import close_database, ping_database
from app.settings import get_settings

settings = get_settings()
ALLOWED_ORIGINS = [settings.allowed_origin, "http://localhost:3001"]

app = FastAPI(title="Fleet Edge API", version="0.1.0")


@app.on_event("startup")
async def startup_event() -> None:
    await ping_database()
    await manager.start_pubsub_listener()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await manager.stop_pubsub_listener()
    await close_database()


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.websocket("/ws/dispatch")
async def dispatch_socket(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin", "")
    if origin and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "system.hello",
                "payload": {
                    "message": "Connected to realtime dispatch stream",
                    "activeConnections": manager.active_count,
                },
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


app.include_router(router, prefix="/api/v1")
