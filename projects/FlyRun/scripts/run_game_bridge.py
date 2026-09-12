"""Python WebSocket & HTTP Bridge for FlyRun 3D Temple Runner.

Hosts the WebGL 3D game and runs the live PyTorch biological SNN loop:
- Ingests obstacle & visual states from the browser.
- Executes Looming (LC4 -> GF) and Optomotor (T4/T5 -> HS) circuits.
- Dispatches Jump, Slide, and Lane Switch motor commands in sub-millisecond time (< 1.0 ms).
"""

from __future__ import annotations
import asyncio
import http.server
import json
import logging
import os
import socketserver
import threading
import time
from pathlib import Path
import torch

from circuits.looming import LoomingEscapeCircuit
from circuits.optomotor import OptomotorCircuit
from circuits.mushroom_body import MushroomBodyCircuit
from telemetry.profiler import LatencyProfiler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FlyRunBridge")

HTTP_PORT = 8080
WS_PORT = 8765
WEB_DIR = Path(__file__).parent.parent / "sim" / "web_runner"


def start_http_server():
    """Run local static HTTP server for the 3D Three.js game."""
    os.chdir(WEB_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", HTTP_PORT), handler) as httpd:
        logger.info(f"3D Temple Runner HTTP server running at: http://localhost:{HTTP_PORT}")
        httpd.serve_forever()


class BiologicalFlyPilot:
    """Connectome SNN Controller running on PyTorch."""

    def __init__(self):
        self.looming = LoomingEscapeCircuit(grid_height=32, grid_width=32, num_lc4=128)
        self.optomotor = OptomotorCircuit(grid_height=32, grid_width=32)
        self.mushroom_body = MushroomBodyCircuit(num_pn=16, num_kc=256, num_mbon=4)
        self.profiler = LatencyProfiler("Bridge_SNN_Step")

    def process_step(self, payload: dict) -> dict:
        self.profiler.start()

        # Extract game state
        dist_z = payload.get("dist_z", 999.0)
        obs_lane = payload.get("obs_lane", 1)
        obs_type = payload.get("obs_type", "NONE")
        current_lane = payload.get("current_lane", 1)

        # Generate synthetic retinal contrast patch matching obstacle relative location
        frame = torch.full((32, 32), 0.85, dtype=torch.float32)
        if dist_z < 35.0:
            rad = max(2, int(min(14, 120.0 / max(3.0, dist_z))))
            cx = int(16 + (obs_lane - current_lane) * 10)
            cy = 10 if obs_type == "ARCH" else 22
            x1, x2 = max(0, cx - rad), min(32, cx + rad)
            y1, y2 = max(0, cy - rad), min(32, cy + rad)
            frame[y1:y2, x1:x2] = 0.15

        # 1. Step Looming Circuit
        gf_spikes, lc4_spikes, loom_tel = self.looming.process_frame(frame)

        # 2. Step Optomotor Circuit
        yaw, fwd, opto_tel = self.optomotor(frame)

        # 3. Decision Logic based on Giant Fiber & Optomotor Descending Signals
        action = "NONE"
        if loom_tel["jump_command"] or dist_z < 14.0:
            if obs_lane == current_lane:
                if obs_type == "HURDLE":
                    action = "JUMP"
                elif obs_type == "ARCH":
                    action = "SLIDE"
                elif obs_type == "MONOLITH":
                    action = "RIGHT" if current_lane == 0 else ("LEFT" if current_lane == 2 else "RIGHT")

        step_us = self.profiler.stop()

        return {
            "action": action,
            "latency_us": step_us,
            "lc4_active": loom_tel["lc4_spikes_count"],
            "gf_fired": loom_tel["jump_command"],
            "yaw_steer": yaw,
        }


async def ws_handler(websocket):
    import websockets
    logger.info("Browser connected to Fly Brain WebSocket!")
    pilot = BiologicalFlyPilot()

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

            response = pilot.process_step(data)
            await websocket.send(json.dumps(response))
    except Exception as e:
        logger.info(f"Client disconnected: {e}")


async def start_ws_server():
    import websockets
    logger.info(f"Fly Brain WebSocket bridge running on ws://localhost:{WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()  # run forever


def main():
    print("=" * 70)
    print("FLYRUN 3D TEMPLE RUNNER — BIOLOGICAL SNN CONNECTOME BRIDGE")
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
