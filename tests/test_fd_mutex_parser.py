import pytest

from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.parsers.fd_mutex_parser import FDMutexParser, fd_available

pytestmark = pytest.mark.skipif(
    not fd_available(),
    reason="Fast Downward translate module not available under external/downward/builds/release",
)


REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
BLOCKS_DIR = REPO_ROOT / "external" / "pddl-to-htn" / "domains" / "Blocks" / "Track1" / "Typed"


@pytest.fixture(scope="module")
def blocks_domain_and_problem():
    domain_path = BLOCKS_DIR / "domain.pddl"
    problem_path = BLOCKS_DIR / "probBLOCKS-10-0.pddl"
    if not (domain_path.exists() and problem_path.exists()):
        pytest.skip("Blocks benchmark domain not vendored")
    parser = DomainParser()
    with open(domain_path) as f:
        domain = parser.parse_domain(f.read())
    return domain, str(domain_path), str(problem_path)


def test_returns_block_bound_groups_with_states(blocks_domain_and_problem):
    domain, domain_path, problem_path = blocks_domain_and_problem
    data = FDMutexParser(domain, domain_path, problem_path).parse()
    assert data.groups, "expected at least one lifted mutex group from FD"
    assert "block" in {gid.rsplit("-", 1)[-1] for gid in data.groups}
    for group in data.groups.values():
        assert group.states, f"group {group.group_id} has no states"
        assert all(state for state in group.states), "states must be non-empty"


def test_mutex_parser_yields_no_edges_or_signatures(blocks_domain_and_problem):
    # FD supplies mutex groups only; edges/signatures are computed downstream.
    domain, domain_path, problem_path = blocks_domain_and_problem
    data = FDMutexParser(domain, domain_path, problem_path).parse()
    assert data.edges == {}
    assert data.action_signatures == {}
