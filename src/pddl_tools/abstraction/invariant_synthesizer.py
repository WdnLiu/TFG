from __future__ import annotations

from collections import defaultdict

from pddl_tools.core.models import (
    Action,
    Domain,
    Edge,
    InvariantData,
    InvariantGroup,
)
from pddl_tools.parsers.fd_mutex_parser import FDMutexParser


class InvariantSynthesizer:
    def __init__(self, domain: Domain, domain_path: str, problem_path: str):
        self._domain = domain
        self._domain_path = domain_path
        self._problem_path = problem_path

    def synthesize(self) -> InvariantData:
        data = FDMutexParser(self._domain, self._domain_path, self._problem_path).parse()
        for action in self._domain.actions:
            signature, edges = self._action_edges(action, data.groups)
            data.action_signatures[action.name.lower()] = signature
            if edges:
                data.edges[action.name.lower()] = edges
        return data

    def _action_edges(
        self, action: Action, groups: dict[str, InvariantGroup]
    ) -> tuple[list[str], dict[str, list[Edge]]]:
        var_types = _build_var_type_map(action.params)
        signature = [var_types.get(v, "object") for v in action.param_vars]

        adds, deletes = _effect_index(action)

        edges: dict[str, list[Edge]] = {}
        for gid, group in groups.items():
            bound_type = _group_bound_type(gid)
            per_var: dict[str, dict[str, int]] = defaultdict(dict)
            for state_idx, state in enumerate(group.states):
                for pred in state:
                    key = (pred.name, pred.bound_arg)
                    for var in adds.get(key, ()):
                        if self._types_overlap(var_types.get(var, "object"), bound_type):
                            per_var[var].setdefault("add", state_idx)
                    for var in deletes.get(key, ()):
                        if self._types_overlap(var_types.get(var, "object"), bound_type):
                            per_var[var].setdefault("del", state_idx)

            for var, info in per_var.items():
                src = info.get("del", info.get("add"))
                dst = info.get("add", info.get("del"))
                if src is None or dst is None:
                    continue
                if var not in action.param_vars:
                    continue
                param_idx = action.param_vars.index(var)
                edges.setdefault(gid, []).append(
                    Edge(src=src, dst=dst, bound_param=param_idx)
                )

            if gid not in edges:
                self._add_precondition_self_loop(action, group, signature, edges)

        return signature, edges

    def _add_precondition_self_loop(
        self,
        action: Action,
        group: InvariantGroup,
        signature: list[str],
        edges: dict[str, list[Edge]],
    ) -> None:
        """Record a 0->0 self-loop when the action requires the invariant's state
        in its precondition but does not transition between states (e.g. an action
        that reads but never changes the bound predicate)."""
        if not group.states:
            return
        pre_facts = _flat_conjuncts(action.precond)
        pre_names = {f[0].lower() for f in pre_facts if isinstance(f, list) and f}
        state_0_names = {pred.name for pred in group.states[0]}
        if not (pre_names & state_0_names):
            return
        bound_type = _group_bound_type(group.group_id)
        for i, vtype in enumerate(signature):
            if self._types_overlap(vtype, bound_type):
                edges.setdefault(group.group_id, []).append(
                    Edge(src=0, dst=0, bound_param=i)
                )
                return

    def _types_overlap(self, var_type: str, bound_type: str) -> bool:
        return self._is_subtype(var_type, bound_type) or self._is_subtype(bound_type, var_type)

    def _is_subtype(self, child: str, ancestor: str) -> bool:
        ancestor_l = ancestor.lower()
        current: str | None = child.lower() if child else None
        while current is not None:
            if current == ancestor_l:
                return True
            current = self._domain.type_hierarchy.get(current)
        return False


def _flat_conjuncts(expr) -> list:
    if not expr:
        return []
    if isinstance(expr, list) and expr and expr[0] == "and":
        return list(expr[1:])
    return [expr]


def _effect_index(action: Action) -> tuple[dict, dict]:
    adds: dict[tuple[str, int], set[str]] = defaultdict(set)
    deletes: dict[tuple[str, int], set[str]] = defaultdict(set)
    for eff in _flat_conjuncts(action.effect):
        if not isinstance(eff, list) or not eff:
            continue
        if eff[0] == "not" and len(eff) > 1 and isinstance(eff[1], list):
            inner = eff[1]
            for pos, arg in enumerate(inner[1:]):
                deletes[(inner[0].lower(), pos)].add(arg)
        else:
            for pos, arg in enumerate(eff[1:]):
                adds[(eff[0].lower(), pos)].add(arg)
    return adds, deletes


def _build_var_type_map(params: list[str]) -> dict[str, str]:
    var_types: dict[str, str] = {}
    pending: list[str] = []
    it = iter(params)
    for token in it:
        if token == "-":
            t = next(it).lower()
            for v in pending:
                var_types[v] = t
            pending = []
        else:
            pending.append(token)
    return var_types


def _group_bound_type(group_id: str) -> str:
    parts = group_id.split("-", 2)
    return parts[-1] if len(parts) == 3 else group_id
