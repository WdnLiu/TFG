"""Invariant source backed by Lotinac's create_htn tool.

Runs the predecessor's invariant analysis (pddl-to-htn) and parses its output
into the same ``invariant.in`` text consumed by ``InvariantParser``, so the rest
of the pipeline receives an identical ``InvariantData`` and is untouched.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from pddl_tools.core.models import Domain, InvariantData
from pddl_tools.parsers.invariant_parser import InvariantParser

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HTN_DIR = _REPO_ROOT / "external" / "pddl-to-htn" / "htn"
_CREATE_HTN = _HTN_DIR / "bin" / "create_htn"

_ACT_RE = re.compile(r"^([A-Z][A-Za-z0-9_-]*)<-?\d+>\[([^\]]*)\]\s*$")
_INV_RE = re.compile(
    r"^Inv\s*\[([^\]]*)\]\s*,\s*\[.*?\]\s*,\s*(\[.*\])\s*;\s*(\d+)\s*->\s*(\d+)\s*$"
)


def create_htn_to_invariant_in(raw: str) -> str:
    """Convert create_htn stdout to the ``invariant.in`` format.

    create_htn emits ``Inv [id],[types],[preds];i->j`` with ``<N>`` version
    markers; InvariantParser wants ``Inv [id],[preds];i->j``. Strip the type
    block and the version markers, and drop duplicate edges.
    """

    def clean(preds: str) -> str:
        return re.sub(r"<-?\d+>", "", preds)

    actions: list[tuple[str, str, list[tuple[str, str, str, str]]]] = []
    invariants: dict[str, str] = {}
    current: tuple[str, str, list] | None = None
    synthetic: dict[str, str] = {}

    def group_id(gid: str, preds: str) -> str:
        # create_htn emits an empty type id for invariants whose bound predicate
        # has no typed argument (e.g. (handempty)). Assign a stable synthetic id
        # keyed on the predicate set so header and edges agree.
        if gid:
            return gid
        return synthetic.setdefault(preds, f"g{len(synthetic)}")

    for line in raw.splitlines():
        s = line.strip()
        m = _ACT_RE.match(s)
        if m:
            current = (m.group(1), m.group(2), [])
            actions.append(current)
            continue
        m = _INV_RE.match(s)
        if m and current is not None:
            preds = clean(m.group(2))
            gid = group_id(m.group(1), preds)
            edge = (gid, preds, m.group(3), m.group(4))
            if edge not in current[2]:
                current[2].append(edge)
            invariants.setdefault(gid, preds)

    out: list[str] = [f"Invariant [{gid}],{preds};0" for gid, preds in invariants.items()]
    out.append("")
    for name, args, edges in actions:
        if not edges:
            continue
        out.append(f"Action {name}[{args}]")
        out.extend(f"Inv [{gid}],{preds};{i}->{j}" for gid, preds, i, j in edges)
        out.append("")
    return "\n".join(out).strip() + "\n"


def run_create_htn(domain_name: str, domain_path: str, problem_path: str) -> str:
    """Run create_htn from its working directory so it locates ``domains/<name>/inv.txt``."""
    if not _CREATE_HTN.exists():
        raise RuntimeError(f"create_htn binary not found at {_CREATE_HTN}")
    inv_txt = _HTN_DIR / "domains" / domain_name / "inv.txt"
    if not inv_txt.exists():
        raise RuntimeError(
            f"Lotinac invariant candidates not found at {inv_txt}. "
            f"create_htn reads domains/{domain_name}/inv.txt (the Fast Downward candidates)."
        )
    proc = subprocess.run(
        [str(_CREATE_HTN), domain_name, str(Path(domain_path).resolve()),
         str(Path(problem_path).resolve())],
        cwd=_HTN_DIR, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"create_htn failed for {domain_name}: {proc.stdout}{proc.stderr}")
    return proc.stdout


def synthesize_lotinac(
    domain: Domain, domain_name: str, domain_path: str, problem_path: str
) -> InvariantData:
    """Produce InvariantData via Lotinac's create_htn, identical in shape to the
    hand-written ``invariant.in`` path."""
    raw = run_create_htn(domain_name, domain_path, problem_path)
    invariant_in = create_htn_to_invariant_in(raw)
    return InvariantParser().parse(invariant_in, domain)


# Benchmark domain name -> create_htn domain directory (where inv.txt lives).
# satellite is excluded (create_htn's parser rejects the (= ) precondition) and
# falls back to the Fast Downward path.
_LOTINAC_NAME = {
    "blocks": "blocks",
    "driverlog": "driverlog",
    "depots": "depots",
    "logistics": "logistics",
    "zenotravel": "zenotravel",
}


def lotinac_name(domain_name: str | None) -> str | None:
    """Map a benchmark domain name to its create_htn directory, or None if unsupported."""
    return _LOTINAC_NAME.get(domain_name or "")


def lotinac_domains() -> tuple[str, ...]:
    """Domain names for which Lotinac's create_htn invariants are available."""
    return tuple(sorted(_LOTINAC_NAME))
