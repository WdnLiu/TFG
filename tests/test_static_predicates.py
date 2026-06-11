from pddl_tools.abstraction.static_predicates import detect_static_predicates


def test_link_is_static_in_mini(mini_domain):
    assert detect_static_predicates(mini_domain) == {"link"}


def test_in_city_is_static_in_logistics(logistics_domain):
    assert detect_static_predicates(logistics_domain) == {"in-city"}


def test_blocks_has_no_static_predicates(blocks_domain):
    assert detect_static_predicates(blocks_domain) == set()
