from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pddl_tools.core.models import Domain, Problem
from pddl_tools.parsers.plan_parser import Plan
from pddl_tools.writers.pddl_writer import PDDLWriter

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VENDORED_VAL = _REPO_ROOT / "external" / "VAL" / "build" / "bin" / "Validate"


def _locate_val() -> Path | None:
    for name in ("Validate", "validate"):
        found = shutil.which(name)
        if found:
            return Path(found)
    if _VENDORED_VAL.exists() and _VENDORED_VAL.is_file():
        return _VENDORED_VAL
    return None


def val_available() -> bool:
    return _locate_val() is not None


@dataclass
class VALResult:
    ok: bool
    output: str
    exit_code: int

    def __bool__(self) -> bool:
        return self.ok


class VALValidator:
    def __init__(self, domain: Domain, problem: Problem):
        self._domain = domain
        self._problem = problem

    def validate(self, plan: Plan, *, timeout: int = 60) -> VALResult:
        binary = _locate_val()
        if binary is None:
            raise RuntimeError(
                "VAL binary not found. Install VAL and place `Validate` on PATH, "
                "or build the vendored copy with `make val-build`."
            )

        writer = PDDLWriter()
        with tempfile.TemporaryDirectory(prefix="val_check_") as tmp:
            tmp_dir = Path(tmp)
            dom_path = tmp_dir / "domain.pddl"
            prob_path = tmp_dir / "problem.pddl"
            plan_path = tmp_dir / "plan.txt"

            dom_path.write_text(writer.write_domain(self._domain))
            prob_path.write_text(writer.write_problem(self._problem, self._domain.name))
            plan_path.write_text(_format_plan(plan))

            proc = subprocess.run(
                [str(binary), str(dom_path), str(prob_path), str(plan_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        output = proc.stdout + proc.stderr
        ok = proc.returncode == 0 and "Plan valid" in proc.stdout
        return VALResult(ok=ok, output=output, exit_code=proc.returncode)


def _format_plan(plan: Plan) -> str:
    return "\n".join(str(step) for step in plan.steps) + "\n"
