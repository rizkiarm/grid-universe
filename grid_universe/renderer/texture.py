from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image
from pyrsistent import pmap

from grid_universe.components.properties.appearance import Appearance, AppearanceName
from grid_universe.state import State
from grid_universe.types import EntityID

DEFAULT_RESOLUTION = 640
DEFAULT_SUBICON_PERCENT = 0.4

ObjectAsset = tuple[AppearanceName, tuple[str, ...]]


@dataclass(frozen=True)
class ObjectRendering:
    appearance: Appearance
    properties: tuple[str, ...]

    def asset(self) -> ObjectAsset:
        return (self.appearance.name, self.properties)


ObjectName = str
ObjectProperty = str
ObjectPropertiesTextureMap = dict[ObjectName, dict[tuple[ObjectProperty, ...], str]]

TexLookupFn = Callable[[ObjectAsset, int], Image.Image]
TextureMap = dict[ObjectAsset, str]


TEXTURE_MAP: TextureMap = {
    (
        AppearanceName.HUMAN,
        (),
    ): "animated_characters/male_adventurer/maleAdventurer_idle.png",
    (
        AppearanceName.HUMAN,
        ("dead",),
    ): "animated_characters/zombie/zombie_fall.png",
    (AppearanceName.COIN, ()): "items/coinGold.png",
    (AppearanceName.CORE, ("required",)): "items/gold_1.png",
    (AppearanceName.BOX, ()): "tiles/boxCrate.png",
    (AppearanceName.BOX, ("moving",)): "tiles/boxCrate_double.png",
    (AppearanceName.MONSTER, ()): "enemies/slimeBlue.png",
    (AppearanceName.MONSTER, ("moving",)): "enemies/slimeBlue_move.png",
    (AppearanceName.KEY, ()): "items/keyRed.png",
    (AppearanceName.PORTAL, ()): "items/star.png",
    (AppearanceName.DOOR, ("locked",)): "tiles/lockRed.png",
    (AppearanceName.DOOR, ()): "tiles/doorClosed_mid.png",
    (AppearanceName.SHIELD, ("immunity",)): "items/gemBlue.png",
    (AppearanceName.GHOST, ("phasing",)): "items/gemGreen.png",
    (AppearanceName.BOOTS, ("speed",)): "items/gemRed.png",
    (AppearanceName.SPIKE, ()): "tiles/spikes.png",
    (AppearanceName.LAVA, ()): "tiles/lava.png",
    (AppearanceName.EXIT, ()): "tiles/signExit.png",
    (AppearanceName.WALL, ()): "tiles/brickBrown.png",
    (AppearanceName.FLOOR, ()): "tiles/brickGrey.png",
}


def load_texture(path: str, size: int) -> Image.Image | None:
    try:
        return Image.open(path).convert("RGBA").resize((size, size))
    except Exception:
        return None


def get_object_renderings(state: State, eids: list[EntityID]) -> list[ObjectRendering]:
    renderings: list[ObjectRendering] = []
    default_appearance: Appearance = Appearance(name=AppearanceName.NONE)
    for eid in eids:
        appearance = state.appearance.get(eid, default_appearance)
        properties = tuple(
            [
                component
                for component, value in state.__dict__.items()
                if isinstance(value, type(pmap())) and eid in value
            ],
        )
        renderings.append(
            ObjectRendering(
                appearance=appearance,
                properties=properties,
            ),
        )
    return renderings


def choose_background(object_renderings: list[ObjectRendering]) -> ObjectRendering:
    items = [
        object_rendering
        for object_rendering in object_renderings
        if object_rendering.appearance.background
    ]
    if len(items) == 0:
        msg = f"No matching background: {object_renderings}"
        raise ValueError(msg)
    return sorted(items, key=lambda x: x.appearance.priority)[
        -1
    ]  # take the lowest priority


def choose_main(object_renderings: list[ObjectRendering]) -> ObjectRendering | None:
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
    object_renderings: list[ObjectRendering], main: ObjectRendering | None,
) -> list[ObjectRendering]:
    items = {

            object_rendering
            for object_rendering in object_renderings
            if object_rendering.appearance.icon
        } - {main}
    return sorted(items, key=lambda x: x.appearance.priority)[
        :4
    ]  # take the highest priority


def get_path(
    object_asset: ObjectAsset, texture_hmap: ObjectPropertiesTextureMap,
) -> str:
    object_name, object_properties = object_asset
    if object_name not in texture_hmap:
        msg = f"Object rendering {object_asset} is not found in texture map"
        raise ValueError(msg)
    nearest_object_properties = sorted(
        texture_hmap[object_name].keys(),
        key=lambda x: len(set(x).intersection(object_properties))
        - len(set(x) - set(object_properties)),
        reverse=True,
    )[0]
    return texture_hmap[object_name][nearest_object_properties]


def render(
    state: State,
    resolution: int = DEFAULT_RESOLUTION,
    subicon_percent: float = DEFAULT_SUBICON_PERCENT,
    texture_map: TextureMap | None = None,
    asset_root: str = "assets/images",
    tex_lookup_fn: TexLookupFn | None = None,
    cache: dict[tuple[str, int], Image.Image | None] | None = None,
) -> Image.Image:
    """Renders ECS state as a PIL Image, with prioritized center and up to 4 corners per tile."""
    if cache is None:
        cache = {}
    cell_size: int = resolution // state.width
    subicon_size: int = int(cell_size * subicon_percent)

    if texture_map is None:
        texture_map = TEXTURE_MAP

    texture_hmap: ObjectPropertiesTextureMap = defaultdict(dict)
    for (obj_name, obj_properties), value in texture_map.items():
        texture_hmap[obj_name][tuple(obj_properties)] = value

    width, height = state.width, state.height
    img = Image.new(
        "RGBA", (width * cell_size, height * cell_size), (128, 128, 128, 255),
    )

    def default_get_tex(object_asset: ObjectAsset, size: int) -> Image.Image | None:
        path = get_path(object_asset, texture_hmap)
        if not path:
            return None
        key = (path, size)
        if key not in cache:
            cache[key] = load_texture(f"{asset_root}/{path}", size)
        return cache[key]

    tex_lookup = tex_lookup_fn or default_get_tex

    grid_entities: dict[tuple[int, int], list[EntityID]] = {}
    for eid, pos in state.position.items():
        grid_entities.setdefault((pos.x, pos.y), []).append(eid)

    for (x, y), eids in grid_entities.items():
        x0, y0 = x * cell_size, y * cell_size

        object_renderings = get_object_renderings(state, eids)

        background = choose_background(object_renderings)
        main = choose_main(object_renderings)
        corner_icons = choose_corner_icons(object_renderings, main)
        others = list(
            set(object_renderings) - {main, *corner_icons, background},
        )

        primary_renderings: list[ObjectRendering] = (
            [background] + others + ([main] if main is not None else [])
        )

        for object_rendering in primary_renderings:
            object_tex = tex_lookup(object_rendering.asset(), cell_size)
            if object_tex:
                img.alpha_composite(object_tex, (x0, y0))

        for idx, corner_icon in enumerate(corner_icons[:4]):
            dx = x0 + (cell_size - subicon_size if idx % 2 == 1 else 0)
            dy = y0 + (cell_size - subicon_size if idx // 2 == 1 else 0)
            tex = tex_lookup(corner_icon.asset(), subicon_size)
            if tex:
                img.alpha_composite(tex, (dx, dy))

    return img


class TextureRenderer:
    resolution: int
    subicon_percent: float
    texture_map: TextureMap
    asset_root: str
    tex_lookup_fn: TexLookupFn | None

    def __init__(
        self,
        resolution: int = DEFAULT_RESOLUTION,
        subicon_percent: float = DEFAULT_SUBICON_PERCENT,
        texture_map: TextureMap | None = None,
        asset_root: str = "assets/images",
        tex_lookup_fn: TexLookupFn | None = None,
    ) -> None:
        self.resolution = resolution
        self.subicon_percent = subicon_percent
        self.texture_map = texture_map or TEXTURE_MAP
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
