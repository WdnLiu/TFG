from pathlib import Path

import pytest

from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.parsers.invariant_parser import InvariantParser

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def mini_domain_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "mini_domain.pddl"


@pytest.fixture
def mini_problem_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "mini_problem.pddl"


@pytest.fixture
def mini_invariant_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "mini_invariant.in"


@pytest.fixture
def mini_domain(mini_domain_path: Path):
    return DomainParser().parse_domain(mini_domain_path.read_text())


@pytest.fixture
def mini_problem(mini_problem_path: Path):
    return DomainParser().parse_problem(str(mini_problem_path))


@pytest.fixture
def mini_invariants(mini_invariant_path: Path):
    return InvariantParser().parse(mini_invariant_path.read_text())


@pytest.fixture
def mini_invariants_indexed(fixtures_dir: Path, mini_domain):
    content = (fixtures_dir / "mini_invariant_indexed.in").read_text()
    return InvariantParser().parse(content, mini_domain)


REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = REPO_ROOT / "external" / "pddl-to-htn" / "domains"


@pytest.fixture
def blocks_domain():
    path = BENCHMARKS / "Blocks" / "Track1" / "Typed" / "domain.pddl"
    if not path.exists():
        pytest.skip("Blocks benchmark domain not vendored")
    return DomainParser().parse_domain(path.read_text())


@pytest.fixture
def blocks_invariants(fixtures_dir: Path, blocks_domain):
    content = (fixtures_dir / "blocks" / "invariant.in").read_text()
    return InvariantParser().parse(content, blocks_domain)


@pytest.fixture
def logistics_domain():
    path = BENCHMARKS / "Logistics" / "Track1" / "Typed" / "domain.pddl"
    if not path.exists():
        pytest.skip("Logistics benchmark domain not vendored")
    return DomainParser().parse_domain(path.read_text())


@pytest.fixture
def logistics_invariants(fixtures_dir: Path, logistics_domain):
    content = (fixtures_dir / "logistics" / "invariant.in").read_text()
    return InvariantParser().parse(content, logistics_domain)
