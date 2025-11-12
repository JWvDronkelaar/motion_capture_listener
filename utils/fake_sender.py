import asyncio
import websockets
import json
import math
import time

# Configuration
PORT = 8765
UPDATE_FREQUENCY_HZ = 20 # Hz
CIRCLE_RADIUS = 2.0

async def send_fake_positions():
    uri = f"ws://localhost:{PORT}"
    async with websockets.connect(uri) as websocket:
        print("[Client] Connected to Blender WS server")
        t0 = time.time()
        while True:
            t = time.time() - t0
            # Make the empty move in a small circle
            data = {
                "x": math.cos(t) * CIRCLE_RADIUS,
                "y": math.sin(t) * CIRCLE_RADIUS,
                "z": 0.5
            }
            await websocket.send(json.dumps(data))
            await asyncio.sleep(1/UPDATE_FREQUENCY_HZ)

asyncio.run(send_fake_positions())
