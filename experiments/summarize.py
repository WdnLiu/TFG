from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def _safe_int(s: str | None) -> int | None:
    if s is None or s == "" or s == "None":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _safe_float(s: str | None) -> float | None:
    if s is None or s == "" or s == "None":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def summarize_levels(csv_path: Path) -> None:
    rows = list(csv.DictReader(csv_path.open()))
    if not rows:
        print(f"(empty) {csv_path}")
        return

    by_dv: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_dv[(r["domain"], r["variant"])].append(r)

    domains = sorted({r["domain"] for r in rows})
    print(f"\n=== {csv_path.name} ===")
    print(f"{'domain':<14} {'variant':<9} {'found':>8} {'valid':>8} "
          f"{'genuine':>9} {'med_len':>8} {'med_rt':>8}")

    for domain in domains:
        for variant in ("baseline", "pipeline"):
            cell = by_dv.get((domain, variant), [])
            if not cell:
                continue
            found = sum(1 for r in cell if r["found"] == "True")
            valid = sum(1 for r in cell if r["valid"] == "True")
            inserts = [_safe_int(r.get("inserts")) for r in cell]
            inserts = [i for i in inserts if i is not None]
            genuine = sum(1 for i in inserts if i > 0)
            lengths = [_safe_int(r.get("plan_length")) for r in cell]
            lengths = [n for n in lengths if n is not None]
            runtimes = [_safe_float(r.get("runtime_s")) for r in cell]
            runtimes = [t for t in runtimes if t is not None]
            print(
                f"{domain:<14} {variant:<9} "
                f"{found:>3}/{len(cell):<4} {valid:>3}/{len(cell):<4} "
                f"{genuine:>3}/{len(cell):<5} "
                f"{(statistics.median(lengths) if lengths else 0):>8.1f} "
                f"{(statistics.median(runtimes) if runtimes else 0):>8.2f}"
            )

    level_distribution = defaultdict(Counter)
    for r in rows:
        if r["variant"] != "pipeline" or r["valid"] != "True":
            continue
        level_distribution[r["domain"]][r.get("attempts", "")] += 1
    if any(level_distribution.values()):
        print("\nRung distribution (pipeline, valid):")
        for domain in sorted(level_distribution):
            dist = ", ".join(f"r{k}:{v}" for k, v in sorted(level_distribution[domain].items()))
            print(f"  {domain:<14} {dist}")


def summarize_all_levels(csv_path: Path) -> None:
    rows = list(csv.DictReader(csv_path.open()))
    if not rows:
        return

    by_dr: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        level = r.get("level", r.get("rung"))
        by_dr[(r["domain"], level)].append(r)

    print(f"\n=== {csv_path.name} (per-level ok rate) ===")
    print(f"{'domain':<14} {'level':>5} {'ok':>9} {'genuine':>9}")
    for (domain, level) in sorted(by_dr):
        cell = by_dr[(domain, level)]
        ok = sum(1 for r in cell if r["ok"] == "True")
        inserts = [_safe_int(r.get("inserts")) for r in cell]
        genuine = sum(1 for i in inserts if i is not None and i > 0)
        print(f"{domain:<14} {level:>5} {ok:>3}/{len(cell):<5} {genuine:>3}/{len(cell):<5}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args()

    for path in args.paths:
        if not path.exists():
            print(f"(missing) {path}")
            continue
        with path.open() as f:
            header = f.readline().strip().split(",")
        if "level" in header or "rung" in header:
            summarize_all_levels(path)
        else:
            summarize_levels(path)


if __name__ == "__main__":
    main()
