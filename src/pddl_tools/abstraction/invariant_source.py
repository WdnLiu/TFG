"""Single entry point for choosing where invariants come from.

Two sources are supported:

- ``"fd"``      Fast Downward's lifted-mutex finder (works on every domain).
- ``"lotinac"`` The predecessor's ``create_htn`` analysis (available only for
                the domains in :func:`lotinac_domains`).
"""
from __future__ import annotations

from pddl_tools.core.models import Domain, InvariantData

SOURCES = ("fd", "lotinac")


def synthesize_invariants(
    domain: Domain,
    domain_path: str,
    problem_path: str,
    source: str = "fd",
    domain_name: str | None = None,
) -> InvariantData:
    """Synthesize invariants from the requested ``source``.

    Raises ``ValueError`` for an unknown source or when ``"lotinac"`` is asked
    for a domain it does not support.
    """
    if source == "fd":
        from pddl_tools.abstraction.invariant_synthesizer import InvariantSynthesizer
        return InvariantSynthesizer(domain, domain_path, problem_path).synthesize()

    if source == "lotinac":
        from pddl_tools.abstraction.lotinac_invariant_source import (
            lotinac_domains,
            lotinac_name,
            synthesize_lotinac,
        )
        name = lotinac_name(domain_name)
        if name is None:
            raise ValueError(
                f"Lotinac invariants are not available for domain "
                f"{domain_name!r}. Supported: {', '.join(lotinac_domains())}. "
                f"Use source='fd' instead."
            )
        return synthesize_lotinac(domain, name, domain_path, problem_path)

    raise ValueError(f"unknown invariant source {source!r}; expected one of {SOURCES}")
