# fake_server.py
# Simple asyncio TCP server that sends fake positions as JSON lines to one client.
# Run: python fake_server.py

import asyncio
import json
import math
import time

HOST = "127.0.0.1"
PORT = 8765

async def handle_client(reader, writer):
    print("Client connected:", writer.get_extra_info("peername"))
    t0 = time.time()
    try:
        while True:
            t = (time.time() - t0) * 3
            msgs = [
                {"id": 1, "x": math.cos(t) * 2.0, "y": math.sin(t) * 1.0, "z": 0.0},
            ]
            # send each as newline-terminated JSON
            for msg in msgs:
                print(msg)
                line = json.dumps(msg) + "\n"
                writer.write(line.encode("utf-8"))
            await writer.drain()
            await asyncio.sleep(0.1)  # ~20 Hz
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        print("Client disconnected")
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = server.sockets[0].getsockname()
    print(f"Fake server running on {addr}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
