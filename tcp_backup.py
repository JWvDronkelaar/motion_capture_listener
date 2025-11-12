import bpy
import multiprocessing
import socket
import json
import time

HOST = "127.0.0.1"
PORT = 8765
RECONNECT_DELAY = 2.0

_process = None
_queue = multiprocessing.Queue()
_stop_flag = multiprocessing.Event()

def create_or_update_object(obj_name, x, y, z):
    """Create or move an Empty safely from Blender's main thread."""
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        bpy.ops.object.add(type='EMPTY')
        bpy.context.object.name = obj_name
        obj = bpy.context.object
    obj.location = (x, y, z)

def process_queue():
    """Poll queue for new position updates."""
    global _queue
    try:
        while not _queue.empty():
            msg = _queue.get_nowait()
            if msg == "STOP":
                return None  # Stop polling
            obj_name = msg.get("id", "TrackerEmpty")
            if isinstance(obj_name, int):
                obj_name = f"Tracker_{obj_name}"
            x = msg.get("x", 0.0)
            y = msg.get("y", 0.0)
            z = msg.get("z", 0.0)
            create_or_update_object(obj_name, x, y, z)
    except Exception as e:
        print("[TCP Client] Error processing queue:", e)
    # Keep polling every 0.1 seconds
    return 0.1

def tcp_process(queue, stop_event):
    """Runs in a separate process: connects to server and reads JSON lines."""
    while not stop_event.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((HOST, PORT))
            file = sock.makefile("r", encoding="utf-8")
            print("[TCP Client] Connected to", (HOST, PORT))
            while not stop_event.is_set():
                line = file.readline()
                if not line:
                    raise ConnectionResetError()
                try:
                    data = json.loads(line.strip())
                    queue.put(data)
                except json.JSONDecodeError:
                    print("[TCP Client] Bad JSON:", line)
            file.close()
            sock.close()
        except Exception as e:
            print("[TCP Client] Connection error:", e)
            time.sleep(RECONNECT_DELAY)
    print("[TCP Client] Process exiting")

class TCP_OT_Start(bpy.types.Operator):
    bl_idname = "wm.start_tcp_client_mp"
    bl_label = "Start TCP Client (Multiprocessing)"

    def execute(self, context):
        global _process, _queue, _stop_flag
        if _process and _process.is_alive():
            self.report({'INFO'}, "TCP client already running")
            return {'CANCELLED'}

        _stop_flag.clear()
        _queue = multiprocessing.Queue()
        _process = multiprocessing.Process(target=tcp_process, args=(_queue, _stop_flag), daemon=True)
        _process.start()
        bpy.app.timers.register(process_queue, first_interval=0.1)
        self.report({'INFO'}, "TCP client process started")
        return {'FINISHED'}

class TCP_OT_Stop(bpy.types.Operator):
    bl_idname = "wm.stop_tcp_client_mp"
    bl_label = "Stop TCP Client (Multiprocessing)"

    def execute(self, context):
        global _process, _queue, _stop_flag
        if _process and _process.is_alive():
            _stop_flag.set()
            _queue.put("STOP")
            _process.join(timeout=2.0)
            _process = None
            self.report({'INFO'}, "TCP client stopped")
        else:
            self.report({'INFO'}, "No client running")
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(TCP_OT_Start.bl_idname)
    self.layout.operator(TCP_OT_Stop.bl_idname)

def register():
    bpy.utils.register_class(TCP_OT_Start)
    bpy.utils.register_class(TCP_OT_Stop)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(TCP_OT_Start)
    bpy.utils.unregister_class(TCP_OT_Stop)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
