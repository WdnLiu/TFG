from pddl_tools.core.models import Action, Domain, Problem


class PDDLWriter:
    def write_domain(self, domain: Domain) -> str:
        lines = [
            f"(define (domain {domain.name})",
            "  (:requirements :strips :typing)",
        ]
        if domain.types or domain.type_hierarchy or domain.type_order:
            lines.append(f"  (:types {self._format_types(domain)})")
        if domain.constants:
            lines.append(f"  (:constants {self._format_typed_args(domain.constants).lstrip()})")
        if domain.predicates:
            lines.append("  (:predicates")
            for name, args in domain.predicates.items():
                lines.append(f"    ({name}{self._format_typed_args(args)})")
            lines.append("  )")
        for action in domain.actions:
            lines.extend(self._format_action(action))
        lines.append(")")
        return "\n".join(lines) + "\n"

    def write_problem(self, problem: Problem, domain_name: str) -> str:
        lines = [
            f"(define (problem {problem.name})",
            f"  (:domain {domain_name})",
        ]
        if problem.objects:
            lines.append(f"  (:objects {self._format_object_tokens(problem.objects)})")
        if problem.init:
            init_fluents = " ".join(self._format_fluent(fluent) for fluent in problem.init)
            lines.append(f"  (:init {init_fluents})")
        if problem.goal:
            lines.append(f"  (:goal {self._format_expression(problem.goal)})")
        lines.append(")")
        return "\n".join(lines) + "\n"

    def _format_types(self, domain: Domain) -> str:
        groups: dict[str, list[str]] = {}
        for child, parent in domain.type_hierarchy.items():
            groups.setdefault(parent, []).append(child)
        for parent in domain.types:
            groups.setdefault(parent, [])
        rooted = set(domain.type_hierarchy) | set(domain.types)
        for t in domain.type_order:
            if t not in rooted and t not in groups:
                groups.setdefault("object", []).append(t)
        parts: list[str] = []
        for parent, children in groups.items():
            if children:
                parts.append(f"{' '.join(children)} - {parent}")
            else:
                parts.append(parent)
        return " ".join(parts)

    def _format_typed_args(self, args: list) -> str:
        if not args:
            return ""
        return " " + " ".join(f"{var} - {self._format_type(t)}" for var, t in args)

    @staticmethod
    def _format_type(t) -> str:
        if isinstance(t, list) and t and t[0] == "either":
            return "(either " + " ".join(t[1:]) + ")"
        return str(t)

    def _format_object_tokens(self, tokens: list[str]) -> str:
        return " ".join(tokens)

    def _format_action(self, action: Action) -> list[str]:
        out = [f"  (:action {action.name}"]
        out.append(f"    :parameters ({self._format_param_tokens(action.params)})")
        out.append(f"    :precondition {self._format_expression(action.precond)}")
        out.append(f"    :effect {self._format_expression(action.effect)}")
        out.append("  )")
        return out

    def _format_param_tokens(self, tokens: list[str]) -> str:
        return " ".join(tokens)

    def _format_expression(self, expr) -> str:
        if expr is None or expr == []:
            return "()"
        if isinstance(expr, str):
            return expr
        return self._format_fluent(expr)

    def _format_fluent(self, fluent) -> str:
        if not isinstance(fluent, list):
            return str(fluent)
        if not fluent:
            return "()"
        rendered = []
        for token in fluent:
            if isinstance(token, list):
                rendered.append(self._format_fluent(token))
            else:
                rendered.append(str(token))
        return "(" + " ".join(rendered) + ")"
