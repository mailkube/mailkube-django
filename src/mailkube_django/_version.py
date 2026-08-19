"""The package version, read from the installed distribution metadata.

There is deliberately **no literal** here, and none anywhere else in the tree:
semantic-release creates the git tag, ``hatch-vcs`` resolves it into the distribution
metadata at build time, and this module reads it back, so the runtime version equals the
released version by construction.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mailkube-django")
except PackageNotFoundError:  # pragma: no cover — only when imported from an uninstalled source tree
    __version__ = "0.0.0"
