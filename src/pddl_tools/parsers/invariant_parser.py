import re

from pddl_tools.core.models import (
    Domain,
    Edge,
    InvariantData,
    InvariantGroup,
    InvariantPredicate,
)

_PRED_BLOCK_RE = re.compile(r'([a-zA-Z0-9_-]+)\[([^\[\]]*)\]')
_INVARIANT_HEAD_RE = re.compile(r'\[(.*?)\]\s*,\s*\[(.*)\]')
_ACTION_HEAD_RE = re.compile(r'([a-zA-Z0-9_-]+)\[(.*?)\]')
_EDGE_BODY_RE = re.compile(r'^\s*(\d+)\s*->\s*(\d+)\s*$')
_GROUP_ID_RE = re.compile(r'\[(.*?)\]')


class InvariantParser:
    def parse(self, content: str, domain: Domain | None = None) -> InvariantData:
        self._domain = domain
        type_order = domain.type_order if domain else None

        data = InvariantData()
        current_action: str | None = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue

            if line.startswith('Invariant'):
                group = self._parse_invariant(line, type_order)
                if group is not None:
                    data.groups[group.group_id] = group
            elif line.startswith('Action'):
                name, signature = self._parse_action(line, type_order, data.groups)
                if name:
                    current_action = name
                    data.action_signatures[name] = signature
            elif line.startswith('Inv') and current_action is not None:
                group_id, edge = self._parse_edge(line, type_order)
                if group_id and edge is not None:
                    by_group = data.edges.setdefault(current_action, {})
                    by_group.setdefault(group_id, []).append(edge)

        return data

    def _parse_invariant(
        self, line: str, type_order: list[str] | None
    ) -> InvariantGroup | None:
        body = line.removeprefix('Invariant').split(';')[0].strip()
        match = _INVARIANT_HEAD_RE.match(body)
        if not match:
            return None

        group_id = self._translate_type_id(match.group(1).strip(), type_order)
        states: list[frozenset[InvariantPredicate]] = []

        for pred_name, args_block in _PRED_BLOCK_RE.findall(match.group(2)):
            raw_args = [t.strip() for t in args_block.split(',') if t.strip()]
            bound_arg = next(
                (idx for idx, tok in enumerate(raw_args) if tok.startswith('*')),
                0,
            )
            arg_types = tuple(
                self._translate_predicate_arg(
                    tok.lstrip('*'), pred_name.lower(), idx, type_order
                )
                for idx, tok in enumerate(raw_args)
            )
            predicate = InvariantPredicate(pred_name.lower(), arg_types, bound_arg)
            states.append(frozenset({predicate}))

        return InvariantGroup(group_id=group_id, states=states)

    def _parse_action(
        self,
        line: str,
        type_order: list[str] | None,
        groups: dict[str, InvariantGroup],
    ) -> tuple[str, list[str]]:
        body = line.removeprefix('Action').strip()
        match = _ACTION_HEAD_RE.match(body)
        if not match:
            return '', []

        name = match.group(1).lower()
        raw_signature = [t.strip() for t in match.group(2).split(',')]
        signature = [
            self._translate_signature_token(tok, type_order, groups)
            for tok in raw_signature
        ]
        return name, signature

    def _parse_edge(
        self, line: str, type_order: list[str] | None
    ) -> tuple[str, Edge | None]:
        parts = line.split(';')
        if len(parts) < 2:
            return '', None

        body = parts[0].removeprefix('Inv').strip()
        head = _GROUP_ID_RE.match(body)
        if not head:
            return '', None

        edge_match = _EDGE_BODY_RE.match(parts[1])
        if not edge_match:
            return '', None

        bound_param: int | None = None
        if len(parts) >= 3 and parts[2].strip().isdigit():
            bound_param = int(parts[2].strip())

        group_id = self._translate_type_id(head.group(1).strip(), type_order)
        edge = Edge(
            src=int(edge_match.group(1)),
            dst=int(edge_match.group(2)),
            bound_param=bound_param,
        )
        return group_id, edge

    def _translate_predicate_arg(
        self,
        token: str,
        predicate_name: str,
        position: int,
        type_order: list[str] | None,
    ) -> str:
        if token == '0' and self._domain is not None:
            declared = self._domain.predicates.get(predicate_name)
            if declared and 0 <= position < len(declared):
                decl_type = declared[position][1]
                if isinstance(decl_type, list):
                    # an (either t1 t2 ...) type: take the first concrete member
                    members = [t for t in decl_type if str(t).lower() != 'either']
                    return (str(members[0]) if members else 'object').lower()
                return str(decl_type).lower()
            return '0'
        return self._translate_type_id(token, type_order)

    def _translate_signature_token(
        self,
        token: str,
        type_order: list[str] | None,
        groups: dict[str, InvariantGroup],
    ) -> str:
        if not (type_order and token.isdigit() and self._domain is not None):
            return token
        idx = int(token)
        if not 0 <= idx < len(type_order):
            return token
        current: str | None = type_order[idx]
        while current is not None:
            if current in groups:
                return current
            current = self._domain.type_hierarchy.get(current)
        return '0'

    @staticmethod
    def _translate_type_id(token: str, type_order: list[str] | None) -> str:
        if type_order and token.isdigit():
            idx = int(token)
            if 0 <= idx < len(type_order):
                return type_order[idx]
        return token
