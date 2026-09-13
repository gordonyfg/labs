"""Serve the browser controller and record incident telemetry.

The browser runs a local heuristic policy; this server does not run the Python SNN.
"""

from __future__ import annotations
import asyncio
import http.server
import json
import logging
import socketserver
import threading
from functools import partial
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FlyRunBridge")

HTTP_PORT = 8080
WS_PORT = 8765
WEB_DIR = Path(__file__).parent.parent / "sim" / "web_runner"


def start_http_server():
    """Run local static HTTP server for the 3D Three.js game."""
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB_DIR))
    with socketserver.TCPServer(("127.0.0.1", HTTP_PORT), handler) as httpd:
        logger.info(f"3D Temple Runner HTTP server running at: http://localhost:{HTTP_PORT}")
        httpd.serve_forever()


async def ws_handler(websocket):
    import websockets
    logger.info("Browser connected to incident logger WebSocket!")

    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "CRASH_EVENT":
                payload = data.get("payload", {})
                ep = payload.get("episode")
                obs = payload.get("obstacleType")
                cause = payload.get("cause")
                dist = payload.get("distance")
                logger.warning(f"CRASH TELEMETRY: Ep {ep} on {obs} ({cause}) at {dist}m | Y={payload.get('characterY')}m")
                log_file = Path(__file__).parent.parent / "data" / "failure_events.jsonl"
                log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(log_file, "a") as f:
                    f.write(json.dumps(payload) + "\n")
                continue

            if data.get("type") == "INCIDENT_EVENT":
                payload = data.get("payload", {})
                ep = payload.get("episode")
                inc_type = payload.get("incidentType", "DAMAGE")
                obs = payload.get("obstacleType")
                dist = payload.get("distance")
                dmg = payload.get("damage")
                hp = payload.get("remainingHealth")
                bb_len = len(payload.get("blackBox", []))
                logger.warning(f"BLACK BOX INCIDENT [{inc_type}]: Ep {ep} on {obs} (-{dmg} HP -> {hp}% HP) at {dist}m | Trajectory samples: {bb_len}")
                incident_file = Path(__file__).parent.parent / "data" / "flight_incidents.jsonl"
                incident_file.parent.mkdir(parents=True, exist_ok=True)
                with open(incident_file, "a") as f:
                    f.write(json.dumps(payload) + "\n")
                continue

            await websocket.send(json.dumps({"error": "Only CRASH_EVENT and INCIDENT_EVENT are supported"}))
    except Exception as e:
        logger.info(f"Client disconnected: {e}")


async def start_ws_server():
    import websockets
    logger.info(f"incident logger WebSocket bridge running on ws://localhost:{WS_PORT}")
    async with websockets.serve(ws_handler, "127.0.0.1", WS_PORT):
        await asyncio.Future()  # run forever


def main():
    print("=" * 70)
    print("FLYRUN 3D TEMPLE RUNNER — BROWSER CONTROLLER & INCIDENT LOGGER")
    print("=" * 70)
    print(f"Open game in browser:  http://localhost:{HTTP_PORT}")
    print(f"WebSocket interface:   ws://localhost:{WS_PORT}")
    print("=" * 70)

    # Start HTTP server in background daemon thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Run WebSocket server in main async loop
    asyncio.run(start_ws_server())


if __name__ == "__main__":
    main()
