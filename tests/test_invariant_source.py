import pytest

from pddl_tools.abstraction.invariant_source import SOURCES, synthesize_invariants
from pddl_tools.abstraction.lotinac_invariant_source import lotinac_domains
from pddl_tools.core.models import Domain


def _dummy_domain():
    return Domain(name="nonexistent", actions=[], predicates={}, types={},
                  type_hierarchy={})


def test_sources_are_fd_and_lotinac():
    assert SOURCES == ("fd", "lotinac")


def test_unknown_source_raises():
    with pytest.raises(ValueError, match="unknown invariant source"):
        synthesize_invariants(_dummy_domain(), "d.pddl", "p.pddl", source="bogus")


def test_lotinac_rejects_unsupported_domain():
    assert "nonexistent" not in lotinac_domains()
    with pytest.raises(ValueError, match="not available"):
        synthesize_invariants(
            _dummy_domain(), "d.pddl", "p.pddl",
            source="lotinac", domain_name="nonexistent",
        )
