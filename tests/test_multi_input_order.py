import bpy

from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER


def round_trip(name: str):
    export_intermediate = ExportIntermediate(
        parameters=ExportParameters(
            is_material=False,
            name=name,
            specific_handlers=BUILT_IN_EXPORTER,
            export_sub_trees=True,
            skip_defaults=True,
            debug_prints=True,
            write_from_roots=False,
        )
    )
    string = export_intermediate.export_to_str(compress=True, json_indent=0)
    import_intermediate = ImportIntermediate()
    import_intermediate.from_str(string)
    import_intermediate.import_nodes(
        parameters=ImportParameters(
            specific_handlers=BUILT_IN_IMPORTER,
            allow_version_mismatch=False,
            getters={},
            overwrite=True,
            debug_prints=True,
        )
    )


def test_multi_input_order():
    try:
        tree = bpy.data.node_groups.new(name="test", type="GeometryNodeTree")
        assert isinstance(tree, bpy.types.GeometryNodeTree)
        tree.is_modifier = True
        tree.use_fake_user = True

        tree.nodes.new(type="GeometryNodeJoinGeometry")
        tree.nodes.new(type="GeometryNodeMeshCube")
        tree.nodes.new(type="GeometryNodeMeshUVSphere")

        join = tree.nodes["Join Geometry"]
        cube = tree.nodes["Cube"]
        sphere = tree.nodes["UV Sphere"]

        tree.links.new(input=cube.outputs["Mesh"], output=join.inputs["Geometry"])
        tree.links.new(input=sphere.outputs["Mesh"], output=join.inputs["Geometry"])

        assert tree.links[0].multi_input_sort_id == 0
        assert tree.links[0].from_node == tree.nodes["Cube"]

        round_trip(tree.name)

        assert tree.links[0].multi_input_sort_id == 0
        assert tree.links[0].from_node == tree.nodes["Cube"]

        assert tree.links[0].swap_multi_input_sort_id(tree.links[1])

        assert tree.links[0].multi_input_sort_id == 1
        assert tree.links[0].from_node == tree.nodes["Cube"]

        round_trip(tree.name)

        assert tree.links[0].multi_input_sort_id == 1
        assert tree.links[0].from_node == tree.nodes["Cube"]

    except:
        # store in case of failure for easy debugging
        bpy.ops.wm.save_as_mainfile(filepath=f"{test_multi_input_order.__name__}.blend")
        raise
