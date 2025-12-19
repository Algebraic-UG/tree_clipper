import bpy
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run print_tree_in_file.py <path-to-file>")
        sys.exit(1)
    file_path = sys.argv[1]

    bpy.ops.wm.open_mainfile(filepath=str(file_path))

    print("modifiers:")
    for node_group in bpy.data.node_groups:
        if isinstance(node_group, bpy.types.GeometryNodeTree):
            if node_group.is_modifier:
                print("  " + node_group.name)

    print("tools:")
    for node_group in bpy.data.node_groups:
        if isinstance(node_group, bpy.types.GeometryNodeTree):
            if node_group.is_tool:
                print("  " + node_group.name)

    print("compositors:")
    for node_group in bpy.data.node_groups:
        if isinstance(node_group, bpy.types.CompositorNodeTree):
            print("  " + node_group.name)

    print("materials:")
    for material in bpy.data.materials:
        if material.node_tree is None:
            continue
        print("  " + material.name)

    print("textures:")
    for node_group in bpy.data.node_groups:
        if isinstance(node_group, bpy.types.TextureNodeTree):
            print("  " + node_group.name)
