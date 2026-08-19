"""Django email backend for mailkube.

Two backends ship in one distribution, and you pick one with ``EMAIL_BACKEND``:

- ``mailkube_django.backends.EmailBackend`` needs only Django and the SDK.
- ``mailkube_django.anymail_backend.EmailBackend`` needs the ``[anymail]`` extra and adds
  Anymail's tags, scheduling, templates, signals and per-recipient status.

Neither is imported here. Importing the backends eagerly would pull ``anymail`` into the
zero-extra-dependency install path, which is exactly what that path promises not to do:
Django imports a backend from its dotted path, so nothing needs re-exporting.
"""

from __future__ import annotations

from ._version import __version__

__all__ = ["__version__"]
