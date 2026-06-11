from __future__ import annotations

import sys
from pathlib import Path

from pddl_tools.core.models import (
    Domain,
    InvariantData,
    InvariantGroup,
    InvariantPredicate,
)


def _type_names(t) -> list[str]:
    if isinstance(t, list) and t and t[0] == "either":
        return [s.lower() for s in t[1:] if isinstance(s, str)]
    if isinstance(t, str):
        return [t.lower()]
    return ["object"]


_REPO_ROOT = Path(__file__).resolve().parents[3]
_FD_BIN = _REPO_ROOT / "external" / "downward" / "builds" / "release" / "bin"
_FD_TRANSLATE = _FD_BIN / "translate"


def fd_available() -> bool:
    return (_FD_TRANSLATE / "invariant_finder.py").exists()


class FDMutexParser:
    def __init__(self, domain: Domain, domain_path: str, problem_path: str):
        self._domain = domain
        self._domain_path = domain_path
        self._problem_path = problem_path

    def parse(self) -> InvariantData:
        raw_groups = self._run_invariant_finder()
        patterns = self._lift(raw_groups)

        data = InvariantData()
        for idx, (predicates, bound_type) in enumerate(patterns):
            group_id = f"fd-{idx}-{bound_type}"
            states = [frozenset({pred}) for pred in predicates]
            data.groups[group_id] = InvariantGroup(group_id=group_id, states=states)
        return data

    def _run_invariant_finder(self) -> list:
        if not fd_available():
            raise RuntimeError(
                f"Fast Downward translate module not found under {_FD_TRANSLATE}. "
                "Ensure external/downward/ is checked out and its release build is in place."
            )

        sys.path.insert(0, str(_FD_BIN))
        saved_argv = sys.argv
        sys.argv = ["fd-translate", self._domain_path, self._problem_path]
        try:
            from translate import (  # type: ignore[import-not-found]
                invariant_finder,
                normalize,
                options,
                pddl_parser,
            )
            options.set_options()
            task = pddl_parser.open(
                domain_filename=self._domain_path,
                task_filename=self._problem_path,
            )
            normalize.normalize(task)
            return list(invariant_finder.get_groups(task))
        finally:
            sys.argv = saved_argv
            if str(_FD_BIN) in sys.path:
                sys.path.remove(str(_FD_BIN))

    def _lift(self, raw_groups: list) -> list[tuple[tuple[InvariantPredicate, ...], str]]:
        object_types = self._object_types()
        deduped: dict[tuple, tuple[tuple[InvariantPredicate, ...], str]] = {}

        for group in raw_groups:
            bound_object = self._infer_bound_object(group)
            if bound_object is None:
                continue
            bound_type = object_types.get(bound_object, "object")
            predicates = self._predicate_specs(group, bound_object, bound_type)
            if not predicates:
                continue
            key = (tuple(sorted(predicates, key=lambda p: (p.name, p.bound_arg))), bound_type)
            deduped.setdefault(key, (tuple(predicates), bound_type))

        return list(deduped.values())

    def _predicate_specs(
        self, group, bound_object: str, bound_type: str
    ) -> list[InvariantPredicate]:
        specs: list[InvariantPredicate] = []
        for fluent in group:
            args = list(fluent.args)
            bound_arg = next(
                (i for i, a in enumerate(args) if a == bound_object),
                None,
            )
            if bound_arg is None:
                continue

            declared = self._domain.predicates.get(fluent.predicate, [])
            if bound_arg < len(declared):
                expected = _type_names(declared[bound_arg][1])
                if not any(self._type_inherits(bound_type, t) for t in expected):
                    continue

            arg_types = tuple(
                _type_names(declared[i][1])[0] if i < len(declared) else "object"
                for i in range(len(args))
            )
            specs.append(
                InvariantPredicate(
                    name=fluent.predicate.lower(),
                    arg_types=arg_types,
                    bound_arg=bound_arg,
                )
            )
        return specs

    @staticmethod
    def _infer_bound_object(group) -> str | None:
        fluents = list(group)
        if not fluents:
            return None
        constants_per_fluent = [
            [a for a in fluent.args if not str(a).startswith("?")]
            for fluent in fluents
        ]
        if not all(constants_per_fluent):
            return None
        common = set(constants_per_fluent[0])
        for cs in constants_per_fluent[1:]:
            common &= set(cs)
        if not common:
            return None
        return next(iter(common))

    def _object_types(self) -> dict[str, str]:
        from pddl_tools.parsers.domain_parser import DomainParser

        return DomainParser().parse_problem(self._problem_path).object_types

    def _type_inherits(self, type_name: str, target) -> bool:
        if isinstance(target, list):
            return any(self._type_inherits(type_name, t) for t in _type_names(target))
        target_lower = target.lower()
        current: str | None = type_name.lower() if type_name else None
        while current is not None:
            if current == target_lower:
                return True
            current = self._domain.type_hierarchy.get(current)
        return False
