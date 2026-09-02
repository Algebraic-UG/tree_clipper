import bpy


class TreeClipperPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    max_clipboard_megabyte: bpy.props.IntProperty(
        name="Max. Clipboard Size (MB)",
        description="""Maximum clipboard size in kilobytes (UTF-8 encoded).

The export fails (safely) if the limit is exceeded.
If this setting is beyond your system's capabilities,
Blender might crash on export.

The default value is somewhat conservative, but not guaranteed to be safe.""",
        default=10,
    )  # type: ignore

    show_advanced_options: bpy.props.BoolProperty(
        name="Show Advanced Options",
        default=False,
    )  # type: ignore

    import_as_asset: bpy.props.BoolProperty(
        name="Import as Asset",
        description="""Instead of having the imported trees in the current .blend file,
store the imports in a local asset library.") # type: ignore""",
        default=True,
    )  # type :ignore

    asset_directory: bpy.props.StringProperty(
        name="Asset Directory",
        description="When importing as asset, store the asset files in this directory.",
        default=bpy.utils.extension_path_user(
            __package__,  # ty:ignore[invalid-argument-type]
            path="assets",
            create=True,
        ),
        subtype="DIR_PATH",
    )  # ty:ignore[invalid-type-form]

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "max_clipboard_megabyte")
        self.layout.prop(self, "show_advanced_options")
        self.layout.prop(self, "import_as_asset")
        self.layout.prop(self, "asset_directory")


def _get_preferences():
    return bpy.context.preferences.addons.get(__package__).preferences  # ty:ignore[unresolved-attribute]


def get_max_clipboard_bytes():
    return 1_000_000 * _get_preferences().max_clipboard_megabyte


def get_show_advanced_options():
    return _get_preferences().show_advanced_options


def get_import_as_asset():
    return _get_preferences().import_as_asset


def get_asset_directory():
    return _get_preferences().asset_directory
