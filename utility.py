import bpy

def get_active_area_bounds(active_area_obj):
    """
    Returns (xmin, xmax, ymin, ymax) in world coordinates,
    extracted from the tracker_active_area object’s mesh.
    """

    if active_area_obj is None:
        return None  # safety

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = active_area_obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()

    xs = []
    ys = []

    for v in mesh.vertices:
        world_co = eval_obj.matrix_world @ v.co
        xs.append(world_co.x)
        ys.append(world_co.y)

    eval_obj.to_mesh_clear()

    return min(xs), max(xs), min(ys), max(ys)
