# Invariant-Driven Abstraction for STRIPS Planning

A pipeline that simplifies classical (STRIPS) planning problems by deriving
state invariants, building a relaxed abstract domain from them, solving the
easier abstract problem, and refining the abstract plan back into a valid
concrete plan (validated with VAL).

## Requirements

- Python 3.10+
- A C++ toolchain and CMake (to build Fast Downward and VAL)
- git

The external tools are pinned as git submodules:

| Submodule | Path | Upstream |
|-----------|------|----------|
| Fast Downward | `external/downward/` | https://github.com/aibasel/downward |
| VAL | `external/VAL/` | https://github.com/KCL-Planning/VAL |
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
(`--invariants lotinac`) additionally needs `create_htn` rebuilt so it emits
the invariant graph:

```bash
cd external/pddl-to-htn/htn
sed -i 's/#define HTN_DEBUG false/#define HTN_DEBUG true/' bin/create_htn.h
g++ -O2 -o bin/create_htn bin/create_htn.cpp   # add forward decls to bin/basic.h on g++ >= 13
cd ../../..
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

## Tests and linting

```bash
pytest          # component tests (FD/VAL-dependent ones skip if not built)
ruff check .    # lint / code-quality checks
```
