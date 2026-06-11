from __future__ import annotations

import contextlib
import os
import resource
import signal
import subprocess
import tempfile
from pathlib import Path

from pddl_tools.core.models import Domain, Problem
from pddl_tools.parsers.plan_parser import Plan, PlanParser
from pddl_tools.writers.pddl_writer import PDDLWriter

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FD_SCRIPT = _REPO_ROOT / "external" / "downward" / "fast-downward.py"


def fd_available() -> bool:
    return _FD_SCRIPT.exists()


def _preexec(mem_bytes: int | None):
    def _apply() -> None:
        os.setsid()
        if mem_bytes is not None:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    return _apply


def run_fd(
    domain: Domain,
    problem: Problem,
    *,
    alias: str = "lama-first",
    timeout: int = 120,
    work_dir: str | None = None,
    memory_mb: int | None = None,
) -> Plan | None:
    if not fd_available():
        raise RuntimeError(f"Fast Downward not found at {_FD_SCRIPT}")

    if memory_mb is None:
        env_cap = os.environ.get("FD_MEMORY_MB")
        memory_mb = int(env_cap) if env_cap else 3072

    workdir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="fd_run_"))
    workdir.mkdir(parents=True, exist_ok=True)

    domain_path = workdir / "domain.pddl"
    problem_path = workdir / "problem.pddl"

    writer = PDDLWriter()
    domain_path.write_text(writer.write_domain(domain))
    problem_path.write_text(writer.write_problem(problem, domain.name))

    mem_bytes = memory_mb * 1024 * 1024 if memory_mb else None
    proc = subprocess.Popen(
        [str(_FD_SCRIPT), "--alias", alias, str(domain_path), str(problem_path)],
        cwd=str(workdir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=_preexec(mem_bytes),
    )

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc.pid)
        proc.wait()
        raise

    plan_file = workdir / "sas_plan"
    if not plan_file.exists():
        return None
    return PlanParser().parse_file(str(plan_file))


def _kill_group(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(os.getpgid(pid), signal.SIGKILL)
