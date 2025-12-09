
import bpy
import bmesh
import mathutils
from datetime import datetime

from .Bounds import Bounds

class TrackerContainer:
    def __init__(self):
        self.trackers_obj = None
        self.bounds = None

        # TODO: change into namedtuple or dataclass
        # tracker_map:
        # tracker_id -> {
        #     "vertex_id": int,
        #     "created_at": datetime,
        #     "updated_at": datetime
        # }
        self.tracker_map = {}

        self.initialize()


    def initialize(self):
        CONTAINER_NAME = "tracker_container"

        existing_obj = bpy.data.objects.get(CONTAINER_NAME)

        if existing_obj is not None:
            print("TrackerContainer: Found existing tracker_container. Reusing.")

            # If it's not a mesh object, replace it
            if existing_obj.type != 'MESH':
                print("TrackerContainer: Existing object is not a mesh. Replacing with new mesh.")
                mesh = bpy.data.meshes.new("tracker_container_mesh")
                existing_obj.data = mesh
            else:
                mesh = existing_obj.data

            mesh.clear_geometry()

            # Remove old tracker_id attribute if present to avoid conflicts
            if "tracker_id" in mesh.attributes:
                mesh.attributes.remove(mesh.attributes["tracker_id"])

            mesh.attributes.new(name="tracker_id", type='INT', domain='POINT')

            self.trackers_obj = existing_obj

        else:
            mesh = bpy.data.meshes.new("tracker_container_mesh")
            mesh.attributes.new(name="tracker_id", type='INT', domain='POINT')

            obj = bpy.data.objects.new(CONTAINER_NAME, mesh)
            bpy.context.scene.collection.objects.link(obj)
            self.trackers_obj = obj

            print("TrackerContainer: Created new tracker_container object.")


        AREA_NAME = "tracker_active_area"
        area_obj = bpy.data.objects.get(AREA_NAME)

        self.bounds = Bounds(area_obj)

    
    def update(self, tracking_data):
        now = datetime.now()

        # Update all incoming trackers
        for tracker_data in tracking_data:
            tracker_id = tracker_data["id"]
            location = mathutils.Vector((tracker_data["x"], tracker_data["y"], tracker_data["z"]))
            
            self.update_tracker(tracker_id, location)

        self.prune_out_of_bounds_trackers()
        self.prune_inactive_trackers()


    def add_tracker(self, tracker_id, location):
        mesh = self.trackers_obj.data

        mesh.vertices.add(1)
        new_index = len(mesh.vertices) - 1
        mesh.vertices[new_index].co = location

        mesh.attributes["tracker_id"].data[new_index].value = tracker_id

        now = datetime.now()

        self.tracker_map[tracker_id] = {
            "vertex_id": new_index,
            "created_at": now,
            "updated_at": now,
        }

        # print(f"Added tracker ID {tracker_id} at location {location}.")


    def update_tracker(self, tracker_id, location):
        mesh = self.trackers_obj.data
        now = datetime.now()

        entry = self.tracker_map.get(tracker_id)
        if entry is not None:
            mesh.vertices[entry["vertex_id"]].co = location
            entry["updated_at"] = now
        else:
            self.add_tracker(tracker_id, location)

        # print(f"Updated tracker ID {tracker_id} to location {location}.")


    # TODO: isn't it slow to do this one by one since after each delete the mapping is rebuilt?
    def delete_tracker(self, tracker_id):
        mesh = self.trackers_obj.data

        entry = self.tracker_map.get(tracker_id)
        if entry is None:
            print(f"Warning delete_tracker() tracker ID not found: {tracker_id}!")
            return

        vertex_id = entry["vertex_id"]

        # Build BMesh
        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.verts.ensure_lookup_table()
        bm.verts.remove(bm.verts[vertex_id])

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        # Rebuild mapping
        self._rebuild_tracker_map()

        # print(f"Deleted tracker ID {tracker_id} from TrackerContainer.")


    def prune_out_of_bounds_trackers(self):
        mesh = self.trackers_obj.data

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()

        to_remove = []

        for vertex in bm.verts:
            if not self.bounds.is_within_active_area(vertex.co):
                to_remove.append(bm.verts[vertex.index])

        delete_count = len(to_remove)

        # Delete vertices
        for v in to_remove:
            bm.verts.remove(v)

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        self._rebuild_tracker_map()

        print(f"Pruned {delete_count} out of bounds trackers. Remaining active trackers: {len(self.tracker_map)}.")


    def prune_inactive_trackers(self, grace_seconds=0.5):
        mesh = self.trackers_obj.data
        now = datetime.now()

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()

        attr = mesh.attributes["tracker_id"].data

        to_remove = []

        for tracker_id, entry in list(self.tracker_map.items()):
            age = (now - entry["updated_at"]).total_seconds()
            if age > grace_seconds:
                # Remove this vertex
                vertex_id = entry["vertex_id"]
                to_remove.append(bm.verts[vertex_id])

        delete_count = len(to_remove)

        # Delete vertices
        for v in to_remove:
            bm.verts.remove(v)

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        self._rebuild_tracker_map()

        print(f"Pruned {delete_count} inactive trackers. Remaining active trackers: {len(self.tracker_map)}.")


    def clear_trackers(self):
        mesh = self.trackers_obj.data
        mesh.clear_geometry()
        self.tracker_map.clear()
        print("Cleared all trackers from TrackerContainer.")


    def destroy(self):
        bpy.data.objects.remove(self.trackers_obj, do_unlink=True)
        print("Destroyed TrackerContainer and removed from scene.")


    def _rebuild_tracker_map(self):
        """
        After BMesh rewrites the vertices, tracker_id values are still stored
        on the attribute array, but vertex indices have changed.

        We rebuild the dictionary by scanning the attribute and reassigning
        the correct vertex index while preserving the old timestamps.
        """
        mesh = self.trackers_obj.data
        attr = mesh.attributes["tracker_id"].data

        old_map = self.tracker_map
        new_map = {}

        for new_vertex_id, item in enumerate(attr):
            tracker_id = item.value

            if tracker_id in old_map:
                existing = old_map[tracker_id]
                new_map[tracker_id] = {
                    "vertex_id": new_vertex_id,
                    "created_at": existing["created_at"],
                    "updated_at": existing["updated_at"],
                }
            else:
                # Should not happen, but we preserve robustness
                now = datetime.now()
                new_map[tracker_id] = {
                    "vertex_id": new_vertex_id,
                    "created_at": now,
                    "updated_at": now,
                }

        self.tracker_map = new_map
