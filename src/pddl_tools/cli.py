"""Run the invariant-driven abstraction pipeline on a single PDDL instance.

Usage:
    python -m pddl_tools --domain D.pddl --problem P.pddl [--invariants fd|lotinac]

Or, after ``pip install -e .``:
    pddl-pipeline --domain D.pddl --problem P.pddl --invariants lotinac
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pddl_tools.abstraction.invariant_source import SOURCES, synthesize_invariants
from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.pipeline import run_pipeline
from pddl_tools.validation.val_validator import val_available
from pddl_tools.writers.pddl_writer import PDDLWriter


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pddl-pipeline",
        description="Abstract, plan, refine and validate a single PDDL problem.",
    )
    p.add_argument("--domain", required=True, help="path to the PDDL domain file")
    p.add_argument("--problem", required=True, help="path to the PDDL problem file")
    p.add_argument("--invariants", choices=SOURCES, default="fd",
                   help="invariant source: 'fd' (Fast Downward, any domain) or "
                        "'lotinac' (create_htn, selected domains). Default: fd.")
    p.add_argument("--domain-name", default=None,
                   help="domain key for the 'lotinac' source (e.g. blocks, logistics). "
                        "Defaults to the name declared in the domain file.")
    p.add_argument("--timeout", type=int, default=60,
                   help="per-planner-call timeout in seconds (default: 60)")
    p.add_argument("--out", default=None,
                   help="write the refined plan to this file")
    p.add_argument("--debug", action="store_true",
                   help="print the abstract domain and the full plan")
    p.add_argument("--save-files", metavar="DIR", default=None,
                   help="write abstract_domain.pddl, abstract_problem.pddl and "
                        "refined_plan.txt to DIR")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    domain_path = str(Path(args.domain).resolve())
    problem_path = str(Path(args.problem).resolve())

    dp = DomainParser()
    domain = dp.parse_domain(Path(domain_path).read_text())
    problem = dp.parse_problem(problem_path)
    domain_name = args.domain_name or domain.name

    print(f"domain    : {domain.name}  ({domain_path})")
    print(f"problem   : {problem.name}")
    print(f"invariants: {args.invariants}"
          + (f" (key={domain_name})" if args.invariants == "lotinac" else ""))

    try:
        invariants = synthesize_invariants(
            domain, domain_path, problem_path, args.invariants, domain_name)
    except ValueError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 2

    print(f"invariant groups: {len(invariants.groups)}")
    if not val_available():
        print("warning: VAL not found; refined plans will not be validated.",
              file=sys.stderr)

    result = run_pipeline(domain, problem, invariants, args.timeout)

    print("\n--- result ---")
    if not result["found"]:
        print(f"no valid plan ({result['attempts']} level(s) tried): {result['error']}")
        return 1

    print(f"valid          : {result['valid']}")
    print(f"abstract length: {result['abstract_length']}")
    print(f"refined length : {result['plan_length']}  (+{result['inserts']} inserted)")
    print(f"levels tried   : {result['attempts']}")
    print(f"runtime        : {result['runtime_s']:.2f}s")

    plan = result["plan"]
    plan_text = "\n".join(str(step) for step in plan) + "\n"
    abstract = result["abstract_domain"]

    if args.debug:
        print("\n--- abstract domain ---")
        print(PDDLWriter().write_domain(abstract))
        print("--- refined plan ---")
        print(plan_text, end="")

    if args.out:
        Path(args.out).write_text(plan_text)
        print(f"plan written to: {args.out}")

    if args.save_files:
        d = Path(args.save_files)
        d.mkdir(parents=True, exist_ok=True)
        w = PDDLWriter()
        (d / "abstract_domain.pddl").write_text(w.write_domain(abstract))
        (d / "abstract_problem.pddl").write_text(w.write_problem(problem, abstract.name))
        (d / "refined_plan.txt").write_text(plan_text)
        print(f"files written to: {d}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
