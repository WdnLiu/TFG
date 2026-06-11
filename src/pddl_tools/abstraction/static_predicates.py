from pddl_tools.core.models import Domain


def detect_static_predicates(domain: Domain) -> set[str]:
    dynamic: set[str] = set()
    for action in domain.actions:
        for fluent in _flatten_effect(action.effect):
            dynamic.add(fluent[0])
    return set(domain.predicates) - dynamic


def _flatten_effect(effect: list) -> list[list]:
    if not effect:
        return []
    items = effect[1:] if effect and effect[0] == 'and' else [effect]
    fluents: list[list] = []
    for item in items:
        if not isinstance(item, list) or not item:
            continue
        if item[0] == 'not' and len(item) > 1 and isinstance(item[1], list):
            fluents.append(item[1])
        elif item[0] != 'not':
            fluents.append(item)
    return fluents
