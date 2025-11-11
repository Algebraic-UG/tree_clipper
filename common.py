COPY_MEMBERS_NODE_TREE = [
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

COPY_MEMBERS_NODE_LINK = [
    "is_muted",
    "is_valid",
]

COPY_MEMBERS_NODE = [
    "bl_description",
    "bl_height_default",
    "bl_height_max",
    "bl_height_min",
    "bl_icon",
    "bl_idname",
    "bl_label",
    "bl_width_default",
    "bl_width_max",
    "bl_width_min",
    "height",
    "hide",
    "label",
    "mute",
    "name",
    "select",
    "show_options",
    "show_preview",
    "show_texture",
    "use_custom_color",
    "warning_propagation",
    "width",
]

COPY_MEMBERS_NODE_SOCKET = [
    "bl_idname",
    "bl_label",
    "bl_subtype_label",
    "description",
    "enabled",
    "hide",
    "hide_value",
    "link_limit",
    "name",
    "pin_gizmo",
    "show_expanded",
    "type",
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
