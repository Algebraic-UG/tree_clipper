import bpy

from tree_clipper.common import version_at_least
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
from tree_clipper.specific_handlers import BUILT_IN_IMPORTER

from .util import (
    export_to_string,
    make_test_node_tree,
    save_failed,
)


if version_at_least(bpy.app.version, [5, 2, 0]):

    def test_panel_states():
        try:
            tree = make_test_node_tree()

            node = tree.nodes.new(type="GeometryNodeMeshBevel")

            node.panel_states[0].is_collapsed = False
            open = export_to_string(tree.name)

            node.panel_states[0].is_collapsed = True
            closed = export_to_string(tree.name)

            def check_state(export: str, state: bool):
                import_intermediate = ImportIntermediate(string=export)
                import_report = import_intermediate.import_all(
                    parameters=ImportParameters(
                        specific_handlers=BUILT_IN_IMPORTER,
                        debug_prints=True,
                    )
                )

                assert (
                    state
                    == bpy.data.node_groups[import_report.renames_node_group[tree.name]]
                    .nodes[0]
                    .panel_states[0]
                    .is_collapsed
                )

            check_state(open, False)
            check_state(closed, True)

        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_panel_states.__name__}")

            raise
