bl_info = {
    "name": "UDP Tracker Bridge",
    "blender": (4, 0, 0),
    "category": "Object",
}

import bpy
import asyncio
import socket
import json

HOST = "127.0.0.1"
PORT = 9999

# Keep a reference to avoid garbage collection
_udp_task = None
_stop_flag = False


async def udp_listener():
    """Async UDP listener that updates Blender empties."""
    global _stop_flag
    loop = asyncio.get_running_loop()

    # Non-blocking UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.setblocking(False)

    print(f"[UDP Tracker] Listening on {HOST}:{PORT}")

    while not _stop_flag:
        try:
            data = await loop.sock_recv(sock, 4096)
            objs = json.loads(data.decode("utf-8"))

            # Update Blender scene (must happen in main thread)
            def update_objects():
                for item in objs:
                    name = item["id"]
                    x, y, z = item["x"], item["y"], item["z"]
                    obj = bpy.data.objects.get(name)
                    if not obj:
                        obj = bpy.data.objects.new(name, None)
                        bpy.context.scene.collection.objects.link(obj)
                    obj.location = (x, y, z)

            bpy.app.timers.register(update_objects, first_interval=0.0)

        except Exception as e:
            print("UDP error:", e)
            await asyncio.sleep(0.5)

    print("[UDP Tracker] Listener stopped.")
    sock.close()


def start_udp_loop():
    global _udp_task, _stop_flag
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
        layout.operator("udp_tracker.start")
        layout.operator("udp_tracker.stop")


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
