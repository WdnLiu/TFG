"""The abstraction pipeline as a reusable library function.

``run_pipeline`` walks the aggressiveness ladder (most to least aggressive)
and returns the first abstraction whose refined plan validates. This is the
shared core used by both the command-line runner (:mod:`pddl_tools.cli`) and
the benchmark driver in ``experiments/``.
"""
from __future__ import annotations

import subprocess
import time

from pddl_tools.abstraction.abstract_domain_builder import AbstractDomainBuilder
from pddl_tools.core.models import Domain, InvariantData, Problem
from pddl_tools.planning.fd_runner import run_fd
from pddl_tools.refinement.plan_refiner import PlanRefiner
from pddl_tools.validation.val_validator import VALValidator


def safe_fd(domain, problem, timeout):
    """Run Fast Downward, treating a timeout as 'no plan' rather than an error."""
    try:
        return run_fd(domain, problem, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def build_levels(invariants: InvariantData):
    """Aggressiveness ladder: (keep_statics, skipped_groups) pairs, hardest first.

    Level 0 drops static preconditions; level 1 keeps them; each later level
    additionally skips one more invariant group, largest first.
    """
    ranked = sorted(
        invariants.groups.values(),
        key=lambda g: (len(g.states), g.group_id),
        reverse=True,
    )
    levels = [(False, set()), (True, set())]
    skipped: set[str] = set()
    for g in ranked:
        skipped = skipped | {g.group_id}
        levels.append((True, set(skipped)))
    return levels


def attempt(domain, problem, invariants, timeout, keep_statics, skip_groups):
    """Run one abstraction configuration end to end (build, plan, refine, validate)."""
    abstract = AbstractDomainBuilder(
        domain, invariants, keep_statics=keep_statics, skip_groups=skip_groups,
    ).build()
    abs_plan = safe_fd(abstract, problem, timeout)
    if abs_plan is None:
        return {"ok": False, "abs_len": None, "error": "no abstract plan"}
    refiner = PlanRefiner(domain, abstract, problem, lambda d, p: safe_fd(d, p, timeout))
    result = refiner.refine(abs_plan)
    if not result.ok or result.plan is None:
        err = str(result.failures[0]) if result.failures else "refine failed"
        return {"ok": False, "abs_len": len(abs_plan), "error": err}
    if not VALValidator(domain, problem).validate(result.plan).ok:
        return {"ok": False, "abs_len": len(abs_plan), "error": "invalid refined plan"}
    return {
        "ok": True,
        "abs_len": len(abs_plan),
        "abstract": abstract,
        "plan": result.plan,
        "plan_len": len(result.plan),
        "inserts": result.inserted_steps,
    }


def run_pipeline(
    domain: Domain,
    problem: Problem,
    invariants: InvariantData,
    timeout: int,
) -> dict:
    """Walk the aggressiveness ladder; return metrics for the first valid level."""
    t0 = time.perf_counter()
    levels = build_levels(invariants)
    last = None
    last_keep = None
    last_skip: set[str] = set()
    attempts = 0
    try:
        for keep_statics, skip in levels:
            attempts += 1
            last = attempt(domain, problem, invariants, timeout, keep_statics, skip)
            last_keep = keep_statics
            last_skip = skip
            if last["ok"]:
                return {
                    "found": True, "valid": True,
                    "plan": last["plan"],
                    "abstract_domain": last["abstract"],
                    "plan_length": last["plan_len"],
                    "runtime_s": time.perf_counter() - t0,
                    "abstract_length": last["abs_len"],
                    "inserts": last["inserts"],
                    "kept_statics": keep_statics,
                    "skipped_groups": ",".join(sorted(skip)) if skip else "",
                    "attempts": attempts,
                    "error": "",
                }
        return {
            "found": False, "valid": False, "plan": None, "plan_length": None,
            "runtime_s": time.perf_counter() - t0,
            "abstract_length": last["abs_len"] if last else None,
            "inserts": None,
            "kept_statics": last_keep,
            "skipped_groups": ",".join(sorted(last_skip)) if last_skip else "",
            "attempts": attempts,
            "error": (last["error"] if last else "no attempt")[:80],
        }
    except Exception as exc:
        return {"found": False, "valid": False, "plan": None, "plan_length": None,
                "runtime_s": time.perf_counter() - t0,
                "abstract_length": None, "inserts": None,
                "kept_statics": None, "skipped_groups": None,
                "attempts": attempts,
                "error": f"{type(exc).__name__}: {exc}"[:80]}
