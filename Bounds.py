from dataclasses import dataclass

import bpy
import bmesh

@dataclass
class RectangularBounds:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class Bounds:
    def __init__(self, active_area_obj=None):
        self.active_area_obj = active_area_obj
        self.bounds = None
        self.initialize()


    def initialize(self):
        AREA_NAME = "tracker_active_area"

        if self.active_area_obj:
            print("Bounds: Using supplied tracker_active_area.")
        elif area_obj := bpy.data.objects.get(AREA_NAME):
            self.active_area_obj = area_obj
            print("TrackerContainer: Found existing tracker_active_area. Reusing.")
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

        self.set_bounds()


    def set_bounds(self):
        """
        Returns bounds in world coordinates,
        extracted from the tracker_active_area object’s mesh.
        Assumes its a grid aligned to world axis for now.
        """

        if self.active_area_obj is None:
            return None  # safety

        # TODO: since this is a rectangle for now should we use bounding box and
        # assume its aligned to the world axis?
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = self.active_area_obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()

        xs = []
        ys = []

        for v in mesh.vertices:
            world_co = eval_obj.matrix_world @ v.co
            xs.append(world_co.x)
            ys.append(world_co.y)

        eval_obj.to_mesh_clear()

        self.bounds = RectangularBounds(min(xs), min(ys), max(ys), max(xs))
        print(f"Bounds are set: {self.bounds}")


    def is_within_active_area(self, location):
        if self.bounds is None:
            print("Bounds: bounds property is not set, this should never happen!")
            return True  # Fallback: allow all

        return (self.bounds.x_min <= location.x <= self.bounds.x_max) and (self.bounds.y_min <= location.y <= self.bounds.y_max)
    