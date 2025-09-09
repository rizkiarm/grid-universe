
from pyrsistent import PMap

from grid_universe.components import Dead, Health
from grid_universe.types import EntityID


def apply_damage_and_check_death(
    health_dict: PMap[EntityID, Health],
    dead_dict: PMap[EntityID, Dead],
    eid: EntityID,
    damage: int,
    lethal: bool,
) -> tuple[PMap[EntityID, Health], PMap[EntityID, Dead]]:
    """Applies damage to the entity. If health drops to 0 or lethal is True, marks as Dead.
    Returns (updated_Health_pmap, updated_dead_pmap).
    """
    if eid in health_dict:
        hp = health_dict[eid]
        new_hp = max(0, hp.health - damage)
        health_dict = health_dict.set(
            eid, Health(health=new_hp, max_health=hp.max_health),
        )
        if new_hp == 0 or lethal:
            dead_dict = dead_dict.set(eid, Dead())
            health_dict = health_dict.set(
                eid, Health(health=0, max_health=hp.max_health),
            )
    elif lethal:
        dead_dict = dead_dict.set(eid, Dead())
    return health_dict, dead_dict
