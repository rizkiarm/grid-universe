from collections import defaultdict
import colorsys
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Optional, Tuple, List
from PIL import Image
from pyrsistent import pmap
from grid_universe.components.properties.appearance import Appearance, AppearanceName
from grid_universe.state import State
from grid_universe.types import EntityID
from grid_universe.utils.image import (
    draw_direction_triangles_on_image,
    recolor_image_keep_tone,
)
import os
import random


DEFAULT_RESOLUTION = 640
DEFAULT_SUBICON_PERCENT = 0.4
DEFAULT_ASSET_ROOT = "assets"

ObjectAsset = Tuple[AppearanceName, Tuple[str, ...]]


@dataclass(frozen=True)
class ObjectRendering:
    appearance: Appearance
    properties: Tuple[str, ...]
    group: Optional[str] = None
    move_dir: Optional[Tuple[int, int]] = None
    move_speed: int = 0

    def asset(self) -> ObjectAsset:
        return (self.appearance.name, self.properties)


ObjectName = str
ObjectProperty = str
ObjectPropertiesTextureMap = Dict[ObjectName, Dict[Tuple[ObjectProperty, ...], str]]

TexLookupFn = Callable[[ObjectRendering, int], Image.Image]
TextureMap = Dict[ObjectAsset, str]


KENNEY_TEXTURE_MAP: TextureMap = {
    (
        AppearanceName.HUMAN,
        tuple([]),
    ): "kenney/animated_characters/male_adventurer/maleAdventurer_idle.png",
    (
        AppearanceName.HUMAN,
        tuple(["dead"]),
    ): "kenney/animated_characters/zombie/zombie_fall.png",
    (AppearanceName.COIN, tuple([])): "kenney/items/coinGold.png",
    (AppearanceName.CORE, tuple(["required"])): "kenney/items/gold_1.png",
    (AppearanceName.BOX, tuple([])): "kenney/tiles/boxCrate.png",
    (AppearanceName.BOX, tuple(["pushable"])): "kenney/tiles/boxCrate_double.png",
    (AppearanceName.MONSTER, tuple([])): "kenney/enemies/slimeBlue.png",
    (
        AppearanceName.MONSTER,
        tuple(["pathfinding"]),
    ): "kenney/enemies/slimeBlue_move.png",
    (AppearanceName.KEY, tuple([])): "kenney/items/keyRed.png",
    (AppearanceName.PORTAL, tuple([])): "kenney/items/star.png",
    (AppearanceName.DOOR, tuple(["locked"])): "kenney/tiles/lockRed.png",
    (AppearanceName.DOOR, tuple([])): "kenney/tiles/doorClosed_mid.png",
    (AppearanceName.SHIELD, tuple(["immunity"])): "kenney/items/gemBlue.png",
    (AppearanceName.GHOST, tuple(["phasing"])): "kenney/items/gemGreen.png",
    (AppearanceName.BOOTS, tuple(["speed"])): "kenney/items/gemRed.png",
    (AppearanceName.SPIKE, tuple([])): "kenney/tiles/spikes.png",
    (AppearanceName.LAVA, tuple([])): "kenney/tiles/lava.png",
    (AppearanceName.EXIT, tuple([])): "kenney/tiles/signExit.png",
    (AppearanceName.WALL, tuple([])): "kenney/tiles/brickBrown.png",
    (AppearanceName.FLOOR, tuple([])): "kenney/tiles/brickGrey.png",
}

FUTURAMA_TEXTURE_MAP: TextureMap = {
    (
        AppearanceName.HUMAN,
        tuple([]),
    ): "futurama/character01",
    (
        AppearanceName.HUMAN,
        tuple(["dead"]),
    ): "futurama/character02",
    (AppearanceName.COIN, tuple([])): "futurama/character03",
    (AppearanceName.CORE, tuple(["required"])): "futurama/character04",
    (AppearanceName.BOX, tuple([])): "futurama/character06",
    (AppearanceName.BOX, tuple(["pushable"])): "futurama/character07",
    (AppearanceName.MONSTER, tuple([])): "futurama/character08",
    (AppearanceName.MONSTER, tuple(["pathfinding"])): "futurama/character09",
    (AppearanceName.KEY, tuple([])): "futurama/character10",
    (AppearanceName.PORTAL, tuple([])): "futurama/character11",
    (AppearanceName.DOOR, tuple(["locked"])): "futurama/character12",
    (AppearanceName.DOOR, tuple([])): "futurama/character13",
    (AppearanceName.SHIELD, tuple(["immunity"])): "futurama/character14",
    (AppearanceName.GHOST, tuple(["phasing"])): "futurama/character15",
    (AppearanceName.BOOTS, tuple(["speed"])): "futurama/character16",
    (AppearanceName.SPIKE, tuple([])): "futurama/character17",
    (AppearanceName.LAVA, tuple([])): "futurama/character18",
    (AppearanceName.EXIT, tuple([])): "futurama/character19",
    (AppearanceName.WALL, tuple([])): "futurama/character20",
    (AppearanceName.FLOOR, tuple([])): "futurama/blank.png",
}

DEFAULT_TEXTURE_MAP: TextureMap = KENNEY_TEXTURE_MAP

TEXTURE_MAP_REGISTRY: Dict[str, TextureMap] = {
    "kenney": KENNEY_TEXTURE_MAP,
    "futurama": FUTURAMA_TEXTURE_MAP,
}


# --- Grouping Rules ---

GroupRule = Callable[[State, EntityID], Optional[str]]


def key_door_group_rule(state: State, eid: EntityID) -> Optional[str]:
    if eid in state.key:
        return f"key:{state.key[eid].key_id}"
    if eid in state.locked:
        return f"key:{state.locked[eid].key_id}"
    return None


def portal_pair_group_rule(state: State, eid: EntityID) -> Optional[str]:
    if eid not in state.portal:
        return None
    pair = state.portal[eid].pair_entity
    a, b = (eid, pair) if eid <= pair else (pair, eid)
    return f"portal:{a}-{b}"


DEFAULT_GROUP_RULES: List[GroupRule] = [
    key_door_group_rule,
    portal_pair_group_rule,
]


def derive_groups(
    state: State, rules: List[GroupRule] = DEFAULT_GROUP_RULES
) -> Dict[EntityID, Optional[str]]:
    out: Dict[EntityID, Optional[str]] = {}
    for eid, _ in state.entity.items():
        group: Optional[str] = None
        for rule in rules:
            group = rule(state, eid)
            if group is not None:
                break
        out[eid] = group
    return out


@lru_cache(maxsize=2048)
def group_to_color(group_id: str) -> Tuple[int, int, int]:
    """
    Deterministically map a group string to an RGB color.
    """
    rng = random.Random(group_id)
    h = rng.random()
    s = 0.6 + 0.3 * rng.random()
    v = 0.7 + 0.25 * rng.random()
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def apply_recolor_if_group(
    tex: Image.Image,
    group: Optional[str],
) -> Image.Image:
    """
    Recolor wrapper that sets hue to the group's color while preserving tone.
    """
    if group is None:
        return tex
    color = group_to_color(group)
    return recolor_image_keep_tone(tex, color)


def load_texture(path: str, size: int) -> Optional[Image.Image]:
    try:
        return Image.open(path).convert("RGBA").resize((size, size))
    except Exception:
        return None


def get_object_renderings(
    state: State, eids: List[EntityID], groups: Dict[EntityID, Optional[str]]
) -> List[ObjectRendering]:
    renderings: List[ObjectRendering] = []
    default_appearance: Appearance = Appearance(name=AppearanceName.NONE)
    for eid in eids:
        appearance = state.appearance.get(eid, default_appearance)
        properties = tuple(
            [
                component
                for component, value in state.__dict__.items()
                if isinstance(value, type(pmap())) and eid in value
            ]
        )

        move_dir: Optional[Tuple[int, int]] = None
        move_speed: int = 0
        if eid in state.moving:
            m = state.moving[eid]
            if m.axis.name == "HORIZONTAL":
                move_dir = (1 if m.direction > 0 else -1, 0)
            else:
                move_dir = (0, 1 if m.direction > 0 else -1)
            move_speed = m.speed

        renderings.append(
            ObjectRendering(
                appearance=appearance,
                properties=properties,
                group=groups.get(eid),
                move_dir=move_dir,
                move_speed=move_speed,
            )
        )
    return renderings


def choose_background(object_renderings: List[ObjectRendering]) -> ObjectRendering:
    items = [
        object_rendering
        for object_rendering in object_renderings
        if object_rendering.appearance.background
    ]
    if len(items) == 0:
        raise ValueError(f"No matching background: {object_renderings}")
    return sorted(items, key=lambda x: x.appearance.priority)[
        -1
    ]  # take the lowest priority


def choose_main(object_renderings: List[ObjectRendering]) -> Optional[ObjectRendering]:
    items = [
        object_rendering
        for object_rendering in object_renderings
        if not object_rendering.appearance.background
    ]
    if len(items) == 0:
        return None
    return sorted(items, key=lambda x: x.appearance.priority)[
        0
    ]  # take the highest priority


def choose_corner_icons(
    object_renderings: List[ObjectRendering], main: Optional[ObjectRendering]
) -> List[ObjectRendering]:
    items = set(
        [
            object_rendering
            for object_rendering in object_renderings
            if object_rendering.appearance.icon
        ]
    ) - set([main])
    return sorted(items, key=lambda x: x.appearance.priority)[
        :4
    ]  # take the highest priority


def get_path(
    object_asset: ObjectAsset, texture_hmap: ObjectPropertiesTextureMap
) -> str:
    object_name, object_properties = object_asset
    if object_name not in texture_hmap:
        raise ValueError(f"Object rendering {object_asset} is not found in texture map")
    nearest_object_properties = sorted(
        texture_hmap[object_name].keys(),
        key=lambda x: len(set(x).intersection(object_properties))
        - len(set(x) - set(object_properties)),
        reverse=True,
    )[0]
    return texture_hmap[object_name][nearest_object_properties]


def select_texture_from_directory(
    dir: str,
    seed: Optional[int],
) -> Optional[str]:
    if not os.path.isdir(dir):
        return None

    try:
        entries = os.listdir(dir)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return None

    files = sorted(
        f for f in entries if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
    )
    if not files:
        return None

    rng = random.Random(seed)
    chosen = rng.choice(files)
    return os.path.join(dir, chosen)


def render(
    state: State,
    resolution: int = DEFAULT_RESOLUTION,
    subicon_percent: float = DEFAULT_SUBICON_PERCENT,
    texture_map: Optional[TextureMap] = None,
    asset_root: str = DEFAULT_ASSET_ROOT,
    tex_lookup_fn: Optional[TexLookupFn] = None,
    cache: Dict[
        Tuple[str, int, Optional[str], Optional[Tuple[int, int]], int],
        Optional[Image.Image],
    ] = {},
) -> Image.Image:
    """
    Renders ECS state as a PIL Image, with prioritized center and up to 4 corners per tile.
    """
    cell_size: int = resolution // state.width
    subicon_size: int = int(cell_size * subicon_percent)

    if texture_map is None:
        texture_map = DEFAULT_TEXTURE_MAP

    texture_hmap: ObjectPropertiesTextureMap = defaultdict(dict)
    for (obj_name, obj_properties), value in texture_map.items():
        texture_hmap[obj_name][tuple(obj_properties)] = value

    width, height = state.width, state.height
    img = Image.new(
        "RGBA", (width * cell_size, height * cell_size), (128, 128, 128, 255)
    )

    groups = derive_groups(state)

    def default_get_tex(
        object_rendering: ObjectRendering, size: int
    ) -> Optional[Image.Image]:
        path = get_path(object_rendering.asset(), texture_hmap)
        if not path:
            return None

        asset_path = f"{asset_root}/{path}"
        if os.path.isdir(asset_path):
            selected_asset_path = select_texture_from_directory(asset_path, state.seed)
            if selected_asset_path is None:
                return None
            asset_path = selected_asset_path

        key = (
            asset_path,
            size,
            object_rendering.group,
            object_rendering.move_dir,
            object_rendering.move_speed,
        )
        if key in cache:
            return cache[key]

        texture = load_texture(asset_path, size)
        if texture is None:
            return None

        texture = apply_recolor_if_group(texture, object_rendering.group)
        if (
            object_rendering.move_dir is not None
            and object_rendering.move_speed > 0
        ):
            dx, dy = object_rendering.move_dir
            texture = draw_direction_triangles_on_image(
                texture.copy(), size, dx, dy, object_rendering.move_speed
            )

        cache[key] = texture
        return texture

    tex_lookup = tex_lookup_fn or default_get_tex

    grid_entities: Dict[Tuple[int, int], List[EntityID]] = {}
    for eid, pos in state.position.items():
        grid_entities.setdefault((pos.x, pos.y), []).append(eid)

    for (x, y), eids in grid_entities.items():
        x0, y0 = x * cell_size, y * cell_size

        object_renderings = get_object_renderings(state, eids, groups)

        background = choose_background(object_renderings)
        main = choose_main(object_renderings)
        corner_icons = choose_corner_icons(object_renderings, main)
        others = list(
            set(object_renderings) - set([main] + corner_icons + [background])
        )

        primary_renderings: List[ObjectRendering] = (
            [background] + others + ([main] if main is not None else [])
        )

        for object_rendering in primary_renderings:
            object_tex = tex_lookup(object_rendering, cell_size)
            if object_tex:
                img.alpha_composite(object_tex, (x0, y0))

        for idx, corner_icon in enumerate(corner_icons[:4]):
            dx = x0 + (cell_size - subicon_size if idx % 2 == 1 else 0)
            dy = y0 + (cell_size - subicon_size if idx // 2 == 1 else 0)
            tex = tex_lookup(corner_icon, subicon_size)
            if tex:
                img.alpha_composite(tex, (dx, dy))

    return img


class TextureRenderer:
    resolution: int
    subicon_percent: float
    texture_map: TextureMap
    asset_root: str
    tex_lookup_fn: Optional[TexLookupFn]

    def __init__(
        self,
        resolution: int = DEFAULT_RESOLUTION,
        subicon_percent: float = DEFAULT_SUBICON_PERCENT,
        texture_map: Optional[TextureMap] = None,
        asset_root: str = DEFAULT_ASSET_ROOT,
        tex_lookup_fn: Optional[TexLookupFn] = None,
    ):
        self.resolution = resolution
        self.subicon_percent = subicon_percent
        self.texture_map = texture_map or DEFAULT_TEXTURE_MAP
        self.asset_root = asset_root
        self.tex_lookup_fn = tex_lookup_fn

    def render(self, state: State) -> Image.Image:
        return render(
            state,
            resolution=self.resolution,
            subicon_percent=self.subicon_percent,
            texture_map=self.texture_map,
            asset_root=self.asset_root,
            tex_lookup_fn=self.tex_lookup_fn,
        )
