import bpy
import bmesh
import mathutils

class TrackerContainer:
    def __init__(self):
        self.trackers_obj = None
        self.tracker_map = {}

        self.initialize()


    def initialize(self):
        # Create mesh and object
        mesh = bpy.data.meshes.new("tracker_container_mesh")

        # Create point-domain integer attribute "tracker_id"
        attr_name = "tracker_id"
        mesh.attributes.new(name=attr_name, type='INT', domain='POINT')

        self.trackers_obj = bpy.data.objects.new("tracker_container", mesh)

        # Link to scene
        bpy.context.scene.collection.objects.link(self.trackers_obj)

        print("Initialized TrackerContainer with empty mesh and tracker_id attribute.")


    def update(self, tracking_data):
        for tracker_data in tracking_data:
            tracker_id = tracker_data["id"]
            location = mathutils.Vector((tracker_data["x"], tracker_data["y"], tracker_data["z"]))

            self.update_tracker(tracker_id, location)


    def add_tracker(self, tracker_id, location):
        mesh = self.trackers_obj.data

        mesh.vertices.add(1)
        new_index = len(mesh.vertices) - 1
        mesh.vertices[new_index].co = location

        mesh.attributes["tracker_id"].data[new_index].value = tracker_id

        self.tracker_map[tracker_id] = new_index
        # Think about storing more data in the mapping dict if needed (like last update time, etc.)

        print(f"Added tracker ID {tracker_id} at location {location}.")

    
    def update_tracker(self, tracker_id, location):
        mesh = self.trackers_obj.data

        idx = self.tracker_map.get(tracker_id)
        if idx is not None:
            mesh.vertices[idx].co = location
        else:
            self.add_tracker(tracker_id, location)

        print(f"Updated tracker ID {tracker_id} to location {location}.")


    def delete_tracker(self, tracker_id):
        mesh = self.trackers_obj.data

        idx = self.tracker_map.get(tracker_id)
        if idx is None:
            print(f"Warning delete_tracker() tracker ID not found: {tracker_id}!")
            return

        # Build BMesh
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Remove vertex
        v = bm.verts[idx]
        bm.verts.remove(v)

        # Apply changes
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        # Rebuild mapping: vertex indices changed!
        self._rebuild_tracker_map()

        print(f"Deleted tracker ID {tracker_id} from TrackerContainer.")


    def clear_trackers(self):
        mesh = self.trackers_obj.data
        mesh.clear_geometry()
        self.tracker_map.clear()
        print("Cleared all trackers from TrackerContainer.")


    def destroy(self):
        bpy.data.objects.remove(self.trackers_obj, do_unlink=True)
        print("Destroyed TrackerContainer and removed from scene.")


    def _rebuild_tracker_map(self):
        mesh = self.trackers_obj.data
        attr = mesh.attributes["tracker_id"].data

        new_map = {}
        for i, item in enumerate(attr):
            tracker_id = item.value
            new_map[tracker_id] = i

        self.tracker_map = new_map
