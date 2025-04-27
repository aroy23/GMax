from fastapi import WebSocket
from typing import List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("email_bot")

# Store active WebSocket connections
active_connections: List[WebSocket] = []

async def broadcast_status(message: str, status_type: str = "info"):
    """Broadcast a status message to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json({
                "type": status_type,
                "message": message
            })
        except Exception as e:
            logger.error(f"Error broadcasting to WebSocket: {e}")

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket) 