from dataclasses import replace
from typing import Any

import pytest
from pyrsistent import pmap, pset

from grid_universe.actions import Action
from grid_universe.components import (
    Collectible,
    Damage,
    Health,
    Immunity,
    Inventory,
    LethalDamage,
    Position,
    Status,
    UsageLimit,
)
from grid_universe.entity import Entity
from grid_universe.objectives import default_objective_fn
from grid_universe.state import State
from grid_universe.step import step
from grid_universe.types import EntityID
from tests.test_utils import make_agent_state


def make_damage_state(
    *,
    agent_hp: int = 10,
    agent_pos: tuple[int, int] = (0, 0),
    damage_sources: list[tuple[int, int, int]] = [],
    lethal_sources: list[tuple[int, int]] = [],
    immunity_effect: bool = False,
    usage_limited_immunity: int = 0,
    agent_dead: bool = False,
    width: int = 5,
    height: int = 5,
    agent_id: EntityID = 1,
) -> tuple[State, EntityID, list[EntityID], list[EntityID]]:
    """Returns a state with one agent and any number of Damage and LethalDamage sources.
    Optionally adds immunity (permanent or usage-limited).
    Returns (state, agent_id, damage_ids, lethal_ids)
    """
    extra: dict[str, dict[EntityID, Any]] = {}
    pos_map: dict[EntityID, Position] = {}
    damage_ids: list[EntityID] = []
    lethal_ids: list[EntityID] = []

    # Damage sources
    for i, (x, y, amount) in enumerate(damage_sources):
        eid: EntityID = 100 + i
        pos_map[eid] = Position(x, y)
        if "damage" not in extra:
            extra["damage"] = {}
        extra["damage"][eid] = Damage(amount=amount)
        damage_ids.append(eid)

    # Lethal sources
    for i, (x, y) in enumerate(lethal_sources):
        eid: EntityID = 200 + i
        pos_map[eid] = Position(x, y)
        if "lethal_damage" not in extra:
            extra["lethal_damage"] = {}
        extra["lethal_damage"][eid] = LethalDamage()
        lethal_ids.append(eid)

    # Agent Health
    health: dict[EntityID, Health] = {
        agent_id: Health(health=agent_hp, max_health=agent_hp),
    }
    extra["health"] = health

    # Immunity effect
    status: dict[EntityID, Status] = {}
    immunity: dict[EntityID, Immunity] = {}
    usage_limit: dict[EntityID, UsageLimit] = {}
    if immunity_effect or usage_limited_immunity > 0:
        effect_id: EntityID = 999
        status[agent_id] = Status(effect_ids=pset([effect_id]))
        immunity[effect_id] = Immunity()
        if usage_limited_immunity > 0:
            usage_limit[effect_id] = UsageLimit(amount=usage_limited_immunity)
        extra["status"] = status
        extra["immunity"] = immunity
        if usage_limit:
            extra["usage_limit"] = usage_limit

    # Agent Dead
    if agent_dead:
        from grid_universe.components import Dead

        extra["dead"] = {agent_id: Dead()}

    # Positions
    pos_map[agent_id] = Position(*agent_pos)
    extra["position"] = pos_map

    # Compose state
    state, _agent_id = make_agent_state(
        agent_pos=agent_pos,
        move_fn=None,
        objective_fn=default_objective_fn,
        extra_components=extra,
        width=width,
        height=height,
        agent_dead=agent_dead,
        agent_id=agent_id,
    )
    return state, agent_id, damage_ids, lethal_ids


def move_agent_to(state: State, agent_id: EntityID, pos: tuple[int, int]) -> State:
    return replace(state, position=state.position.set(agent_id, Position(*pos)))


def agent_health(state: State, agent_id: EntityID) -> int:
    return state.health[agent_id].health if agent_id in state.health else -1


def agent_is_dead(state: State, agent_id: EntityID) -> bool:
    return agent_id in state.dead


def step_on_tile(state: State, agent_id: EntityID, action: Action) -> State:
    """Move agent in action using step, then Wait to apply damage if needed."""
    state2: State = step(state, action, agent_id=agent_id)
    # Optionally, call WaitAction to represent a turn passing if needed
    return state2


# --- TESTS ---


def test_agent_takes_damage() -> None:
    """Agent health decreases by damage amount."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(1, 0, 4)],
        agent_pos=(0, 0),
        agent_hp=10,
    )
    state2 = move_agent_to(state, agent_id, (1, 0))
    state3 = step(state2, Action.WAIT, agent_id=agent_id)
    assert agent_health(state3, agent_id) == 6


def test_agent_dies_from_lethal_damage() -> None:
    """Agent dies on lethal damage regardless of HP."""
    state, agent_id, _, lethal_ids = make_damage_state(
        lethal_sources=[(2, 0)],
        agent_hp=10,
        agent_pos=(2, 0),
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_is_dead(state2, agent_id)


def test_agent_takes_accumulated_damage_from_multiple_sources() -> None:
    """Agent takes sum of all damage sources at their tile."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 5), (0, 0, 2)],
        agent_pos=(0, 0),
        agent_hp=12,
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 5


def test_agent_damage_does_not_underflow() -> None:
    """Health never drops below zero."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 10)],
        agent_hp=6,
        agent_pos=(0, 0),
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 0


def test_no_damage_when_agent_not_on_source() -> None:
    """No damage when agent not on same position as any source."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(3, 3, 5)],
        agent_pos=(1, 1),
        agent_hp=7,
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 7


def test_dead_agent_is_not_damaged() -> None:
    """Dead agents are not affected by damage."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 3)],
        agent_pos=(0, 0),
        agent_hp=10,
        agent_dead=True,
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 10


def test_zero_damage_has_no_effect() -> None:
    """Zero damage source does not affect HP."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 0)],
        agent_pos=(0, 0),
        agent_hp=8,
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 8


def test_negative_damage_raises() -> None:
    """Negative damage raises ValueError."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, -4)],
        agent_pos=(0, 0),
        agent_hp=7,
    )
    with pytest.raises(ValueError):
        step(state, Action.WAIT, agent_id=agent_id)


def test_lethal_damage_precedence() -> None:
    """Lethal on same tile as damage: lethal takes precedence, agent dies."""
    state, agent_id, damage_ids, lethal_ids = make_damage_state(
        damage_sources=[(4, 4, 2)],
        lethal_sources=[(4, 4)],
        agent_pos=(4, 4),
        agent_hp=10,
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_is_dead(state2, agent_id)


def test_immunity_blocks_damage() -> None:
    """Agent with immunity effect takes no damage."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 6)],
        agent_pos=(0, 0),
        agent_hp=10,
        immunity_effect=True,
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 10


def test_usage_limited_immunity_blocks_then_expires() -> None:
    """Usage-limited immunity blocks once, then is gone."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 3)],
        agent_pos=(0, 0),
        agent_hp=10,
        usage_limited_immunity=1,
    )
    # Immunity blocks first time
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_health(state2, agent_id) == 10
    # Immunity is now expired; next tick, agent is damaged
    state3 = step(state2, Action.WAIT, agent_id=agent_id)
    assert agent_health(state3, agent_id) == 7


def test_multiple_agents_take_appropriate_damage() -> None:
    """Multiple agents: each takes damage only at their tile."""
    agent1: EntityID = 8
    agent2: EntityID = 9
    state1, _, _, _ = make_damage_state(
        agent_id=agent1,
        agent_pos=(0, 0),
        agent_hp=7,
    )
    state2, _, _, _ = make_damage_state(
        agent_id=agent2,
        agent_pos=(1, 1),
        agent_hp=11,
        damage_sources=[(0, 0, 2), (1, 1, 5)],  # need to create all damagers here
    )
    state: State = replace(
        state1,
        agent=state1.agent.update(state2.agent),
        health=state1.health.update(state2.health),
        position=state1.position.update(state2.position),
        damage=state1.damage.update(state2.damage),
        entity=state1.entity.update(state2.entity),
    )
    print(state.position)
    state = step(state, Action.WAIT, agent_id=agent1)
    state = step(state, Action.WAIT, agent_id=agent2)
    assert agent_health(state, agent1) == 3
    assert agent_health(state, agent2) == 1


def test_damage_and_collectible_both_apply() -> None:
    """Agent collects item and takes damage at same tile."""
    from grid_universe.systems.collectible import collectible_system

    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(1, 0, 3)],
        agent_pos=(1, 0),
        agent_hp=10,
    )
    # Place collectible at (1,0)
    collectible_id: EntityID = 333
    state = replace(
        state,
        entity=state.entity.set(collectible_id, Entity()),
        collectible=state.collectible.set(collectible_id, Collectible()),
        position=state.position.set(collectible_id, Position(1, 0)),
        inventory=state.inventory.set(agent_id, Inventory(pset())),
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    state3 = collectible_system(state2, agent_id)
    assert agent_health(state3, agent_id) == 7
    assert collectible_id in state3.inventory[agent_id].item_ids


def test_damage_and_exit_simultaneous_lose_overrides_win() -> None:
    """If agent stands on Exit and LethalDamage same step, agent loses (death over win)."""
    from grid_universe.components import Exit

    state, agent_id, _, _ = make_damage_state(
        lethal_sources=[(2, 2)],
        agent_pos=(2, 2),
        agent_hp=1,
    )
    exit_id: EntityID = 444
    state = replace(
        state,
        exit=state.exit.set(exit_id, Exit()),
        position=state.position.set(exit_id, Position(2, 2)),
    )
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_is_dead(state2, agent_id)
    assert not state2.win


def test_no_health_component_is_robust() -> None:
    """Agent without health component does not raise or crash."""
    state, agent_id, damage_ids, _ = make_damage_state(
        damage_sources=[(0, 0, 5)],
        agent_pos=(0, 0),
    )
    state = replace(state, health=pmap())  # Remove all health
    state2 = step(state, Action.WAIT, agent_id=agent_id)
    assert agent_id not in state2.health
