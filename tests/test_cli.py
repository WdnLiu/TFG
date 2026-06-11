from pathlib import Path

import pytest

from pddl_tools.cli import main
from pddl_tools.parsers.fd_mutex_parser import fd_available
from pddl_tools.validation.val_validator import val_available

REPO = Path(__file__).resolve().parents[1]
BLOCKS = REPO / "external" / "pddl-to-htn" / "domains" / "Blocks" / "Track1" / "Typed"


def test_cli_unsupported_lotinac_domain_exits_with_error():
    domain, problem = BLOCKS / "domain.pddl", BLOCKS / "probBLOCKS-4-0.pddl"
    if not domain.exists():
        pytest.skip("Blocks benchmark not vendored")
    code = main([
        "--domain", str(domain), "--problem", str(problem),
        "--invariants", "lotinac", "--domain-name", "nonexistent",
    ])
    assert code == 2


@pytest.mark.skipif(
    not (fd_available() and val_available()),
    reason="CLI pipeline run requires Fast Downward and VAL",
)
def test_cli_runs_pipeline_and_writes_plan(tmp_path):
    domain, problem = BLOCKS / "domain.pddl", BLOCKS / "probBLOCKS-4-0.pddl"
    if not domain.exists():
        pytest.skip("Blocks benchmark not vendored")
    out = tmp_path / "plan.txt"
    code = main([
        "--domain", str(domain), "--problem", str(problem),
        "--invariants", "fd", "--out", str(out), "--timeout", "60",
    ])
    assert code == 0
    assert out.read_text().strip()
