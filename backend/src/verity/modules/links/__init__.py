"""The polymorphic link primitive (ADR-0003).

One table carries the long tail of the 360-degree model — any object linked to
any other — indexed in both directions. Hot, dashboard-critical pairs keep their
own explicit join tables; everything else links through here.

This is shared infrastructure, not a domain: it lives as a module only because
the layer rules put ``core`` below ``db`` (so a model, which needs ``Base``,
cannot live in ``core``). Other modules import ``links.service``; they never
touch ``links.models``. The link stores identity, never the human label — that
is resolved by whichever module owns the object, so it cannot go stale.
"""
