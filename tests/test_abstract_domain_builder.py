from pddl_tools.abstraction.abstract_domain_builder import (
    AbstractDomainBuilder,
    abstract_name,
)
from pddl_tools.core.models import InvariantData


def _action(domain, name: str):
    target = abstract_name(name)
    for action in domain.actions:
        if action.name in (target, name):
            return action
    raise AssertionError(f"action {name!r} not found")


def _fluents_in_and(expr):
    if not expr:
        return []
    if expr[0] == 'and':
        return list(expr[1:])
    return [expr]


def test_passthrough_when_no_edges_at_all(mini_domain):
    empty = InvariantData()
    abstract = AbstractDomainBuilder(mini_domain, empty).build()
    assert abstract.name == abstract_name(mini_domain.name)
    assert abstract.actions == mini_domain.actions
    for original, rewritten in zip(mini_domain.actions, abstract.actions, strict=False):
        assert rewritten is original


def test_blocks_pick_up_collapses_to_two_invariant_fluents(blocks_domain, blocks_invariants):
    abstract = AbstractDomainBuilder(blocks_domain, blocks_invariants).build()
    pick_up = _action(abstract, "pick-up")
    pre = _fluents_in_and(pick_up.precond)
    eff = _fluents_in_and(pick_up.effect)
    assert ['clear', '?x'] in pre
    assert ['ontable', '?x'] in pre
    assert ['handempty'] not in pre
    assert ['holding', '?x'] in eff
    assert ['not', ['clear', '?x']] in eff
    assert ['not', ['ontable', '?x']] in eff


def test_blocks_stack_dedups_holding_across_invariants(blocks_domain, blocks_invariants):
    abstract = AbstractDomainBuilder(blocks_domain, blocks_invariants).build()
    stack = _action(abstract, "stack")
    pre = _fluents_in_and(stack.precond)
    eff = _fluents_in_and(stack.effect)
    assert pre.count(['holding', '?x']) == 1
    assert ['clear', '?y'] in pre
    assert eff.count(['on', '?x', '?y']) == 1
    assert ['clear', '?x'] in eff
    assert ['not', ['holding', '?x']] in eff
    assert ['not', ['clear', '?y']] in eff


def test_logistics_drive_truck_drops_static_in_city(logistics_domain, logistics_invariants):
    abstract = AbstractDomainBuilder(logistics_domain, logistics_invariants).build()
    drive = _action(abstract, "drive-truck")
    pre = _fluents_in_and(drive.precond)
    eff = _fluents_in_and(drive.effect)
    assert ['at', '?truck', '?loc-from'] in pre
    assert ['in-city', '?loc-from', '?city'] not in pre
    assert ['at', '?truck', '?loc-to'] in eff
    assert ['not', ['at', '?truck', '?loc-from']] in eff


def test_keep_statics_retains_in_city(logistics_domain, logistics_invariants):
    abstract = AbstractDomainBuilder(
        logistics_domain, logistics_invariants, keep_statics=True).build()
    drive = _action(abstract, "drive-truck")
    pre = _fluents_in_and(drive.precond)
    assert ['in-city', '?loc-from', '?city'] in pre


def test_logistics_load_truck_drops_truck_co_location(
    logistics_domain, logistics_invariants
):
    abstract = AbstractDomainBuilder(logistics_domain, logistics_invariants).build()
    load = _action(abstract, "load-truck")
    pre = _fluents_in_and(load.precond)
    eff = _fluents_in_and(load.effect)
    assert ['at', '?pkg', '?loc'] in pre
    assert ['at', '?truck', '?loc'] not in pre
    assert ['in', '?pkg', '?truck'] in eff
    assert ['not', ['at', '?pkg', '?loc']] in eff


def test_logistics_fly_airplane_passes_through(logistics_domain, logistics_invariants):
    abstract = AbstractDomainBuilder(logistics_domain, logistics_invariants).build()
    original_fly = _action(logistics_domain, "fly-airplane")
    abstract_fly = _action(abstract, "fly-airplane")
    assert abstract_fly is original_fly


def test_bound_param_inferred_from_signature_when_missing(mini_domain, mini_invariants):
    abstract = AbstractDomainBuilder(mini_domain, mini_invariants).build()
    grab = _action(abstract, "grab")
    pre = _fluents_in_and(grab.precond)
    eff = _fluents_in_and(grab.effect)
    assert ['here', '?l', '?p'] in pre
    assert ['carrying', '?l', '?m'] in eff
    assert ['not', ['here', '?l', '?p']] in eff
