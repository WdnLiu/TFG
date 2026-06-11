import re

from pddl_tools.core.models import Action, Domain, Problem


class DomainParser:
    def parse_domain(self, content: str) -> Domain:
        structure = self._to_tree(self._tokenize(content))
        type_tokens = self._find_section(':types', structure[2:])
        types, type_hierarchy = self._parse_type_declarations(type_tokens)

        return Domain(
            name=structure[1][1],
            types=types,
            type_hierarchy=type_hierarchy,
            type_order=self._collect_type_order(type_tokens),
            predicates=self._parse_predicates(self._find_section(':predicates', structure[2:])),
            constants=self._extract_typed_params(self._find_section(':constants', structure[2:])),
            actions=[
                self._parse_action(s[1:])
                for s in structure[2:]
                if isinstance(s, list) and s[0] == ':action'
            ],
        )

    def _collect_type_order(self, tokens: list) -> list[str]:
        order: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if token == '-' or not isinstance(token, str):
                continue
            if token not in seen:
                seen.add(token)
                order.append(token)
        return order

    def parse_problem(self, path: str) -> Problem:
        with open(path) as f:
            structure = self._to_tree(self._tokenize(f.read()))

        objects: list[str] = []
        init: list[list[str]] = []
        goal: list = []

        for section in structure[2:]:
            if section[0] == ':objects':
                objects = section[1:]
            elif section[0] == ':init':
                init = [p for p in section[1:] if isinstance(p, list)]
            elif section[0] == ':goal':
                goal = section[1] if len(section) > 1 else []

        return Problem(name=structure[1][1], objects=objects, init=init, goal=goal)

    def _tokenize(self, text: str) -> list[str]:
        stripped = re.sub(r';.*', '', text.lower())
        return stripped.replace('(', ' ( ').replace(')', ' ) ').split()

    def _to_tree(self, tokens: list[str]) -> list | str:
        token = tokens.pop(0)
        if token != '(':
            return token
        subtree: list = []
        while tokens[0] != ')':
            subtree.append(self._to_tree(tokens))
        tokens.pop(0)
        return subtree

    def _find_section(self, keyword: str, sections: list) -> list:
        for section in sections:
            if isinstance(section, list) and section[0] == keyword:
                return section[1:]
        return []

    def _parse_type_declarations(self, tokens: list) -> tuple[dict[str, list[str]], dict[str, str]]:
        parent_to_children: dict[str, list[str]] = {}
        child_to_parent: dict[str, str] = {}
        pending: list[str] = []

        it = iter(tokens)
        for token in it:
            if token == '-':
                parent = next(it)
                parent_to_children.setdefault(parent, []).extend(pending)
                for child in pending:
                    child_to_parent[child] = parent
                pending = []
            else:
                pending.append(token)

        return parent_to_children, child_to_parent

    def _parse_predicates(self, sections: list) -> dict[str, list[tuple[str, str]]]:
        predicates: dict[str, list[tuple[str, str]]] = {}
        for pred_tokens in sections:
            if isinstance(pred_tokens, list):
                predicates[pred_tokens[0]] = self._extract_typed_params(pred_tokens[1:])
        return predicates

    def _extract_typed_params(self, tokens: list) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        pending: list[str] = []
        it = iter(tokens)
        for token in it:
            if token == '-':
                var_type = next(it)
                result.extend((var, var_type) for var in pending)
                pending = []
            else:
                pending.append(token)
        result.extend((var, 'object') for var in pending)
        return result

    def _parse_action(self, data: list) -> Action:
        return Action(
            name=data[0],
            params=self._find_by_key(':parameters', data),
            precond=self._find_by_key(':precondition', data),
            effect=self._find_by_key(':effect', data),
        )

    def _find_by_key(self, key: str, data: list) -> list:
        try:
            return data[data.index(key) + 1]
        except (ValueError, IndexError):
            return []
