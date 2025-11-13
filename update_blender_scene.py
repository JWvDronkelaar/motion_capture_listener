import bpy

# Update Blender scene (must happen in main thread)
def update_blender_scene(messages):
    for item in messages:
        name = item["id"]
        x, y, z = item["x"], item["y"], item["z"]
        obj = bpy.data.objects.get(name)
        
        if not obj:
            obj = bpy.data.objects.new(name, None)
            bpy.context.scene.collection.objects.link(obj)
        
        obj.location = (x, y, z)
