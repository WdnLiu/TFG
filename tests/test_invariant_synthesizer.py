from pathlib import Path

import pytest

from pddl_tools.abstraction.invariant_synthesizer import InvariantSynthesizer
from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.parsers.fd_mutex_parser import fd_available

REPO = Path(__file__).resolve().parents[1]
BLOCKS = REPO / "external" / "pddl-to-htn" / "domains" / "Blocks" / "Track1" / "Typed"

pytestmark = pytest.mark.skipif(
    not fd_available(),
    reason="invariant synthesis requires Fast Downward's mutex finder",
)


def test_synthesizer_adds_edges_and_signatures_to_fd_groups():
    domain_path, problem_path = BLOCKS / "domain.pddl", BLOCKS / "probBLOCKS-4-0.pddl"
    if not domain_path.exists():
        pytest.skip("Blocks benchmark not vendored")
    domain = DomainParser().parse_domain(domain_path.read_text())

    data = InvariantSynthesizer(domain, str(domain_path), str(problem_path)).synthesize()

    # FDMutexParser yields groups only; the synthesizer adds the action edges
    # and signatures the abstraction step consumes.
    assert data.groups
    assert data.edges
    assert data.action_signatures
    for by_group in data.edges.values():
        assert all(edges for edges in by_group.values())
