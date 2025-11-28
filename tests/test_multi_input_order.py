import bpy

from .util import round_trip


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
