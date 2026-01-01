# Tree Clipper

Easier version control and sharing of node trees via `.json` or copy-pasteable strings.

Sharing node trees between users and in communities usually involves screenshots of node setups (which a user has to try and exactly re-create manually) or `.blend` files which can be cumbersome (and a security risk) to download and append relevant data blocks to scenes.

`Tree Clipper` aims to improve two main workflows:

- Storage of large collections of nodes in `.json` format, so that version control such as `git` can properly track changes in a node tree rather than a single binary `.blend` file
- Sharing of node groups in communities like Discord and Stack Exchange. Users can share a 'magic string' which will be de-serialized into a node tree by the add-on, enabling rapid sharing and collaborating between users

More to come once we actually finish building.

## Testing

Testing leverages [pytest](https://docs.pytest.org/en/stable/), also see the [CI](.github/workflows/test.yml) setup.

### Binary Blend Files

The directory [packages/tree_clipper/tests/binary_blend_files/](packages/tree_clipper/tests/binary_blend_files/) contains binary blend files with relatively big node groups from various sources.
In certain cases, the files are generated from an add-on.

Note that these files are within Git LFS and optional unless you want to test Tree Clipper.

#### Sources & Attribution

| Source                    | Description                            | License                 | Link                                                             |
| ------------------------- | -------------------------------------- | ----------------------- | ---------------------------------------------------------------- |
| **Erindale’s Nodevember** | Procedural awesomeness                 | **CC0** (public domain) | [Patreon Collection](https://www.patreon.com/collection/1812208) |
| **Molecular Nodes**       | Molecular animation toolbox            | **GPLv3**               | [GitHub](https://github.com/BradyAJohnston/MolecularNodes)       |
| **Microscopy Nodes**      | Microscopy data handling               | **GPLv3**               | [GitHub](https://github.com/aafkegros/MicroscopyNodes)           |
| **Typst Importer**        | Render Typst content in Blender        | **GPLv3**               | [GitHub](https://github.com/kolibril13/blender_typst_importer)   |
| **Squishy Volumes**       | Material Point Method (MPM) in Blender | **GPLv3**               | [GitHub](https://github.com/Algebraic-UG/squishy_volumes)        |

#### Licensing/permission

Included assets are used with permission from the respective authors for testing purposes in this repository.
If you reuse or redistribute them, please follow each project’s license/terms and attribution requirements.

## Development

It is recommended to use [vscode](https://code.visualstudio.com/) with these extensions:
- [ruff](https://github.com/astral-sh/ruff-vscode)
- [ty](https://github.com/astral-sh/ty-vscode)
- [Python Debugger](https://code.visualstudio.com/docs/python/debugging)
- [Blender Development](https://github.com/JacquesLucke/blender_vscode)

[uv](https://docs.astral.sh/uv/) is also required for this workflow.

### Vendorizing Tree Clipper

Ideally, the [core logic](packages/tree_clipper/) of Tree Clipper is not used as dependency in downstream addons directly and it should be [vendorized](https://pypi.org/project/vendorize/) instead.
This is what the [Tree Clipper Addon](packages/tree_clipper_addon/) does as well.

The motivation for this is that we expect other addons like [Squishy Volumes](https://github.com/Algebraic-UG/squishy_volumes) to use an incompatible version of Tree Clipper.
Vendoring avoids version conflicts and ensures that all addons can load.
> [!IMPORTANT]
> Vendoring currently has two drawbacks developers must be aware of:
> 1. There is the editable code of the core logic in [packages/tree_clipper/](packages/tree_clipper/) and there's the vendorized code which will reside in packages/tree_clipper_addon/src/tree_clipper_addon/_vendor/. The vendorized code runs and can be debugged, but should not be edited directly.
> 2. Depending on your version of the [Blender Development](https://github.com/JacquesLucke/blender_vscode) addon (whether it has [this change](https://github.com/JacquesLucke/blender_vscode/pull/258)), the task [`run-python-vendor`](.vscode/tasks.json) must run before starting Blender. Subsequent reloads will do this automatically.