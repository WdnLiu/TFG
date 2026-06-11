from pddl_tools.core.models import Action

Fluent = tuple[str, ...]


def conjuncts(expr) -> list[tuple[bool, list]]:
    if not expr:
        return []
    items = expr[1:] if isinstance(expr, list) and expr and expr[0] == 'and' else [expr]
    out: list[tuple[bool, list]] = []
    for item in items:
        if not isinstance(item, list) or not item:
            continue
        if item[0] == 'not' and len(item) > 1 and isinstance(item[1], list):
            out.append((False, item[1]))
        elif item[0] != 'not':
            out.append((True, item))
    return out


def ground(fluent: list, binding: dict[str, str]) -> Fluent:
    return tuple(binding.get(token, token) for token in fluent)


def unmet_preconditions(
    action: Action,
    binding: dict[str, str],
    state: set[Fluent],
) -> list[tuple[bool, Fluent]]:
    missing: list[tuple[bool, Fluent]] = []
    for positive, fluent in conjuncts(action.precond):
        grounded = ground(fluent, binding)
        if positive and grounded not in state:
            missing.append((True, grounded))
        elif not positive and grounded in state:
            missing.append((False, grounded))
    return missing


def apply_effect(
    action: Action,
    binding: dict[str, str],
    state: set[Fluent],
) -> None:
    adds: list[Fluent] = []
    dels: list[Fluent] = []
    for positive, fluent in conjuncts(action.effect):
        grounded = ground(fluent, binding)
        if positive:
            adds.append(grounded)
        else:
            dels.append(grounded)
    for fluent in dels:
        state.discard(fluent)
    for fluent in adds:
        state.add(fluent)


def format_fluent(fluent: Fluent) -> str:
    return "(" + " ".join(fluent) + ")"
