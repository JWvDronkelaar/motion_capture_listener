import bpy
import mathutils


# Update Blender scene (must happen in main thread)
# TODO: 
def update_blender_scene(tracker_container, messages):
    for item in messages:
        tracker_id = item["id"]
        location = mathutils.Vector((item["x"], item["y"], item["z"]))

        tracker_container.update_tracker(tracker_id, location)
