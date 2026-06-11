from pddl_tools.parsers.domain_parser import DomainParser


def test_parses_action_names(mini_domain):
    names = {a.name for a in mini_domain.actions}
    assert names == {"go", "grab", "stash"}


def test_parses_type_hierarchy(mini_domain):
    assert mini_domain.type_hierarchy["mover"] == "thing"
    assert mini_domain.type_hierarchy["load"] == "thing"
    assert mini_domain.type_hierarchy["thing"] == "object"


def test_parses_predicate_arities(mini_domain):
    assert len(mini_domain.predicates["here"]) == 2
    assert len(mini_domain.predicates["link"]) == 2
    assert len(mini_domain.predicates["carrying"]) == 2


def test_untyped_predicates_default_to_object():
    from pddl_tools.parsers.domain_parser import DomainParser
    text = "(define (domain d) (:requirements :strips) (:predicates (on ?x ?y) (clear ?x) (handempty)))"
    domain = DomainParser().parse_domain(text)
    assert domain.predicates["on"] == [("?x", "object"), ("?y", "object")]
    assert domain.predicates["clear"] == [("?x", "object")]
    assert domain.predicates["handempty"] == []


def test_parses_problem(mini_problem):
    assert mini_problem.name == "mini-task"
    assert mini_problem.goal[0] == "and"
    assert ["here", "x1", "c"] in mini_problem.goal[1:]


def test_empty_action_section_yields_no_actions():
    src = "(define (domain empty) (:requirements :strips :typing) (:types thing - object))"
    domain = DomainParser().parse_domain(src)
    assert domain.actions == []
    assert domain.name == "empty"
