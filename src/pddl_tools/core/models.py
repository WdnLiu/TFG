from dataclasses import dataclass, field


def typed_param_map(tokens: list[str]) -> dict[str, str]:
    """Parse a PDDL typed list (``a b - t c - u``) into ``{name: type}``.

    Names without an explicit type are omitted; callers default them as needed.
    """
    mapping: dict[str, str] = {}
    pending: list[str] = []
    it = iter(tokens)
    for token in it:
        if token == '-':
            type_name = next(it)
            for name in pending:
                mapping[name] = type_name
            pending = []
        else:
            pending.append(token)
    return mapping


@dataclass(frozen=True)
class InvariantPredicate:
    name: str
    arg_types: tuple[str, ...]
    bound_arg: int = 0


@dataclass(frozen=True)
class Edge:
    src: int
    dst: int
    bound_param: int | None = None

    @property
    def is_self_loop(self) -> bool:
        return self.src == self.dst


@dataclass
class Action:
    name: str
    params: list[str]
    precond: list
    effect: list

    @property
    def param_vars(self) -> list[str]:
        return [token for token in self.params if token.startswith('?')]

    @property
    def var_types(self) -> dict[str, str]:
        return typed_param_map(self.params)

    def ground_preconditions(self, grounded_args: list[str]) -> list[list[str]]:
        mapping = dict(zip(self.param_vars, grounded_args, strict=False))
        if not self.precond:
            return []
        facts = self.precond[1:] if self.precond[0] == 'and' else [self.precond]
        grounded: list[list[str]] = []
        for fact in facts:
            if not isinstance(fact, list):
                continue
            if fact[0] in ('not', '='):
                continue
            if any(isinstance(token, list) for token in fact):
                continue
            grounded.append([mapping.get(token, token) for token in fact])
        return grounded


@dataclass
class Domain:
    name: str
    actions: list[Action]
    predicates: dict[str, list[tuple[str, str]]]
    types: dict[str, list[str]]
    type_hierarchy: dict[str, str]
    type_order: list[str] = field(default_factory=list)
    constants: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Problem:
    name: str
    objects: list[str]
    init: list[list[str]]
    goal: list

    @property
    def object_types(self) -> dict[str, str]:
        return typed_param_map(self.objects)


@dataclass
class InvariantGroup:
    group_id: str
    states: list[frozenset[InvariantPredicate]] = field(default_factory=list)

    @property
    def predicate_names(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for state in self.states:
            for pred in state:
                if pred.name not in seen:
                    seen.add(pred.name)
                    ordered.append(pred.name)
        return ordered

    @property
    def arity(self) -> int:
        return len(self.states)


@dataclass
class InvariantData:
    groups: dict[str, InvariantGroup] = field(default_factory=dict)
    edges: dict[str, dict[str, list[Edge]]] = field(default_factory=dict)
    action_signatures: dict[str, list[str]] = field(default_factory=dict)
