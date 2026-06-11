from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def _safe_int(s):
    if s is None or s in ("", "None"):
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return None


def aggregate_levels(path: Path):
    rows = list(csv.DictReader(path.open()))
    out = defaultdict(lambda: {"found": 0, "valid": 0, "genuine": 0,
                                "total": 0, "level_distribution": []})
    for r in rows:
        domain = r.get("domain") or path.stem
        variant = r.get("variant") or r.get("source") or "pipeline"
        key = (domain, variant)
        bucket = out[key]
        bucket["total"] += 1
        if r.get("found") == "True":
            bucket["found"] += 1
        if r.get("valid") == "True":
            bucket["valid"] += 1
        ins = _safe_int(r.get("inserts"))
        if ins is not None and ins > 0:
            bucket["genuine"] += 1
        level = _safe_int(r.get("attempts"))
        if level is not None:
            bucket["level_distribution"].append(level)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for path in args.paths:
        if not path.exists():
            continue
        with path.open() as f:
            header = f.readline().strip().split(",")
        if "level" in header or "rung" in header:
            continue  # per-level CSVs handled separately
        per_dv = aggregate_levels(path)
        for (domain, variant), bucket in per_dv.items():
            level_distribution = bucket["level_distribution"]
            rows.append({
                "source": path.name,
                "domain": domain,
                "variant": variant,
                "total": bucket["total"],
                "found": bucket["found"],
                "valid": bucket["valid"],
                "genuine": bucket["genuine"],
                "modal_level": (
                    max(set(level_distribution), key=level_distribution.count) if level_distribution else None
                ),
                "min_level": min(level_distribution) if level_distribution else None,
                "max_level": max(level_distribution) if level_distribution else None,
            })

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(f"{'source':<40} {'domain':<14} {'variant':<9} {'total':>5} "
          f"{'valid':>6} {'genuine':>7} {'mode':>5} {'rmin':>5} {'rmax':>5}")
    for r in rows:
        print(
            f"{r['source']:<40} {r['domain']:<14} {r['variant']:<9} "
            f"{r['total']:>5} {r['valid']:>6} {r['genuine']:>7} "
            f"{r['modal_level'] or '-'!s:>5} "
            f"{r['min_level'] or '-'!s:>5} {r['max_level'] or '-'!s:>5}"
        )


if __name__ == "__main__":
    main()
