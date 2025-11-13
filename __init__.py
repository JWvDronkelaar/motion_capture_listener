import bpy

import asyncio
from enum import Enum, auto
import json
import socket

from . update_blender_scene import update_blender_scene

# Configuration
HOST = "127.0.0.1"
PORT = 9999
TIMEOUT = 3.0               # seconds to wait for first packet before aborting start
INACTIVITY_TIMEOUT = 3.0    # seconds of receiving no data before auto-stop

class ListenerState(Enum):
    STOPPED = auto()
    CONNECTING = auto()
    RUNNING = auto()

# State
_udp_task = None
_stop_flag = False
_listener_state = ListenerState.STOPPED


def refresh_udp_panel():
    """Force refresh of the 3D View UI panel."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return None


async def udp_listener():
    """Async UDP listener that updates Blender empties."""
    global _stop_flag, _listener_state
    _listener_state = ListenerState.CONNECTING
    bpy.app.timers.register(refresh_udp_panel, first_interval=0.0)
    
    loop = asyncio.get_running_loop()

    # Non-blocking UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.setblocking(False)

    print(f"[UDP Tracker] Listening on {HOST}:{PORT}")

    first_packet_received = False
    last_packet_time = loop.time()

    try:
        while not _stop_flag:
            try:
                # Wait 1 second for a packet, so we can periodically check stop_flag
                data = await asyncio.wait_for(loop.sock_recv(sock, 4096), timeout=1.0)
                messages = json.loads(data.decode("utf-8"))

                if not first_packet_received:
                    first_packet_received = True
                    _listener_state = ListenerState.RUNNING
                    bpy.app.timers.register(refresh_udp_panel, first_interval=0.0)
                    print("[UDP Tracker] First packet received. Server is up and running.")

                last_packet_time = loop.time()

                # Schedule Blender update in main thread (safe)
                bpy.app.timers.register(
                    lambda msgs=messages: update_blender_scene(msgs),
                    first_interval=0.0
                )

            except asyncio.TimeoutError:
                now = loop.time()
                # Timeout when starting listener and waiting for first packet data
                if not first_packet_received and (now - last_packet_time) > TIMEOUT:
                    print(f"[UDP Tracker] ❌ It took over {TIMEOUT} seconds to receive data — was the server started?")
                    _stop_flag = True
                
                # Timeout for inactivity
                elif first_packet_received and now - last_packet_time > INACTIVITY_TIMEOUT:
                    print(F"[UDP Tracker] ❌ No data received for {INACTIVITY_TIMEOUT} seconds — has the server stopped?")
                    _stop_flag = True
                continue

            except Exception as e:
                print("UDP error:", e)
                await asyncio.sleep(0.5)

    finally:
        sock.close()
        _listener_state = ListenerState.STOPPED
        bpy.app.timers.register(refresh_udp_panel, first_interval=0.0)  # refresh again on stop
        print("[UDP Tracker] Listener stopped.")
        

def start_udp_loop():
    global _udp_task, _stop_flag, _listener_state

    if _listener_state in (ListenerState.CONNECTING, ListenerState.RUNNING):
        print("[UDP Tracker] Listener is already running.")
        return

    _stop_flag = False

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def run_loop():
        try:
            loop.run_until_complete(udp_listener())
        except Exception as e:
            print("Loop exception:", e)
        finally:
            loop.close()

    import threading
    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
    _udp_task = t


def stop_udp_loop():
    global _stop_flag
    if not _listener_state:
        print("[UDP Tracker] Not currently running.")
        return
    _stop_flag = True


class UDP_OT_Start(bpy.types.Operator):
    bl_idname = "udp_tracker.start"
    bl_label = "Start UDP Tracker"

    def execute(self, context):
        start_udp_loop()
        return {'FINISHED'}


class UDP_OT_Stop(bpy.types.Operator):
    bl_idname = "udp_tracker.stop"
    bl_label = "Stop UDP Tracker"

    def execute(self, context):
        stop_udp_loop()
        return {'FINISHED'}


class UDP_PT_Panel(bpy.types.Panel):
    bl_label = "UDP Tracker Bridge"
    bl_idname = "UDP_PT_TrackerPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tracker"

    def draw(self, context):
        layout = self.layout
        global _listener_state

        col = layout.column(align=True)

        if _listener_state == ListenerState.RUNNING:
            col.label(text="Status: Running", icon="CHECKMARK")
            col.operator("udp_tracker.stop", text="Stop Listener", icon="PAUSE")

        elif _listener_state == ListenerState.CONNECTING:
            col.label(text="Status: Connecting...", icon="TIME")
            col.operator("udp_tracker.stop", text="Cancel Connection", icon="CANCEL")

        else:
            col.label(text="Status: Stopped", icon="X")
            col.operator("udp_tracker.start", text="Start Listener", icon="PLAY")


def register():
    bpy.utils.register_class(UDP_OT_Start)
    bpy.utils.register_class(UDP_OT_Stop)
    bpy.utils.register_class(UDP_PT_Panel)


def unregister():
    bpy.utils.unregister_class(UDP_OT_Start)
    bpy.utils.unregister_class(UDP_OT_Stop)
    bpy.utils.unregister_class(UDP_PT_Panel)


if __name__ == "__main__":
    register()
