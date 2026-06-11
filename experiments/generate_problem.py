import random


def generate_problem(
    *,
    n_locations: int,
    n_workshops: int = 2,
    n_drones: int = 1,
    n_trucks: int = 1,
    n_items_per_type: int = 2,
    assemble_i3: int = 1,
    assemble_i4: int = 1,
    seed: int,
) -> str:
    rng = random.Random(seed)

    locs = [f"loc{i+1}" for i in range(n_locations)]
    workshops = [f"ws{i+1}" for i in range(n_workshops)]
    all_locations = locs + workshops

    drones = [f"drone{i+1}" for i in range(n_drones)]
    trucks = [f"truck{i+1}" for i in range(n_trucks)]

    items = {t: [f"i{t}_{j+1}" for j in range(n_items_per_type)] for t in range(3)}
    goal_items_i3 = [f"i3_g{k+1}" for k in range(assemble_i3)]
    goal_items_i4 = [f"i4_g{k+1}" for k in range(assemble_i4)]

    nodes = all_locations[:]
    rng.shuffle(nodes)
    edges: set[tuple[str, str]] = set()
    for i in range(len(nodes) - 1):
        edges.add((nodes[i], nodes[i + 1]))
        edges.add((nodes[i + 1], nodes[i]))
    for _ in range(len(nodes)):
        a, b = rng.sample(nodes, 2)
        if a != b:
            edges.add((a, b))
            edges.add((b, a))

    init: list[str] = []
    for agent in drones + trucks:
        init.append(f"(at_ {agent} {rng.choice(all_locations)})")
    for t in range(3):
        for item in items[t]:
            init.append(f"(at_ {item} {rng.choice(all_locations)})")
    for a, b in sorted(edges):
        init.append(f"(path {a} {b})")

    ws_choices_i3 = [rng.choice(workshops) for _ in goal_items_i3]
    dest_choices_i3 = [rng.choice(all_locations) for _ in goal_items_i3]
    dest_choices_i4 = [rng.choice(all_locations) for _ in goal_items_i4]

    goals = []
    for gi, dest in zip(goal_items_i3, dest_choices_i3, strict=False):
        goals.append(f"(at_ {gi} {dest})")
    for gi, dest in zip(goal_items_i4, dest_choices_i4, strict=False):
        goals.append(f"(at_ {gi} {dest})")

    obj_lines = [
        f"    {' '.join(locs)} - location",
        f"    {' '.join(workshops)} - workshop",
    ]
    if drones:
        obj_lines.append(f"    {' '.join(drones)} - drone")
    if trucks:
        obj_lines.append(f"    {' '.join(trucks)} - truck")
    for t in range(3):
        obj_lines.append(f"    {' '.join(items[t])} - item{t}")
    if goal_items_i3:
        obj_lines.append(f"    {' '.join(goal_items_i3)} - item3")
    if goal_items_i4:
        obj_lines.append(f"    {' '.join(goal_items_i4)} - item4")

    init_str = "\n    ".join(init)
    goal_str = "\n    ".join(goals)
    objects_str = "\n".join(obj_lines)
    _ = ws_choices_i3

    return (
        f"(define (problem generated-task-{seed})\n"
        f"  (:domain full-domain)\n"
        f"  (:objects\n{objects_str}\n  )\n"
        f"  (:init\n    {init_str}\n  )\n"
        f"  (:goal (and\n    {goal_str}\n  ))\n"
        f")\n"
    )
