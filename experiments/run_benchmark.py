from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from pddl_tools.abstraction.invariant_source import SOURCES, synthesize_invariants
from pddl_tools.parsers.domain_parser import DomainParser
from pddl_tools.pipeline import run_pipeline as pipeline_run
from pddl_tools.pipeline import safe_fd
from pddl_tools.validation.val_validator import VALValidator

SIZE_RE = re.compile(r"(\d+)")
FIELDS = (
    "domain", "problem", "size", "variant",
    "found", "valid", "plan_length", "runtime_s",
    "abstract_length", "inserts", "kept_statics", "skipped_groups",
    "attempts", "error",
)


@dataclass(frozen=True)
class DomainSpec:
    name: str
    domain_path: Path
    problem_dir: Path
    problem_glob: str


CORPUS_ROOT = REPO / "external" / "pddl-to-htn" / "domains"

DOMAINS = (
    DomainSpec("blocks", CORPUS_ROOT / "Blocks/Track1/Typed/domain.pddl",
               CORPUS_ROOT / "Blocks/Track1/Typed", "probBLOCKS-*.pddl"),
    DomainSpec("logistics", CORPUS_ROOT / "Logistics/Track1/Typed/domain.pddl",
               CORPUS_ROOT / "Logistics/Track1/Typed", "probLOGISTICS-*.pddl"),
    DomainSpec("logistics_fixed", CORPUS_ROOT / "Logistics/Track1/TypedFixed/domain.pddl",
               CORPUS_ROOT / "Logistics/Track1/TypedFixed", "probLOGISTICS-*.pddl"),
    DomainSpec("driverlog", CORPUS_ROOT / "DriverLog/Strips/driverlog.pddl",
               CORPUS_ROOT / "DriverLog/Strips", "pfile*"),
    DomainSpec("satellite", CORPUS_ROOT / "Satellite/Strips/stripsSat.pddl",
               CORPUS_ROOT / "Satellite/Strips", "pfile*"),
    DomainSpec("depots", CORPUS_ROOT / "Depots/Strips/Depots.pddl",
               CORPUS_ROOT / "Depots/Strips", "pfile*"),
    DomainSpec("zenotravel", CORPUS_ROOT / "ZenoTravel/Strips/zenotravelStrips.pddl",
               CORPUS_ROOT / "ZenoTravel/Strips", "pfile*"),
    DomainSpec("elevator", CORPUS_ROOT / "Elevator/m10-strips/domain.pddl",
               CORPUS_ROOT / "Elevator/m10-strips", "s*.pddl"),
    DomainSpec("rovers", CORPUS_ROOT / "Rovers/Strips/StripsRover.pddl",
               CORPUS_ROOT / "Rovers/Strips", "pfile*"),
    DomainSpec("freecell", CORPUS_ROOT / "FreeCell/Typed/domain.pddl",
               CORPUS_ROOT / "FreeCell/Typed", "probfreecell-*.pddl"),
)


def baseline_run(domain, problem, timeout):
    t0 = time.perf_counter()
    plan = safe_fd(domain, problem, timeout)
    runtime = time.perf_counter() - t0
    if plan is None:
        return {"found": False, "valid": False, "plan_length": None,
                "runtime_s": runtime, "abstract_length": None, "inserts": None,
                "kept_statics": None, "skipped_groups": None, "attempts": None,
                "error": ""}
    valid = VALValidator(domain, problem).validate(plan).ok
    return {"found": True, "valid": valid, "plan_length": len(plan),
            "runtime_s": runtime, "abstract_length": None, "inserts": None,
            "kept_statics": None, "skipped_groups": None, "attempts": None,
            "error": ""}


def run_one(args):
    spec_name, domain_path, problem_path, variant, timeout, source = args
    with redirect_stdout(io.StringIO()):
        dp = DomainParser()
        domain = dp.parse_domain(Path(domain_path).read_text())
        problem = dp.parse_problem(problem_path)
        if variant == "baseline":
            metrics = baseline_run(domain, problem, timeout)
        else:
            try:
                invariants = synthesize_invariants(
                    domain, domain_path, problem_path, source, spec_name)
            except ValueError as exc:
                metrics = {"found": False, "valid": False, "plan_length": None,
                           "runtime_s": 0.0, "abstract_length": None, "inserts": None,
                           "kept_statics": None, "skipped_groups": None,
                           "attempts": 0, "error": str(exc)[:80]}
            else:
                metrics = pipeline_run(domain, problem, invariants, timeout)

    size_match = SIZE_RE.search(Path(problem_path).name)
    metrics.update({
        "domain": spec_name,
        "problem": Path(problem_path).name,
        "size": int(size_match.group(1)) if size_match else 0,
        "variant": variant,
    })
    return metrics


def collect_jobs(timeout, domain_filter=None, max_size=None,
                 variants=("baseline", "pipeline"), source="fd"):
    jobs = []
    for spec in DOMAINS:
        if domain_filter and spec.name not in domain_filter:
            continue
        if not spec.domain_path.exists():
            continue
        for problem_path in sorted(spec.problem_dir.glob(spec.problem_glob)):
            size_match = SIZE_RE.search(problem_path.name)
            size = int(size_match.group(1)) if size_match else 0
            if max_size is not None and size > max_size:
                continue
            for variant in variants:
                jobs.append((
                    spec.name,
                    str(spec.domain_path),
                    str(problem_path),
                    variant,
                    timeout,
                    source,
                ))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", default=None)
    ap.add_argument("--max-size", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--variants", nargs="+", default=["baseline", "pipeline"],
                    choices=["baseline", "pipeline"])
    ap.add_argument("--invariants", choices=SOURCES, default="fd",
                    help="invariant source for the pipeline variant (default: fd)")
    ap.add_argument("--out", default=str(REPO / "experiments" / "results" / "benchmark.csv"))
    args = ap.parse_args()

    jobs = collect_jobs(args.timeout, args.domains, args.max_size,
                        tuple(args.variants), args.invariants)
    print(f"jobs={len(jobs)} workers={args.workers} timeout={args.timeout}s "
          f"invariants={args.invariants}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    completed = 0
    with open(out_path, "w", newline="") as f, ProcessPoolExecutor(max_workers=args.workers) as ex:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        futures = [ex.submit(run_one, job) for job in jobs]
        for fut in as_completed(futures):
            row = fut.result()
            writer.writerow({k: row.get(k) for k in FIELDS})
            f.flush()
            completed += 1
            if completed % 10 == 0 or completed == len(jobs):
                elapsed = time.perf_counter() - t0
                print(f"  {completed}/{len(jobs)} done | elapsed {elapsed:.1f}s")

    print(f"wrote {out_path} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
