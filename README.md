# Invariant-Driven Abstraction for STRIPS Planning

A pipeline that simplifies classical (STRIPS) planning problems by deriving
state invariants, building a relaxed abstract domain from them, solving the
easier abstract problem, and refining the abstract plan back into a valid
concrete plan (validated with VAL).

The accompanying thesis is in [`thesis.pdf`](thesis.pdf).

## Repository layout

| Path | Contents |
|------|----------|
| `src/` | the `pddl_tools` package |
| `tests/` | component and end-to-end tests |
| `data/` | example PDDL domains, problems and invariant inputs |
| `experiments/` | benchmark and assembly-grid runners, and their results |
| `external/` | pinned submodules, plus `patches/` with local `pddl-to-htn` changes |
| `scripts/` | `build_lotinac.sh`, which patches and builds `create_htn` |

## Requirements

- Python 3.10+
- A C++ toolchain and CMake (to build Fast Downward and VAL)
- git

The external tools are pinned as git submodules:

| Submodule | Path | Upstream |
|-----------|------|----------|
| Fast Downward | `external/downward/` | https://github.com/WdnLiu/downward (fork of aibasel/downward) |
| VAL | `external/VAL/` | https://github.com/WdnLiu/VAL (fork of KCL-Planning/VAL) |
| pddl-to-htn (Lotinac) | `external/pddl-to-htn/` | https://github.com/dloti/pddl-to-htn |

## Installing dependencies and building

```bash
# 1. Clone with submodules (or: git submodule update --init --recursive)
git clone --recurse-submodules <repo-url>
cd TFG

# 2. Build Fast Downward (release)
./external/downward/build.py release

# 3. Build VAL
cd external/VAL && mkdir -p build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 .. && \
    make -j"$(nproc)"
cd ../../..

# 4. Create a virtual environment and install the package (with test and lint extras)
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The FD route (`--invariants fd`) works after step 2. The Lotinac route
(`--invariants lotinac`) additionally needs `create_htn` built from
`pddl-to-htn` with the local changes in `external/patches/`; one script
applies them and builds it:

```bash
./scripts/build_lotinac.sh
```

## Running the pipeline (single instance)

With the virtual environment active (`pddl-pipeline` is equivalent):

```bash
python -m pddl_tools --domain DOMAIN.pddl --problem PROBLEM.pddl --invariants fd
```

Flags:

| Flag | Description |
|------|-------------|
| `--domain PATH` | PDDL domain file (required) |
| `--problem PATH` | PDDL problem file (required) |
| `--invariants {fd,lotinac}` | invariant source (default `fd`) |
| `--domain-name NAME` | domain key for the `lotinac` source (defaults to the name declared in the domain) |
| `--timeout SECONDS` | per-planner-call timeout (default 60) |
| `--out FILE` | write the refined plan to `FILE` |
| `--save-files DIR` | write `abstract_domain.pddl`, `abstract_problem.pddl`, `refined_plan.txt` to `DIR` |
| `--debug` | print the abstract domain and the full plan |

## Outputs

Every run first prints a header identifying the instance:

```
domain    : <name>  (<path>)
problem   : <name>
invariants: <fd|lotinac> [(key=<name>)]
invariant groups: <N>
```

If a refined plan validates, the result block lists the metrics below and exits 0:

| Field | Meaning |
|-------|---------|
| `valid` | VAL accepted the refined plan (`False` if VAL is unavailable) |
| `abstract length` | number of steps in the abstract plan returned by Fast Downward |
| `refined length` | total steps in the refined concrete plan |
| `(+N inserted)` | concrete steps added by the per-step subplanner during refinement |
| `levels tried` | abstraction levels walked on the aggressiveness ladder before success |
| `runtime` | wall-clock time of the whole pipeline, in seconds |

Optional outputs depend on the flags: `--out FILE` writes the refined plan,
`--save-files DIR` additionally writes `abstract_domain.pddl` and
`abstract_problem.pddl`, and `--debug` echoes the abstract domain and plan
to stdout.

If no abstraction level produces a valid refined plan the result block
reports the cause and exits with a non-zero status:

| Output | Meaning | Exit code |
|--------|---------|-----------|
| `no valid plan (N level(s) tried): no abstract plan` | Fast Downward failed (or timed out) on the abstract problem | 1 |
| `no valid plan (N level(s) tried): <step> refine failed` | the per-step subplanner could not re-establish a dropped precondition | 1 |
| `no valid plan (N level(s) tried): invalid refined plan` | the refined plan was rejected by VAL | 1 |
| `error: <message>` (stderr) | the invariant source produced no graph for this domain | 2 |

## Tests and linting

```bash
pytest          # component tests (FD/VAL-dependent ones skip if not built)
ruff check .    # lint / code-quality checks
```
