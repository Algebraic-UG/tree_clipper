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