import bpy

from .util import (
    make_test_node_tree,
    save_failed,
    round_trip,
)


def test_render_layers_edgecase():
    try:
        tree = make_test_node_tree(name="test", ty="CompositorNodeTree")

        bpy.context.scene.render.engine = "BLENDER_EEVEE"
        view_layer = bpy.context.scene.view_layers["ViewLayer"]

        AOVS_COUNT = 42
        for _ in range(AOVS_COUNT):
            view_layer.aovs.add()

        tree.nodes.new(type="CompositorNodeRLayers")
        tree.nodes.new(type="NodeGroupOutput")

        layers = tree.nodes["Render Layers"]
        output = tree.nodes["Group Output"]

        assert isinstance(layers, bpy.types.CompositorNodeRLayers)
        layers.scene = bpy.context.scene
        layers.layer = "ViewLayer"  # ty: ignore[invalid-assignment]

        tree.links.new(
            input=layers.outputs[
                AOVS_COUNT - 1 + 2  # Image and Alpha
            ],
            output=output.inputs[0],
        )

        for _ in range(AOVS_COUNT):
            view_layer.aovs.remove(view_layer.aovs[-1])

        layers.update()

        round_trip(original_name=tree.name, is_material=False)
    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_render_layers_edgecase.__name__}")

        raise
