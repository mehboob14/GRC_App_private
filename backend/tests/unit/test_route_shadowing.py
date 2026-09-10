"""Route order: a static path declared after a parameterised one is dead.

Routing matches in declaration order, so ``GET /vendors/findings`` declared
after ``GET /vendors/{vendor_id}`` never runs — the path parameter captures the
literal segment and the UUID coercion answers 422 instead. Every router says in
its docstring that static paths come first; this proves it for all of them at
once rather than one module at a time.

Paths here are router-relative: the ``/api/v1`` mount prefix is applied to every
route equally, so it changes nothing about which route shadows which.
"""

from __future__ import annotations

import re

import pytest

from verity.main import create_app

_PARAM = re.compile(r"\{[^}]+\}")


def _shadows(parameterised: str, static: str) -> bool:
    """Would a request for `static` be swallowed by `parameterised` first?"""
    pattern = (
        "^"
        + "/".join(
            "[^/]+" if _PARAM.fullmatch(seg) else re.escape(seg) for seg in parameterised.split("/")
        )
        + "$"
    )
    return re.match(pattern, static) is not None


def _routes(node: object) -> list[tuple[str, str, str]]:
    """Every (method, path, name) in declaration order.

    FastAPI keeps an included router as its own match group rather than
    flattening it into ``app.routes``, so walk whichever child collection the
    installed version exposes.
    """
    inner = getattr(node, "original_router", None)
    if inner is not None:
        return _routes(inner)
    children = getattr(node, "routes", None)
    if children is not None:
        return [route for child in children for route in _routes(child)]
    path = getattr(node, "path", None)
    if path is None:
        return []
    name = getattr(node, "name", "?")
    methods: set[str] = getattr(node, "methods", None) or set()
    return [(method, path, name) for method in sorted(methods)]


def test_the_walker_actually_finds_the_routes() -> None:
    """Guards the test itself: a walker that returns nothing would pass vacuously."""
    paths = {path for _, path, _ in _routes(create_app())}
    assert "/vendors/{vendor_id}" in paths
    assert len(paths) > 100


def test_no_static_path_is_captured_by_an_earlier_parameterised_one() -> None:
    seen: list[tuple[str, str, str]] = []
    dead: list[str] = []
    for method, path, name in _routes(create_app()):
        if _PARAM.search(path) is None:
            dead += [
                f"{method} {path} ({name}) is captured by {earlier_path} ({earlier_name})"
                for earlier_method, earlier_path, earlier_name in seen
                if earlier_method == method and _shadows(earlier_path, path)
            ]
        seen.append((method, path, name))
    assert not dead, "unreachable routes:\n  " + "\n  ".join(dead)


@pytest.mark.parametrize("path", ["/vendors/findings", "/vendors/intake", "/vendors/roster"])
def test_the_cross_vendor_collections_are_declared_first(path: str) -> None:
    """These three shipped after ``/{vendor_id}`` and were dead on arrival."""
    order = [p for method, p, _ in _routes(create_app()) if method == "GET"]
    assert order.index(path) < order.index("/vendors/{vendor_id}")
