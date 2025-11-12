import bpy
import asyncio
from multiprocessing import Process
import json
import websockets

# Configuration
WS_PORT = 8765
UPDATE_FREQUENCY_HZ = 20 # Hz

# Global stop flag
stop_server = False

async def ws_handler(websocket, path):
    print("[WebSocket] Client connected")
    async for message in websocket:
        try:
            data = json.loads(message)
            x = data.get("x", 0)
            y = data.get("y", 0)
            z = data.get("z", 0)
            
            # Must update Blender data in main thread
            def update_position():
                obj = bpy.data.objects.get("TrackerEmpty")
                if obj:
                    obj.location = (x, y, z)
            bpy.app.timers.register(update_position, first_interval=0.0)
        except Exception as e:
            print("[WebSocket] Error:", e)

async def ws_main():
    async with websockets.serve(ws_handler, "localhost", WS_PORT):
        print(f"[WebSocket] Server running on ws://localhost:{WS_PORT}")
        while not stop_server:
            await asyncio.sleep(1/UPDATE_FREQUENCY_HZ)

def run_ws_server():
    asyncio.run(ws_main())

class WS_OT_Start(bpy.types.Operator):
    """Start WebSocket server"""
    bl_idname = "wm.start_ws_server"
    bl_label = "Start WebSocket Server"

    _process = None

    def execute(self, context):
        global stop_server
        stop_server = False
        if not bpy.data.objects.get("TrackerEmpty"):
            bpy.ops.object.add(type='EMPTY')
            bpy.context.object.name = "TrackerEmpty"

        if self._process is None:
            self._process = Process(target=run_ws_server, daemon=True)
            self._process.start()
            self.report({'INFO'}, "WebSocket server started.")
        else:
            self.report({'INFO'}, "Server already running.")
        return {'FINISHED'}

class WS_OT_Stop(bpy.types.Operator):
    """Stop WebSocket server"""
    bl_idname = "wm.stop_ws_server"
    bl_label = "Stop WebSocket Server"

    def execute(self, context):
        global stop_server
        stop_server = True
        self.report({'INFO'}, "Stopping WebSocket server.")
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(WS_OT_Start.bl_idname)
    self.layout.operator(WS_OT_Stop.bl_idname)

def register():
    bpy.utils.register_class(WS_OT_Start)
    bpy.utils.register_class(WS_OT_Stop)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(WS_OT_Start)
    bpy.utils.unregister_class(WS_OT_Stop)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
