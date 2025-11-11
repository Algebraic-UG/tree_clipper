COPY_MEMBERS = [
    # ID
    "is_runtime_data",
    "name",
    "tag",
    "use_extra_user",
    "use_fake_user",
    #
    # NodeTree
    # "annotation",
    "bl_description",
    "bl_icon",
    "bl_idname",
    "bl_label",
    "bl_use_group_interface",
    "color_tag",
    "default_group_node_width",
    "description",
    #
    # CompositorNodeTree
    "use_view_border",
    #
    # GeometryNodeTree
    "is_mode_edit",
    "is_mode_object",
    "is_mode_paint",
    "is_mode_sculpt",
    "is_modifier",
    "is_tool",
    "is_type_curve",
    "is_type_grease_pencil",
    "is_type_mesh",
    "is_type_pointcloud",
    "show_modifier_manage_panel",
    "use_wait_for_click",
]

# TODO: the following should be automated

# import bpy
# n = bpy.data.node_groups["Geometry Nodes"]
# for m in dir(n):
#     a = getattr(n, m)
#     try:
#         setattr(n, m, a)
#     except Exception:
#         continue
#     print(f"{m}: {type(a)}")


# Yields:

# annotation: <class 'NoneType'>
# bl_description: <class 'str'>
# bl_icon: <class 'str'>
# bl_idname: <class 'str'>
# bl_label: <class 'str'>
# bl_use_group_interface: <class 'bool'>
# color_tag: <class 'str'>
# default_group_node_width: <class 'int'>
# description: <class 'str'>
# is_mode_edit: <class 'bool'>
# is_mode_object: <class 'bool'>
# is_mode_paint: <class 'bool'>
# is_mode_sculpt: <class 'bool'>
# is_modifier: <class 'bool'>
# is_runtime_data: <class 'bool'>
# is_tool: <class 'bool'>
# is_type_curve: <class 'bool'>
# is_type_grease_pencil: <class 'bool'>
# is_type_mesh: <class 'bool'>
# is_type_pointcloud: <class 'bool'>
# name: <class 'str'>
# show_modifier_manage_panel: <class 'bool'>
# tag: <class 'bool'>
# use_extra_user: <class 'bool'>
# use_fake_user: <class 'bool'>
# use_wait_for_click: <class 'bool'>
