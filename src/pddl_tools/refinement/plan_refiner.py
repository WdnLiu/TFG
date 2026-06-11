from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from pddl_tools.abstraction.abstract_domain_builder import (
    ABSTRACT_PREFIX,
    concrete_name,
)
from pddl_tools.core.models import Action, Domain, Problem
from pddl_tools.core.state import (
    Fluent,
    apply_effect,
    conjuncts,
    format_fluent,
    ground,
)
from pddl_tools.parsers.plan_parser import Plan, PlanStep

Planner = Callable[[Domain, Problem], Plan | None]


@dataclass(frozen=True)
class RefinementFailure:
    step_index: int
    action: str
    reason: str

    def __str__(self) -> str:
        return f"step {self.step_index} ({self.action}): {self.reason}"


@dataclass
class RefinementResult:
    ok: bool
    plan: Plan | None = None
    failures: list[RefinementFailure] = field(default_factory=list)
    inserted_steps: int = 0

    def __bool__(self) -> bool:
        return self.ok


class PlanRefiner:
    def __init__(
        self,
        original_domain: Domain,
        abstract_domain: Domain,
        problem: Problem,
        planner: Planner,
        *,
        verbose: bool = False,
    ):
        self._original_domain = original_domain
        self._abstract_domain = abstract_domain
        self._problem = problem
        self._planner = planner
        self._original_actions: dict[str, Action] = {a.name: a for a in original_domain.actions}
        self._abstract_actions: dict[str, Action] = {a.name: a for a in abstract_domain.actions}
        self._verbose = verbose

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(f"[refiner] {msg}", flush=True)

    def refine(self, abstract_plan: Plan) -> RefinementResult:
        state: set[Fluent] = {tuple(fact) for fact in self._problem.init}
        refined_steps: list[PlanStep] = []
        failures: list[RefinementFailure] = []
        inserted = 0

        self._log(f"abstract plan has {len(abstract_plan.steps)} steps")
        for step in abstract_plan.steps:
            self._log(f"  abstract: {step}")

        for index, step in enumerate(abstract_plan.steps):
            if step.action.startswith(ABSTRACT_PREFIX):
                outcome = self._refine_abstract_step(index, step, state)
            else:
                outcome = self._apply_concrete_step(index, step, state)

            if outcome.failures:
                failures.extend(outcome.failures)
                continue

            refined_steps.extend(outcome.steps)
            inserted += outcome.inserted

        self._log(f"refined plan has {len(refined_steps)} steps, {inserted} inserted")
        failures.extend(self._check_goal(state, len(abstract_plan.steps)))

        if failures:
            return RefinementResult(ok=False, failures=failures, inserted_steps=inserted)

        refined_plan = Plan(steps=refined_steps, cost=len(refined_steps))
        return RefinementResult(ok=True, plan=refined_plan, inserted_steps=inserted)

    def _refine_abstract_step(
        self, index: int, step: PlanStep, state: set[Fluent]
    ) -> _StepOutcome:
        self._log(f"step {index}: abstract action {step.action}")
        original_name = concrete_name(step.action)
        original_action = self._original_actions.get(original_name)
        if original_action is None:
            return _StepOutcome(failures=[RefinementFailure(
                index, step.action, "original action not found for abstract step"
            )])

        params = original_action.param_vars
        if len(step.args) != len(params):
            return _StepOutcome(failures=[RefinementFailure(
                index, step.action,
                f"arity mismatch: expected {len(params)} args, got {len(step.args)}",
            )])

        binding = dict(zip(params, step.args, strict=False))
        precondition_targets = [
            ground(fluent, binding)
            for positive, fluent in conjuncts(original_action.precond)
            if positive
        ]
        self._log(
            f"  subplan goal (original preconditions): "
            f"{', '.join(format_fluent(a) for a in precondition_targets)}"
        )

        subplan = (
            self._subplan(state, precondition_targets)
            if precondition_targets else Plan(steps=[])
        )
        if subplan is None:
            return _StepOutcome(failures=[RefinementFailure(
                index, step.action,
                "subplanner found no plan to re-establish preconditions: "
                + ", ".join(format_fluent(fluent) for fluent in precondition_targets),
            )])

        self._log(f"  subplan returned {len(subplan.steps)} steps")
        steps: list[PlanStep] = []
        for sub_step in subplan.steps:
            sub_action = self._original_actions.get(sub_step.action)
            if sub_action is None:
                return _StepOutcome(failures=[RefinementFailure(
                    index, sub_step.action,
                    "subplanner returned unknown action",
                )])
            sub_binding = dict(zip(sub_action.param_vars, sub_step.args, strict=False))
            apply_effect(sub_action, sub_binding, state)
            steps.append(sub_step)
            self._log(f"    insert: {sub_step}")

        apply_effect(original_action, binding, state)
        original_step = PlanStep(action=original_name, args=step.args)
        steps.append(original_step)
        self._log(f"    apply: {original_step}")
        return _StepOutcome(steps=steps, inserted=len(steps) - 1)

    def _apply_concrete_step(
        self, index: int, step: PlanStep, state: set[Fluent]
    ) -> _StepOutcome:
        self._log(f"step {index}: concrete action {step.action}")
        action = self._original_actions.get(step.action)
        if action is None:
            return _StepOutcome(failures=[RefinementFailure(
                index, step.action, "action schema not found in original domain"
            )])

        params = action.param_vars
        if len(step.args) != len(params):
            return _StepOutcome(failures=[RefinementFailure(
                index, step.action,
                f"arity mismatch: expected {len(params)} args, got {len(step.args)}",
            )])

        binding = dict(zip(params, step.args, strict=False))
        apply_effect(action, binding, state)
        self._log(f"  applied: {step}")
        return _StepOutcome(steps=[step])

    def _subplan(self, state: set[Fluent], targets: list[Fluent]) -> Plan | None:
        sub_init = [list(fluent) for fluent in state]
        sub_goal = self._build_goal(targets)
        subproblem = Problem(
            name="refinement_subgoal",
            objects=list(self._problem.objects),
            init=sub_init,
            goal=sub_goal,
        )
        return self._planner(self._original_domain, subproblem)

    @staticmethod
    def _build_goal(targets: list[Fluent]) -> list:
        fluents = [list(fluent) for fluent in targets]
        if len(fluents) == 1:
            return fluents[0]
        return ['and', *fluents]

    def _check_goal(self, state: set[Fluent], plan_length: int) -> list[RefinementFailure]:
        failures: list[RefinementFailure] = []
        for positive, fluent in conjuncts(self._problem.goal):
            grounded = ground(fluent, {})
            if positive and grounded not in state:
                failures.append(RefinementFailure(
                    plan_length, "<goal>",
                    f"goal fluent not satisfied after refinement: {format_fluent(grounded)}",
                ))
            elif not positive and grounded in state:
                failures.append(RefinementFailure(
                    plan_length, "<goal>",
                    f"negated goal fluent not satisfied: {format_fluent(grounded)}",
                ))
        return failures


@dataclass
class _StepOutcome:
    steps: list[PlanStep] = field(default_factory=list)
    failures: list[RefinementFailure] = field(default_factory=list)
    inserted: int = 0
