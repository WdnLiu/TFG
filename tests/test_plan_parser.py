from pddl_tools.parsers.plan_parser import Plan, PlanParser, PlanStep


def test_parses_steps_and_cost(fixtures_dir):
    plan = PlanParser().parse_file(str(fixtures_dir / "sample_sas_plan"))
    assert plan.steps == [
        PlanStep(action="pick-up", args=("a1", "b")),
        PlanStep(action="move", args=("a1", "b", "a")),
        PlanStep(action="drop", args=("a1", "a", "item1")),
    ]
    assert plan.cost == 3


def test_empty_input_yields_empty_plan():
    plan = PlanParser().parse("")
    assert plan.steps == []
    assert plan.cost is None


def test_blank_and_comment_lines_skipped():
    content = "\n; header comment\n(go a b)\n\n; cost = 5\n"
    plan = PlanParser().parse(content)
    assert plan.steps == [PlanStep(action="go", args=("a", "b"))]
    assert plan.cost == 5


def test_lines_are_lowercased():
    plan = PlanParser().parse("(PICK-UP A1 B)\n")
    assert plan.steps == [PlanStep(action="pick-up", args=("a1", "b"))]


def test_malformed_line_skipped():
    plan = PlanParser().parse("not a valid step\n(go a b)\n")
    assert plan.steps == [PlanStep(action="go", args=("a", "b"))]


def test_plan_iteration_and_length():
    plan = Plan(steps=[PlanStep("a", ()), PlanStep("b", ("x",))])
    assert len(plan) == 2
    assert [s.action for s in plan] == ["a", "b"]


def test_plan_step_string_representation():
    assert str(PlanStep("go", ("a", "b"))) == "(go a b)"
    assert str(PlanStep("handempty", ())) == "(handempty)"
