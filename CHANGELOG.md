# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.1.9] - 2026-07-28

Patch release to aid importing trees containing fonts and a few internal code changes.
Some of which might fix bugs that were undiscovered.

### Fixed
- In a new project, [the user might be missing a font to select](https://github.com/Algebraic-UG/tree_clipper/issues/219).

### Changed
- Updated to new version of `ruff` and fixed the new findings.

## [0.1.8] - 2026-07-07

Trying to get the PyPI publish job to work >.<

## [0.1.7] - 2026-06-05

Support for the next LTS version of Blender!

### Added

- [Support for Blender 5.2](https://github.com/Algebraic-UG/tree_clipper/issues/181).
- A bunch of new tests based on the bundled assets from Blender itself.

### Changed

### Fixed

- Get Bundle Item import [must have been broken](https://github.com/Algebraic-UG/tree_clipper/issues/214).

## [0.1.6] - 2026-02-26

This release is a Banger.

Tree Clipper already accepted exports from an earlier version of Tree Clipper, but the Blender version had to match exactly.
That was very limiting, and we're now trying to be backward-compatible.

Also worth highlighting: progress on third-party-defined properties.

### Added

- Support for Blender 5.1.
- Backwards compatibility.

### Changed

### Fixed

- Issues with properties registered by third-party addons.
- Min/Max issue for certain subtypes in interface sockets.
- Crytomatte nodes issues.

## [0.1.5] - 2026-01-23

This version might be the first to be in the extension store.

### Added

Reporting runtime of the import.

### Changed

Tags of the addon are now "Import-Export" and "Node".

### Fixed

## [0.1.4] - 2026-01-21

Increasing the default clipboard size limit.

### Added

### Changed

### Fixed

## [0.1.3] - 2026-01-21

This release is only there to push the new logo.

### Added

### Changed

### Fixed

## [0.1.2] - 2026-01-19

Fix annoying bug, easy sub-tree export, and starting backwards compatibilty.

### Added

Backwards compatibility is now a goal.
Starting with this version, matching major, smaller-or-equal minor, and any path version can be imported.

Note that this doesn't (yet) change the strict Blender version requirement.

### Changed

The tree that is currently visible is the one being exported, not the root tree.
This makes it more intuitive and easier to export sub-trees.

### Fixed

If the editor displayed a sub-tree, the import still happened on the root (parent) tree.

## [0.1.1] - 2026-01-08

Minor fixes and improvements.

### Added

Addon preferences for max clipboard size and advanced options.

### Changed

The export and import have one less pop-up to click through if the advanced options are hidden.
This is the default.
The import still has one if there are external items to be set.

### Fixed

- Clipboard size limit check makes crashes with very large exports less likely.
- Fixed wrong export of the "Subsurface IOR" default value.

## [0.1.0] - 2026-01-06

Initial release of the extension and package.

### Added

### Changed

### Fixed