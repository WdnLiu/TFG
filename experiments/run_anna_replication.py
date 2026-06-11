"""Replicate the scaling experiments of Buch Cardona (2024).

Anna's experiments fixed the number of locations and scaled the number of
agents 2, 4, 8, 16, 32 with a 600s timeout. She compared direct FD on the
original domain ("No abstraction") with her hand-crafted abstractions
("Abstraction 1" and "Abstraction 2"). This script runs the same setup
with our pipeline as a third method.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments"))

from generate_problem import generate_problem
from run_benchmark import pipeline_run, safe_fd

from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.parsers.invariant_parser import InvariantParser

ASSEMBLY_DOMAIN = REPO / "data" / "new_full_domain.pddl"
ASSEMBLY_INVARIANT_FILE = REPO / "data" / "invariant.in"

FIELDS = (
    "locations", "agents", "seed", "method",
    "ok", "plan_length", "runtime_s",
    "abstract_length", "inserts", "level", "error",
)


def _generate(n_locations: int, agents: int, seed: int) -> tuple[str, str]:
    n_trucks = max(1, agents // 2)
    n_drones = max(1, agents - n_trucks)
    text = generate_problem(
        n_locations=n_locations,
        n_workshops=max(2, n_locations // 25),
        n_drones=n_drones,
        n_trucks=n_trucks,
        n_items_per_type=max(2, n_locations // 40),
        assemble_i3=1,
        assemble_i4=1,
        seed=seed,
    )
    return text, f"locations={n_locations} agents={agents} (trucks={n_trucks}+drones={n_drones}) seed={seed}"


def _run_baseline(domain, problem, timeout):
    t0 = time.perf_counter()
    plan = safe_fd(domain, problem, timeout)
    dt = time.perf_counter() - t0
    if plan is None:
        return {"method": "baseline", "ok": False, "plan_length": None, "runtime_s": dt,
                "abstract_length": None, "inserts": None, "level": None,
                "error": "no plan or timeout"}
    return {"method": "baseline", "ok": True, "plan_length": len(plan.steps), "runtime_s": dt,
            "abstract_length": None, "inserts": None, "level": None, "error": ""}


def _run_pipeline(domain, problem, invariants, timeout):
    m = pipeline_run(domain, problem, invariants, timeout)
    return {"method": "pipeline", "ok": bool(m.get("valid")), "plan_length": m.get("plan_length"),
            "runtime_s": m.get("runtime_s"), "abstract_length": m.get("abstract_length"),
            "inserts": m.get("inserts"), "level": m.get("attempts"),
            "error": (m.get("error") or "")[:80]}


def run_one(n_locations: int, agents: int, seed: int, timeout: int) -> list[dict]:
    with redirect_stdout(io.StringIO()):
        problem_text, label = _generate(n_locations, agents, seed)
        tmp_problem = REPO / "experiments" / f".tmp_anna_{n_locations}_{agents}_{seed}.pddl"
        try:
            tmp_problem.write_text(problem_text)
            dp = DomainParser()
            domain_text = ASSEMBLY_DOMAIN.read_text()
            domain = dp.parse_domain(domain_text)
            problem = dp.parse_problem(str(tmp_problem))
            invariants = InvariantParser().parse(
                ASSEMBLY_INVARIANT_FILE.read_text(), domain)

            base = _run_baseline(domain, problem, timeout)
            pipe = _run_pipeline(domain, problem, invariants, timeout)
        finally:
            tmp_problem.unlink(missing_ok=True)

    common = {"locations": n_locations, "agents": agents, "seed": seed}
    print(f"  {label}: baseline={base['ok']}/{base['runtime_s']:.1f}s  pipeline={pipe['ok']}/{pipe['runtime_s']:.1f}s")
    return [{**common, **base}, {**common, **pipe}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locations", type=int, nargs="+", default=[50, 100])
    ap.add_argument("--agents", type=int, nargs="+", default=[2, 4, 8, 16, 32])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", default=str(REPO / "experiments" / "results" / "exp1_anna_replication.csv"))
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    rows: list[dict] = []
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for loc in args.locations:
            for ag in args.agents:
                for seed in args.seeds:
                    for row in run_one(loc, ag, seed, args.timeout):
                        w.writerow({k: row.get(k) for k in FIELDS})
                        rows.append(row)
                    f.flush()
    print(f"wrote {out} in {time.perf_counter() - t0:.1f}s ({len(rows)} rows)")


if __name__ == "__main__":
    main()
