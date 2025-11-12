# external_server.py
import socket
import time
import json
import math

HOST = "127.0.0.1"
PORT = 9999
FPS = 24
INTERVAL = 1.0 / FPS

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def fake_positions(t):
    """Simulate 10 moving objects on a circular path."""
    objs = []
    speed_factor = 5
    for i in range(10):
        angle = (t * speed_factor + i * 36) * math.pi / 180
        x = math.cos(angle) * 5
        y = math.sin(angle) * 5
        z = 0.0
        objs.append({"id": f"obj_{i}", "x": x, "y": y, "z": z})
    return objs

print(f"Sending fake data to UDP {HOST}:{PORT}")
t = 0.0
while True:
    payload = fake_positions(t)
    sock.sendto(json.dumps(payload).encode("utf-8"), (HOST, PORT))
    t += 1
    time.sleep(INTERVAL)
