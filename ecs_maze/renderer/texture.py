from typing import Callable, Dict, Optional, Tuple, List
from PIL import Image
from ecs_maze.state import State
from ecs_maze.utils.render import eid_to_render_type
from ecs_maze.types import EntityID, RenderType

TexLookupFn = Callable[[RenderType, int], Optional[Image.Image]]
TextureMap = Dict[RenderType, Optional[str]]

# --- Texture Map using RenderType as key (not string) ---
# ---    Note: this is sorted by rendering priority    ---
TEXTURE_MAP: TextureMap = {
    RenderType.AGENT: "animated_characters/male_adventurer/maleAdventurer_idle.png",
    RenderType.DEAD: "animated_characters/zombie/zombie_fall.png",
    RenderType.REWARDABLE_ITEM: "items/coinGold.png",
    RenderType.REQUIRED_ITEM: "items/gold_1.png",
    RenderType.ITEM: "items/coinBronze.png",
    RenderType.BOX: "tiles/boxCrate.png",
    RenderType.MOVING_BOX: "tiles/boxCrate_double.png",
    RenderType.ENEMY: "enemies/slimeBlue.png",
    RenderType.MOVING_ENEMY: "enemies/slimeBlue_move.png",
    RenderType.KEY: "items/keyRed.png",
    RenderType.PORTAL: "items/star.png",
    RenderType.LOCKED: "tiles/lockRed.png",
    RenderType.DOOR: "tiles/doorClosed_mid.png",
    RenderType.POWERUP_GHOST: "items/gemBlue.png",
    RenderType.POWERUP_SHIELD: "items/gemGreen.png",
    RenderType.POWERUP_HAZARD_IMMUNITY: "items/gemRed.png",
    RenderType.POWERUP_DOUBLE_SPEED: "items/gemYellow.png",
    RenderType.HAZARD_SPIKE: "tiles/spikes.png",
    RenderType.HAZARD_LAVA: "tiles/lava.png",
    RenderType.EXIT: "tiles/signExit.png",
    RenderType.WALL: "tiles/brickBrown.png",
    RenderType.FLOOR: "tiles/brickGrey.png",
}

# --- Icon priorities as tuples of RenderType ---
BACKGROUND_PRIORITY: Tuple[RenderType, ...] = (
    RenderType.HAZARD_LAVA,
    RenderType.WALL,
    RenderType.FLOOR,
)
MAIN_PRIORITY: Tuple[RenderType, ...] = tuple(TEXTURE_MAP.keys())
CORNER_PRIORITY: Tuple[RenderType, ...] = (
    RenderType.KEY,
    RenderType.REWARDABLE_ITEM,
    RenderType.REQUIRED_ITEM,
    RenderType.POWERUP_GHOST,
    RenderType.POWERUP_SHIELD,
    RenderType.POWERUP_HAZARD_IMMUNITY,
    RenderType.POWERUP_DOUBLE_SPEED,
    RenderType.PORTAL,
    RenderType.EXIT,
)


def load_texture(path: str, size: int) -> Optional[Image.Image]:
    try:
        return Image.open(path).convert("RGBA").resize((size, size))
    except Exception:
        return None


def get_cell_render_types(state: State, eids: List[int]) -> List[RenderType]:
    """For all eids at a cell, return a list of RenderType enums for prioritized rendering."""
    return [eid_to_render_type(state, eid) for eid in eids]


def choose_background_icon(types_present: List[RenderType]) -> RenderType:
    for candidate in BACKGROUND_PRIORITY:
        if candidate in types_present:
            return candidate
    raise ValueError(f"No matching background icon: {types_present}")


def choose_main_icon(types_present: List[RenderType]) -> RenderType:
    for candidate in MAIN_PRIORITY:
        if candidate in types_present:
            return candidate
    raise ValueError(f"No matching main icon: {types_present}")


def choose_corner_icons(
    types_present: List[RenderType], main_icon: RenderType
) -> List[RenderType]:
    found: List[RenderType] = []
    for candidate in CORNER_PRIORITY:
        for tp in types_present:
            if tp == candidate and tp != main_icon and tp not in found:
                found.append(tp)
        if len(found) == 4:
            break
    return found


def render(
    state: State,
    cell_size: int = 32,
    subicon_size: int = 20,
    texture_map: Optional[TextureMap] = None,
    asset_root: str = "assets/images",
    tex_lookup_fn: Optional[TexLookupFn] = None,
) -> Image.Image:
    """
    Renders ECS state as a PIL Image, with prioritized center and up to 4 corners per tile.
    """
    if texture_map is None:
        texture_map = TEXTURE_MAP
    width, height = state.width, state.height
    img = Image.new(
        "RGBA", (width * cell_size, height * cell_size), (128, 128, 128, 255)
    )
    cache: Dict[Tuple[str, int], Optional[Image.Image]] = {}

    def default_get_tex(rtype: RenderType, size: int) -> Optional[Image.Image]:
        path = texture_map.get(rtype)
        if not path:
            return None
        key = (path, size)
        if key not in cache:
            cache[key] = load_texture(f"{asset_root}/{path}", size)
        return cache[key]

    tex_lookup = tex_lookup_fn or default_get_tex

    grid_entities: Dict[Tuple[int, int], List[EntityID]] = {}
    for eid, pos in state.position.items():
        grid_entities.setdefault((pos.x, pos.y), []).append(eid)

    for (x, y), eids in grid_entities.items():
        x0, y0 = x * cell_size, y * cell_size
        types_present = get_cell_render_types(state, eids)

        bg_type = choose_background_icon(types_present)
        main_icon = choose_main_icon(types_present)
        corner_icons = choose_corner_icons(types_present, main_icon)

        # Background
        bg_tex = tex_lookup(bg_type, cell_size)
        if bg_tex:
            img.alpha_composite(bg_tex, (x0, y0))
        # Render "other" objects that are on this cell but not main/corner/bg
        for rtype in (
            set(types_present)
            - set([main_icon] + corner_icons)
            - set(BACKGROUND_PRIORITY)
        ):
            tex = tex_lookup(rtype, cell_size)
            if tex:
                img.alpha_composite(tex, (x0, y0))
        # Main icon
        main_tex = tex_lookup(main_icon, cell_size)
        if main_tex:
            img.alpha_composite(main_tex, (x0, y0))
        # Corners
        for idx, icon_type in enumerate(corner_icons[:4]):
            dx = x0 + (cell_size - subicon_size if idx % 2 == 1 else 0)
            dy = y0 + (cell_size - subicon_size if idx // 2 == 1 else 0)
            tex = tex_lookup(icon_type, subicon_size)
            if tex:
                img.alpha_composite(tex, (dx, dy))

    return img


class TextureRenderer:
    cell_size: int
    subicon_size: int
    texture_map: TextureMap
    asset_root: str
    tex_lookup_fn: Optional[TexLookupFn]

    def __init__(
        self,
        cell_size: int = 32,
        subicon_size: int = 20,
        texture_map: Optional[TextureMap] = None,
        asset_root: str = "assets/images",
        tex_lookup_fn: Optional[TexLookupFn] = None,
    ):
        self.cell_size = cell_size
        self.subicon_size = subicon_size
        self.texture_map = texture_map or TEXTURE_MAP
        self.asset_root = asset_root
        self.tex_lookup_fn = tex_lookup_fn

    def render(self, state: State) -> Image.Image:
        return render(
            state,
            cell_size=self.cell_size,
            subicon_size=self.subicon_size,
            texture_map=self.texture_map,
            asset_root=self.asset_root,
            tex_lookup_fn=self.tex_lookup_fn,
        )
