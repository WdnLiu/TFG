from pddl_tools.abstraction.abstract_domain_builder import abstract_name
from pddl_tools.core.models import Action, Domain, Problem
from pddl_tools.parsers.plan_parser import Plan, PlanStep
from pddl_tools.refinement.plan_refiner import PlanRefiner


def _mini_world():
    actions = [
        Action(
            name="move",
            params=["?a", "-", "agent", "?l1", "-", "loc", "?l2", "-", "loc"],
            precond=["and", ["at", "?a", "?l1"]],
            effect=["and", ["not", ["at", "?a", "?l1"]], ["at", "?a", "?l2"]],
        ),
        Action(
            name="pick-up",
            params=["?a", "-", "agent", "?l", "-", "loc", "?i", "-", "item"],
            precond=["and", ["at", "?a", "?l"], ["at", "?i", "?l"]],
            effect=["and", ["not", ["at", "?i", "?l"]], ["holding", "?a", "?i"]],
        ),
    ]
    domain = Domain(
        name="mini",
        actions=actions,
        predicates={
            "at": [("?x", "object"), ("?l", "loc")],
            "holding": [("?a", "agent"), ("?i", "item")],
        },
        types={},
        type_hierarchy={},
        type_order=[],
    )
    problem = Problem(
        name="mini",
        objects=["a1", "-", "agent", "i1", "-", "item", "l1", "l2", "-", "loc"],
        init=[["at", "a1", "l1"], ["at", "i1", "l2"]],
        goal=["holding", "a1", "i1"],
    )
    return domain, problem


def _mini_abstract(domain):
    abstract_actions = [
        Action(
            name="move",
            params=domain.actions[0].params,
            precond=domain.actions[0].precond,
            effect=domain.actions[0].effect,
        ),
        Action(
            name=abstract_name("pick-up"),
            params=domain.actions[1].params,
            precond=["at", "?i", "?l"],
            effect=domain.actions[1].effect,
        ),
    ]
    return Domain(
        name=abstract_name(domain.name),
        actions=abstract_actions,
        predicates=domain.predicates,
        types=domain.types,
        type_hierarchy=domain.type_hierarchy,
        type_order=domain.type_order,
    )


def test_refiner_inserts_subplan_then_original_action():
    domain, problem = _mini_world()
    abstract = _mini_abstract(domain)
    abstract_plan = Plan(steps=[PlanStep(abstract_name("pick-up"), ("a1", "l2", "i1"))])

    def planner(d, p):
        return Plan(steps=[PlanStep("move", ("a1", "l1", "l2"))])

    result = PlanRefiner(domain, abstract, problem, planner).refine(abstract_plan)
    assert result.ok, [str(f) for f in result.failures]
    assert result.inserted_steps == 1
    assert [s.action for s in result.plan.steps] == ["move", "pick-up"]


def test_refiner_returns_failure_when_subplan_does_not_exist():
    domain, problem = _mini_world()
    abstract = _mini_abstract(domain)
    abstract_plan = Plan(steps=[PlanStep(abstract_name("pick-up"), ("a1", "l2", "i1"))])

    def planner(d, p):
        return None

    result = PlanRefiner(domain, abstract, problem, planner).refine(abstract_plan)
    assert not result.ok
    assert any("no plan" in f.reason or "re-establish" in f.reason for f in result.failures)


def test_refiner_passes_through_when_step_is_not_abstract():
    domain, problem = _mini_world()
    abstract = _mini_abstract(domain)
    problem.goal = ["at", "a1", "l2"]
    abstract_plan = Plan(steps=[PlanStep("move", ("a1", "l1", "l2"))])

    def planner(d, p):
        raise AssertionError("subplanner should not be called for passthrough actions")

    result = PlanRefiner(domain, abstract, problem, planner).refine(abstract_plan)
    assert result.ok, [str(f) for f in result.failures]
    assert result.inserted_steps == 0
    assert result.plan.steps == abstract_plan.steps


def test_refiner_subgoal_is_original_action_preconditions():
    domain, problem = _mini_world()
    abstract = _mini_abstract(domain)
    abstract_plan = Plan(steps=[PlanStep(abstract_name("pick-up"), ("a1", "l2", "i1"))])

    captured_goals = []

    def planner(d, p):
        captured_goals.append(p.goal)
        return None

    PlanRefiner(domain, abstract, problem, planner).refine(abstract_plan)
    goal = captured_goals[0]
    assert goal == ["and", ["at", "a1", "l2"], ["at", "i1", "l2"]]
