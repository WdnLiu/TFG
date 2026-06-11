from pddl_tools.core.models import Edge
from pddl_tools.parsers.invariant_parser import InvariantParser


def test_parses_groups_signatures_and_edges(mini_invariants):
    assert set(mini_invariants.groups) == {"mover", "load"}
    assert mini_invariants.action_signatures["go"] == ["mover", "0", "0"]
    assert mini_invariants.action_signatures["grab"] == ["mover", "0", "load"]
    assert mini_invariants.edges["go"]["mover"] == [Edge(src=0, dst=0)]
    assert mini_invariants.edges["grab"]["load"] == [Edge(src=0, dst=1)]
    assert mini_invariants.edges["stash"]["load"] == [Edge(src=1, dst=0)]


def test_empty_input_yields_empty_data():
    data = InvariantParser().parse("")
    assert data.groups == {}
    assert data.edges == {}
    assert data.action_signatures == {}


def test_indexed_group_ids_resolve_to_type_names(mini_invariants_indexed):
    assert set(mini_invariants_indexed.groups) == {"mover", "load"}
    load_states = [{p.name for p in state} for state in mini_invariants_indexed.groups["load"].states]
    assert load_states == [{"here"}, {"carrying"}]
    assert mini_invariants_indexed.edges["grab"]["load"] == [Edge(src=0, dst=1)]


def test_predicate_zero_resolves_to_declared_type(mini_invariant_path, mini_domain):
    data = InvariantParser().parse(mini_invariant_path.read_text(), mini_domain)
    here = next(iter(data.groups["mover"].states[0]))
    assert here.arg_types == ("mover", "place")


def test_star_marker_records_bound_arg(mini_domain):
    data = InvariantParser().parse("Invariant [block],[on[block,*block]];0\n", mini_domain)
    pred = next(iter(data.groups["block"].states[0]))
    assert pred.bound_arg == 1


def test_multi_state_group_arity_and_predicates(mini_domain):
    content = "Invariant [block],[ontable[block],holding[block],on[block,block]];0\n"
    group = InvariantParser().parse(content, mini_domain).groups["block"]
    assert group.arity == 3
    assert group.predicate_names == ["ontable", "holding", "on"]


def test_edge_with_explicit_bound_param(mini_domain):
    content = (
        "Invariant [block],[ontable[block],holding[block]];0\n"
        "Action STACK[block,block]\n"
        "Inv [block];0->1;1\n"
    )
    edge = InvariantParser().parse(content, mini_domain).edges["stack"]["block"][0]
    assert edge == Edge(src=0, dst=1, bound_param=1)


def test_multiple_edges_per_action_group(mini_domain):
    content = (
        "Invariant [block],[a[block],b[block],c[block]];0\n"
        "Action TWICE[block]\n"
        "Inv [block];0->1;0\n"
        "Inv [block];1->0;0\n"
    )
    data = InvariantParser().parse(content, mini_domain)
    assert len(data.edges["twice"]["block"]) == 2


def test_comments_and_malformed_lines_are_ignored(mini_domain):
    content = (
        "; comment\n# comment\n"
        "Invariant garbage\n"
        "Invariant [block],[a[block]];0\n"
        "Action garbage\n"
        "Inv garbage\n"
    )
    data = InvariantParser().parse(content, mini_domain)
    assert set(data.groups) == {"block"}
    assert data.action_signatures == {}
