"""Bounded contexts, one package each, as vertical slices.

A module owns its ``router``, ``schemas``, ``models``, ``service``, ``repository``,
``exceptions``, and optionally ``tasks``. It may import another module's ``service``.
It may never import another module's ``repository``, ``models``, or tables — enforced by
the import-linter contracts in ``backend/pyproject.toml``, one per module.

There is no global ``models.py`` or ``services.py``. Layer-first structure is what turns
a codebase into mud at thirty modules.
"""
