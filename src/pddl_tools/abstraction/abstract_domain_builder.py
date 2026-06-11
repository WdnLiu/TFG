from dataclasses import replace

from pddl_tools.abstraction.static_predicates import detect_static_predicates
from pddl_tools.core.models import (
    Action,
    Domain,
    Edge,
    InvariantData,
    InvariantGroup,
)
from pddl_tools.core.state import conjuncts

ABSTRACT_PREFIX = "abstract_"


def abstract_name(name: str) -> str:
    return f"{ABSTRACT_PREFIX}{name}"


def concrete_name(name: str) -> str:
    if name.startswith(ABSTRACT_PREFIX):
        return name[len(ABSTRACT_PREFIX):]
    return name


class AbstractDomainBuilder:
    def __init__(
        self,
        domain: Domain,
        invariants: InvariantData,
        keep_statics: bool = False,
        skip_groups: set[str] | None = None,
    ):
        self._domain = domain
        self._invariants = invariants
        self._keep_statics = keep_statics
        self._skip_groups = set(skip_groups) if skip_groups else set()
        self._statics = detect_static_predicates(domain)

    def build(self) -> Domain:
        abstract_actions = []
        for action in self._domain.actions:
            abstracted = self._abstract(action)
            if abstracted is action:
                abstract_actions.append(action)
            else:
                abstract_actions.append(replace(abstracted, name=abstract_name(action.name)))
        return replace(
            self._domain,
            name=abstract_name(self._domain.name),
            actions=abstract_actions,
        )

    def _abstract(self, action: Action) -> Action:
        edges_by_group = self._invariants.edges.get(action.name)
        if not edges_by_group:
            return action

        active = {gid: edges for gid, edges in edges_by_group.items()
                  if gid not in self._skip_groups}
        if not active:
            return action

        pre_fluents = _unwrap_and(action.precond)
        eff_adds, eff_dels = _split_effect(action.effect)
        return self._rewrite(action, active, pre_fluents, eff_adds, eff_dels)

    def _rewrite(
        self,
        action: Action,
        edges_by_group: dict,
        pre_fluents: list[list],
        eff_adds: list[list],
        eff_dels: list[list],
    ) -> Action:
        new_pre: list[list] = []
        new_add: list[list] = []
        new_del: list[list] = []

        for group_id, edges in edges_by_group.items():
            group = self._invariants.groups.get(group_id)
            if group is None or not group.states:
                continue
            bound_var = self._infer_bound_var(action, group_id)
            for edge in edges:
                bound = self._edge_bound_var(action, edge) or bound_var
                target_fluent = self._lift_target(group, edge, bound, eff_adds)
                if target_fluent is not None:
                    _append_unique(new_add, target_fluent)
                source_fluent = self._lift_source(group, edge, bound, pre_fluents, eff_dels)
                if source_fluent is None:
                    continue
                if source_fluent in eff_dels and source_fluent != target_fluent:
                    _append_unique(new_pre, source_fluent)
                    _append_unique(new_del, source_fluent)

        if self._keep_statics:
            for fluent in pre_fluents:
                if isinstance(fluent, list) and fluent and fluent[0] in self._statics:
                    _append_unique(new_pre, fluent)

        new_effects = list(new_add) + [['not', fluent] for fluent in new_del]

        return Action(
            name=action.name,
            params=list(action.params),
            precond=_wrap_and(new_pre),
            effect=_wrap_and(new_effects),
        )

    def _lift_source(
        self,
        group: InvariantGroup,
        edge: Edge,
        bound_var: str | None,
        pre_fluents: list[list],
        del_fluents: list[list],
    ) -> list | None:
        if not 0 <= edge.src < len(group.states):
            return None
        for pred in group.states[edge.src]:
            fluent = _find_fluent(pre_fluents, pred.name, pred.bound_arg, bound_var)
            if fluent is not None:
                return fluent
            fluent = _find_fluent(del_fluents, pred.name, pred.bound_arg, bound_var)
            if fluent is not None:
                return fluent
        return None

    def _lift_target(
        self,
        group: InvariantGroup,
        edge: Edge,
        bound_var: str | None,
        add_fluents: list[list],
    ) -> list | None:
        if not 0 <= edge.dst < len(group.states):
            return None
        for pred in group.states[edge.dst]:
            fluent = _find_fluent(add_fluents, pred.name, pred.bound_arg, bound_var)
            if fluent is not None:
                return fluent
        return None

    def _edge_bound_var(self, action: Action, edge: Edge) -> str | None:
        if edge.bound_param is None:
            return None
        variables = action.param_vars
        if 0 <= edge.bound_param < len(variables):
            return variables[edge.bound_param]
        return None

    def _infer_bound_var(self, action: Action, group_id: str) -> str | None:
        signature = self._invariants.action_signatures.get(action.name)
        if not signature or group_id not in signature:
            return None
        idx = signature.index(group_id)
        variables = action.param_vars
        if 0 <= idx < len(variables):
            return variables[idx]
        return None


def _find_fluent(
    fluents: list[list],
    name: str,
    bound_arg: int,
    bound_var: str | None,
) -> list | None:
    for fluent in fluents:
        if not isinstance(fluent, list) or not fluent or fluent[0] != name:
            continue
        if bound_var is None:
            return fluent
        position = 1 + bound_arg
        if position < len(fluent) and fluent[position] == bound_var:
            return fluent
    return None


def _unwrap_and(expr) -> list[list]:
    if not expr:
        return []
    if isinstance(expr, list) and expr and expr[0] == 'and':
        return [item for item in expr[1:] if isinstance(item, list)]
    if isinstance(expr, list):
        return [expr]
    return []


def _split_effect(expr) -> tuple[list[list], list[list]]:
    adds: list[list] = []
    dels: list[list] = []
    for positive, fluent in conjuncts(expr):
        (adds if positive else dels).append(fluent)
    return adds, dels


def _wrap_and(fluents: list[list]) -> list:
    if not fluents:
        return []
    if len(fluents) == 1:
        return fluents[0]
    return ['and', *fluents]


def _append_unique(target: list[list], fluent: list) -> None:
    if fluent not in target:
        target.append(fluent)
