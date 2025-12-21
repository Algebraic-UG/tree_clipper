import bpy

from typing import Type

from .common import no_clobber


# TODO: we might need to return a list that fits the Blender version
KNOWN_POINTABLES = {
    bpy.types.SunLight,
    bpy.types.Texture,
    bpy.types.Object,
    bpy.types.WorkSpace,
    bpy.types.Mesh,
    bpy.types.Text,
    bpy.types.Lattice,
    bpy.types.Material,
    bpy.types.Camera,
    bpy.types.World,
    bpy.types.Volume,
    bpy.types.FreestyleLineStyle,
    bpy.types.MovieClip,
    bpy.types.PointLight,
    bpy.types.LightProbeVolume,
    bpy.types.TextureNodeTree,
    bpy.types.AreaLight,
    bpy.types.VoronoiTexture,
    bpy.types.CompositorNodeTree,
    bpy.types.NoiseTexture,
    bpy.types.Image,
    bpy.types.SpotLight,
    bpy.types.ImageTexture,
    bpy.types.VectorFont,
    bpy.types.ParticleSettings,
    bpy.types.Screen,
    bpy.types.Annotation,
    bpy.types.MagicTexture,
    bpy.types.MetaBall,
    bpy.types.Key,
    bpy.types.MarbleTexture,
    bpy.types.MusgraveTexture,
    bpy.types.StucciTexture,
    bpy.types.WoodTexture,
    bpy.types.DistortedNoiseTexture,
    bpy.types.LightProbeSphere,
    bpy.types.Scene,
    bpy.types.CloudsTexture,
    bpy.types.Brush,
    bpy.types.WindowManager,
    bpy.types.Library,
    bpy.types.Collection,
    bpy.types.Sound,
    bpy.types.NodeTree,
    bpy.types.GreasePencil,
    bpy.types.Curves,
    bpy.types.Armature,
    bpy.types.Light,
    bpy.types.Curve,
    bpy.types.Speaker,
    bpy.types.Action,
    bpy.types.GeometryNodeTree,
    bpy.types.ShaderNodeTree,
    bpy.types.PointCloud,
    bpy.types.LightProbe,
    bpy.types.CacheFile,
    bpy.types.TextCurve,
    bpy.types.BlendTexture,
    bpy.types.Mask,
    bpy.types.PaintCurve,
    bpy.types.LightProbePlane,
    bpy.types.Palette,
    bpy.types.SurfaceCurve,
}


def add_all_known_pointer_properties(
    *,
    cls: Type[bpy.types.PropertyGroup],
    prefix: str,
):
    def get_pointer_property_name(ty: type):
        return f"{prefix}{ty.__name__}"

    # does this even ever happen
    if not hasattr(cls, "__annotations__"):
        cls.__annotations__ = {}

    # we store which kind of thing we're pointing to, used in get_pointer
    no_clobber(
        cls.__annotations__,
        "active_ptr_type_name",
        bpy.props.StringProperty(),
    )

    # now actually register all the properties
    for pointable in KNOWN_POINTABLES:
        no_clobber(
            cls.__annotations__,
            get_pointer_property_name(pointable),
            bpy.props.PointerProperty(type=pointable),
        )

    # this switches the type we're pointing to and clears all
    def set_active_pointer_type(self, type_name: str):
        self.active_ptr_type_name = type_name
        for ty in KNOWN_POINTABLES:
            setattr(self, get_pointer_property_name(ty), None)

    # this is needed to display the property
    def get_active_pointer_identifier(self) -> str:
        return f"{prefix}{self.active_ptr_type_name}"

    # directly return the pointer
    def get_active_pointer(self) -> bpy.types.PointerProperty:
        return getattr(self, self.get_active_pointer_identifier())

    assert not hasattr(cls, set_active_pointer_type.__name__)
    setattr(cls, set_active_pointer_type.__name__, set_active_pointer_type)
    assert not hasattr(cls, get_active_pointer_identifier.__name__)
    setattr(cls, get_active_pointer_identifier.__name__, get_active_pointer_identifier)
    assert not hasattr(cls, get_active_pointer.__name__)
    setattr(cls, get_active_pointer.__name__, get_active_pointer)
