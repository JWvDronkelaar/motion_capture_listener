
import bpy
import bmesh
import mathutils
from datetime import datetime

from .utility import get_active_area_bounds

class TrackerContainer:
    def __init__(self):
        self.trackers_obj = None
        self.active_area_obj = None

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

        # -------------------------------------------------------------
        # 2. Create or reuse tracker_active_area mesh plane
        # -------------------------------------------------------------
        AREA_NAME = "tracker_active_area"
        area_obj = bpy.data.objects.get(AREA_NAME)

        if area_obj is not None:
            print("TrackerContainer: Found existing tracker_active_area. Reusing.")
            self.active_area_obj = area_obj
        else:
            # Create a 2×2 plane centered on origin
            mesh = bpy.data.meshes.new("tracker_active_area_mesh")
            bm = bmesh.new()
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1)  # 2×2 plane
            bm.to_mesh(mesh)
            bm.free()

            area_obj = bpy.data.objects.new(AREA_NAME, mesh)
            bpy.context.scene.collection.objects.link(area_obj)
            self.active_area_obj = area_obj

            print("TrackerContainer: Created new tracker_active_area plane.")

        print("Initialized TrackerContainer: mesh reset + tracker_id attribute ensured + active area ready.")



    def is_within_active_area(self, location):
        bounds = get_active_area_bounds(self.active_area_obj)
        if bounds is None:
            return True  # Fallback: allow all

        xmin, xmax, ymin, ymax = bounds

        return (xmin <= location.x <= xmax) and (ymin <= location.y <= ymax)


    # ---------------------------------------------------------------------
    # MAIN UPDATE LOOP
    # ---------------------------------------------------------------------
    def update(self, tracking_data, grace_seconds=2.0):
        now = datetime.now()

        # Update all incoming trackers
        for tracker_data in tracking_data:
            tracker_id = tracker_data["id"]
            location = mathutils.Vector((tracker_data["x"], tracker_data["y"], tracker_data["z"]))
            
            # TODO: this is incredibly inefficient, optimize later
            if not self.is_within_active_area(location):
                if tracker_id in self.tracker_map:
                    self.delete_tracker(tracker_id)
                continue
            
            self.update_tracker(tracker_id, location)

        # Prune trackers not updated recently
        self.prune_inactive_trackers(grace_seconds)


    # ---------------------------------------------------------------------
    # ADD TRACKER
    # ---------------------------------------------------------------------
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

        print(f"Added tracker ID {tracker_id} at location {location}.")


    # ---------------------------------------------------------------------
    # UPDATE TRACKER
    # ---------------------------------------------------------------------
    def update_tracker(self, tracker_id, location):
        mesh = self.trackers_obj.data
        now = datetime.now()

        entry = self.tracker_map.get(tracker_id)
        if entry is not None:
            mesh.vertices[entry["vertex_id"]].co = location
            entry["updated_at"] = now
        else:
            self.add_tracker(tracker_id, location)

        print(f"Updated tracker ID {tracker_id} to location {location}.")


    # ---------------------------------------------------------------------
    # DELETE TRACKER
    # ---------------------------------------------------------------------
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

        print(f"Deleted tracker ID {tracker_id} from TrackerContainer.")


    # ---------------------------------------------------------------------
    # PRUNE INACTIVE WITH GRACE PERIOD
    # ---------------------------------------------------------------------
    def prune_inactive_trackers(self, grace_seconds):
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

        # Delete vertices
        for v in to_remove:
            bm.verts.remove(v)

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        self._rebuild_tracker_map()

        print(f"Pruned inactive trackers. Remaining active trackers: {len(self.tracker_map)}.")


    # ---------------------------------------------------------------------
    # CLEAR TRACKERS
    # ---------------------------------------------------------------------
    def clear_trackers(self):
        mesh = self.trackers_obj.data
        mesh.clear_geometry()
        self.tracker_map.clear()
        print("Cleared all trackers from TrackerContainer.")


    # ---------------------------------------------------------------------
    # DESTROY
    # ---------------------------------------------------------------------
    def destroy(self):
        bpy.data.objects.remove(self.trackers_obj, do_unlink=True)
        print("Destroyed TrackerContainer and removed from scene.")


    # ---------------------------------------------------------------------
    # REBUILD TRACKER MAP
    # ---------------------------------------------------------------------
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
