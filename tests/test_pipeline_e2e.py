"""End-to-end tests: synthesize invariants, abstract, plan, refine, and validate
a real instance through the public ``run_pipeline`` entry point.

These exercise the whole stack and need Fast Downward and VAL built; they skip
otherwise.
"""
from pathlib import Path

import pytest

from pddl_tools.abstraction.invariant_source import synthesize_invariants
from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.parsers.fd_mutex_parser import fd_available
from pddl_tools.parsers.invariant_parser import InvariantParser
from pddl_tools.pipeline import run_pipeline
from pddl_tools.validation.val_validator import val_available

REPO = Path(__file__).resolve().parents[1]
BLOCKS = REPO / "external" / "pddl-to-htn" / "domains" / "Blocks" / "Track1" / "Typed"

pytestmark = pytest.mark.skipif(
    not (fd_available() and val_available()),
    reason="end-to-end tests require Fast Downward and VAL to be built",
)


def test_pipeline_blocks_fd_invariants_genuine():
    domain_path = BLOCKS / "domain.pddl"
    problem_path = BLOCKS / "probBLOCKS-4-0.pddl"
    if not (domain_path.exists() and problem_path.exists()):
        pytest.skip("Blocks benchmark not vendored")

    dp = DomainParser()
    domain = dp.parse_domain(domain_path.read_text())
    problem = dp.parse_problem(str(problem_path))
    invariants = synthesize_invariants(
        domain, str(domain_path), str(problem_path), source="fd", domain_name="blocks")

    result = run_pipeline(domain, problem, invariants, timeout=60)

    assert result["found"] and result["valid"]
    # FD drops the single-arm (handempty), so refinement must re-serialise picks.
    assert result["inserts"] > 0


def test_pipeline_assembly_handcrafted_invariants_genuine():
    domain_path = REPO / "data" / "new_full_domain.pddl"
    problem_path = REPO / "data" / "new_full_problem.pddl"
    invariant_path = REPO / "data" / "invariant.in"
    if not all(p.exists() for p in (domain_path, problem_path, invariant_path)):
        pytest.skip("assembly data files missing")

    dp = DomainParser()
    domain = dp.parse_domain(domain_path.read_text())
    problem = dp.parse_problem(str(problem_path))
    invariants = InvariantParser().parse(invariant_path.read_text(), domain)

    result = run_pipeline(domain, problem, invariants, timeout=60)

    assert result["found"] and result["valid"]
    assert result["inserts"] > 0
