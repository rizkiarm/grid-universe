from typing import Any, Mapping, Set
from grid_universe.state import State
from grid_universe.components import PowerUp, Hazard
from grid_universe.types import EntityID, Tag, RenderType

# Map PowerUp type names to Tag
POWERUP_TAG_MAP = {
    "GHOST": Tag.POWERUP_GHOST,
    "SHIELD": Tag.POWERUP_SHIELD,
    "HAZARD_IMMUNITY": Tag.POWERUP_HAZARD_IMMUNITY,
    "DOUBLE_SPEED": Tag.POWERUP_DOUBLE_SPEED,
}
HAZARD_TAG_MAP = {
    "LAVA": Tag.HAZARD_LAVA,
    "SPIKE": Tag.HAZARD_SPIKE,
}

# Map sets of tags to RenderType, from most to least specific
TAG_COMBO_TO_RENDER_TYPE = [
    ((Tag.AGENT, Tag.DEAD), RenderType.DEAD),
    ((Tag.ENEMY, Tag.MOVING), RenderType.MOVING_ENEMY),
    ((Tag.BOX, Tag.MOVING), RenderType.MOVING_BOX),
    ((Tag.ITEM, Tag.REQUIRED), RenderType.REQUIRED_ITEM),
    ((Tag.ITEM, Tag.REWARDABLE), RenderType.REWARDABLE_ITEM),
    ((Tag.AGENT,), RenderType.AGENT),
    ((Tag.ENEMY,), RenderType.ENEMY),
    ((Tag.BOX,), RenderType.BOX),
    ((Tag.PUSHABLE,), RenderType.BOX),
    ((Tag.PORTAL,), RenderType.PORTAL),
    ((Tag.LOCKED,), RenderType.LOCKED),
    ((Tag.DOOR,), RenderType.DOOR),
    ((Tag.KEY,), RenderType.KEY),
    ((Tag.ITEM,), RenderType.ITEM),
    ((Tag.POWERUP_GHOST,), RenderType.POWERUP_GHOST),
    ((Tag.POWERUP_SHIELD,), RenderType.POWERUP_SHIELD),
    ((Tag.POWERUP_HAZARD_IMMUNITY,), RenderType.POWERUP_HAZARD_IMMUNITY),
    ((Tag.POWERUP_DOUBLE_SPEED,), RenderType.POWERUP_DOUBLE_SPEED),
    ((Tag.HAZARD_LAVA,), RenderType.HAZARD_LAVA),
    ((Tag.HAZARD_SPIKE,), RenderType.HAZARD_SPIKE),
    ((Tag.EXIT,), RenderType.EXIT),
    ((Tag.WALL,), RenderType.WALL),
    ((Tag.FLOOR,), RenderType.FLOOR),
]


def entity_tags(state: State, eid: EntityID) -> Set[Tag]:
    """
    Returns a set of Tag enums describing the entity's components and their types.
    """
    tags: Set[Tag] = set()
    # Map simple component stores to tags
    tag_map: list[tuple[Mapping[int, Any], Tag]] = [
        (state.agent, Tag.AGENT),
        (state.enemy, Tag.ENEMY),
        (state.box, Tag.BOX),
        (state.pushable, Tag.PUSHABLE),
        (state.moving, Tag.MOVING),
        (state.item, Tag.ITEM),
        (state.collectible, Tag.COLLECTIBLE),
        (state.required, Tag.REQUIRED),
        (state.rewardable, Tag.REWARDABLE),
        (state.key, Tag.KEY),
        (state.locked, Tag.LOCKED),
        (state.door, Tag.DOOR),
        (state.portal, Tag.PORTAL),
        (state.exit, Tag.EXIT),
        (state.wall, Tag.WALL),
        (state.dead, Tag.DEAD),
        (state.floor, Tag.FLOOR),
    ]
    for store, tag in tag_map:
        if eid in store:
            tags.add(tag)

    # PowerUp tags
    if eid in state.powerup:
        powerup: PowerUp = state.powerup[eid]
        pu_tag = POWERUP_TAG_MAP.get(powerup.type.name)
        if pu_tag:
            tags.add(pu_tag)
    # Hazard tags
    if eid in state.hazard:
        hazard: Hazard = state.hazard[eid]
        hz_tag = HAZARD_TAG_MAP.get(hazard.type.name)
        if hz_tag:
            tags.add(hz_tag)
    return tags


def tags_to_render_type(tags: Set[Tag]) -> RenderType:
    """
    Map a set of Tag enums to a RenderType enum.
    Fails fast if no RenderType matches.
    """
    for tag_combo, render_type in TAG_COMBO_TO_RENDER_TYPE:
        if all(tag in tags for tag in tag_combo):
            return render_type
    raise ValueError(f"No matching render type for tags: {tags}")


def eid_to_render_type(state: State, eid: EntityID) -> RenderType:
    """
    Given an entity ID and State, return the most appropriate RenderType.
    """
    tags = entity_tags(state, eid)
    return tags_to_render_type(tags)
