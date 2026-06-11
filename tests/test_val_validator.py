from pathlib import Path

import pytest

from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.parsers.plan_parser import Plan, PlanParser, PlanStep
from pddl_tools.validation.val_validator import VALValidator, val_available

pytestmark = pytest.mark.skipif(
    not val_available(),
    reason="VAL binary not built; run `make val-build`",
)


REPO = Path(__file__).resolve().parents[1]
DOMAIN_PATH = REPO / "data" / "new_full_domain.pddl"
PROBLEM_PATH = REPO / "data" / "new_full_problem.pddl"


def _parse_world():
    if not (DOMAIN_PATH.exists() and PROBLEM_PATH.exists()):
        pytest.skip("Assembly domain/problem not present")
    dp = DomainParser()
    return dp.parse_domain(DOMAIN_PATH.read_text()), dp.parse_problem(str(PROBLEM_PATH))


def _solve_with_fd(domain, problem) -> Plan:
    import subprocess
    import tempfile
    fd = REPO / "external" / "downward" / "fast-downward.py"
    if not fd.exists():
        pytest.skip("Fast Downward not vendored")
    from pddl_tools.writers.pddl_writer import PDDLWriter
    workdir = Path(tempfile.mkdtemp(prefix="val_test_"))
    writer = PDDLWriter()
    (workdir / "domain.pddl").write_text(writer.write_domain(domain))
    (workdir / "problem.pddl").write_text(writer.write_problem(problem, domain.name))
    subprocess.run(
        [str(fd), "--alias", "lama-first",
         str(workdir / "domain.pddl"), str(workdir / "problem.pddl")],
        cwd=str(workdir), capture_output=True, text=True, timeout=120,
    )
    plan_file = workdir / "sas_plan"
    if not plan_file.exists():
        pytest.skip("FD failed to produce a plan")
    return PlanParser().parse_file(str(plan_file))


def test_val_accepts_valid_plan():
    domain, problem = _parse_world()
    plan = _solve_with_fd(domain, problem)
    result = VALValidator(domain, problem).validate(plan)
    assert result.ok, f"VAL rejected a plan FD produced: {result.output[-400:]}"
    assert result.exit_code == 0


def test_val_rejects_tampered_plan():
    domain, problem = _parse_world()
    plan = _solve_with_fd(domain, problem)
    if len(plan.steps) < 2:
        pytest.skip("plan too short to tamper")
    tampered = Plan(steps=plan.steps[1:], cost=plan.cost)
    result = VALValidator(domain, problem).validate(tampered)
    assert not result.ok
    assert result.exit_code != 0 or "Plan valid" not in result.output


def test_val_rejects_empty_plan_with_nontrivial_goal():
    domain, problem = _parse_world()
    result = VALValidator(domain, problem).validate(Plan(steps=[]))
    assert not result.ok


def test_val_unavailable_raises_helpful_error(monkeypatch):
    import pddl_tools.validation.val_validator as mod
    monkeypatch.setattr(mod, "_locate_val", lambda: None)
    domain, problem = _parse_world()
    with pytest.raises(RuntimeError, match="VAL binary not found"):
        VALValidator(domain, problem).validate(Plan(steps=[PlanStep("noop", ())]))
