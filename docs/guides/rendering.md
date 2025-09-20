# Rendering

This guide explains how the texture-based renderer turns a `State` into an image, how textures are selected and layered, how grouping and recoloring work, and how to customize assets and performance. It also includes examples and troubleshooting tips.

Contents

- Rendering model and layering
- Texture maps and asset resolution
- Grouping and deterministic recoloring
- Moving overlays (direction triangles)
- Performance and caching
- Customization patterns
- End-to-end examples
- Troubleshooting


## Rendering model and layering

The `TextureRenderer` draws a snapshot of the grid into a single RGBA image. Each cell is composed from objects in that cell, using `Appearance` flags and `priority` to decide draw order.

- Per cell, objects are split into functional roles by their `Appearance`:

    - Background: objects with `appearance.background = True`. Exactly one is chosen (the background “tile”).

    - Main: the primary non-background object.

    - Corner icons: objects with `appearance.icon = True` (up to four), drawn as small overlays in the corners.

    - Others: any remaining non-background, non-icon objects (drawn between background and main).

- Selection rules:

    - Background: from all background items, pick the one with the lowest priority after sorting descending (i.e., visually most “behind”; defaults often are floor `priority=10` and wall `priority=9`).

    - Main: among non-backgrounds, pick the highest priority (lowest numeric value).

    - Corner icons: up to 4 highest-priority `icon=True` objects.

    - Others: all remaining non-background, non-icon, non-main items.

- Composition order in a cell:

    - Draw background, then others, then main.

    - Draw up to 4 corner icons scaled by `subicon_percent` and positioned to corners.

- Object properties influence asset lookup:

    - Every entity’s `AppearanceName` and the set of component “properties” (e.g., `"pushable"`, `"pathfinding"`, `"dead"`, `"locked"`, `"required"`, etc.) are used to find the best-matching texture from a texture map (see next section).


## Texture maps and asset resolution

The renderer maps `(AppearanceName, properties)` → a file path or a directory under `asset_root`. If the path is a directory, one file is chosen deterministically (per `State.seed`) from that directory.

- Built-ins:

    - `DEFAULT_TEXTURE_MAP`: a Kenney-based mapping.

    - `FUTURAMA_TEXTURE_MAP`: an example alt set.

    - `TEXTURE_MAP_REGISTRY`: `{ "kenney": KENNEY_TEXTURE_MAP, "futurama": FUTURAMA_TEXTURE_MAP }`.

- The `texture_map` has entries like:

    - `(AppearanceName.BOX, ())`: `"kenney/tiles/boxCrate.png"`

    - `(AppearanceName.BOX, ("pushable",))`: `"kenney/tiles/boxCrate_double.png"`

    - `(AppearanceName.HUMAN, ("dead",))`: `"kenney/animated_characters/zombie/zombie_fall.png"`

- Best-match selection:

    - Given a requested asset key `(AppearanceName, properties_set)`, the renderer selects the path whose declared properties tuple maximizes overlap and minimizes extra unmatched properties.

    - This allows falling back to a generic “BOX” when the `("pushable",)` texture is not provided, and specializing when available.

- Asset root:

    - All texture paths are resolved relative to `asset_root` (default `"assets"`).

    - If the resolved path is a directory, the renderer lists image files (`.png`, `.jpg`, `.jpeg`, `.gif`), sorts them, and then chooses one via a deterministic RNG seeded from `state.seed` (one selection per object as rendered).

- Loading:

    - `load_texture` opens the image and resizes to the required square size (cell size or subicon size), returning RGBA.

    - If loading fails, the object is skipped (cell still renders other layers).


## Grouping and deterministic recoloring

Some objects are grouped to share a distinctive color (hue) while preserving texture tone. This provides instant visual grouping without hand-authoring tinted variants of assets.

- Group rules (`derive_groups`):

    - Keys/doors by `key_id`: `key_door_group_rule` maps both to `"key:<key_id>"`.

    - Paired portals: `portal_pair_group_rule` maps the pair to `` "portal:<A>-<B>" `` where `A < B` are the portal EIDs.

- Coloring:

    - `group_to_color(group_id)` deterministically maps a group string to an RGB color via `random.Random(group_id) → HSV → RGB`.

    - `apply_recolor_if_group(image, group)` recolors the texture to the group’s hue while preserving the per-pixel value (brightness/tone) and (by default) preserving saturation.

    - The recoloring operates on non-transparent pixels only (`alpha > 0`).

- Result:

    - All doors/keys of the same `key_id` share a hue.

    - The two portals in a pair share a hue.

- Custom groups:

    - You can extend the `derive_groups` rules to recolor other categories consistently across the map (e.g., all boxes of a certain puzzle, enemies in squads, etc.).


## Moving overlays (direction triangles)

Entities with a `Moving` component are annotated with a small set of white triangles pointing in the movement direction. The number of triangles equals the entity’s `Moving.speed`, centered and spaced along the pointing axis.

- Behavior:

    - If an object has `move_dir = (dx, dy)` and `move_speed > 0`, `draw_direction_triangles_on_image` overlays triangles on a copy of the texture before compositing it into the grid.

    - Triangles are centered; the centroid arrangement is symmetric around the image center. The triangles are isosceles and sized relative to the cell size.

- Use:

    - Makes it visually obvious when/where movers are headed, helpful for debugging and gameplay feedback, especially with subtle textures.


## Performance and caching

Rendering an entire grid each step can be expensive if textures are reloaded and recolored repeatedly. The renderer uses a small, in-memory cache keyed by:

- `(asset_path, size, group, move_dir, move_speed)`

    - `asset_path`: full path to the image file used (after directory selection).

    - `size`: cell size or subicon size.

    - `group`: group identifier string or `None` (affects recoloring).

    - `move_dir`: movement direction vector (affects overlay).

    - `move_speed`: movement speed (affects overlay).

- Tips:

    - Reuse a single `TextureRenderer` instance across frames so it reuses the cache.

    - Keep `asset_root` consistent.

    - Prefer using the same resolution across frames for maximum cache hits.

    - If you introduce dynamic recoloring rules or moving overlays that change every frame, expect more cache misses; consider coarser rendering or fewer variants for performance-critical loops.


## Customization patterns

You have several knobs to adapt the renderer to your project:

- Use a different texture map:

    - Start from `DEFAULT_TEXTURE_MAP` and add or override entries.

    - Add directories for appearance variants; the renderer will pick one deterministically.

- Add new appearances or property-matched variants:

    - Map `(AppearanceName.SOMETHING, ("propA","propB"))` to a path.

    - Provide a fallback `(AppearanceName.SOMETHING, ())` so the mixer always finds something.

- Override the texture lookup function (advanced):

    - The `render()` function accepts a `tex_lookup_fn` that can replace the default path resolution/loading/recoloring/overlay logic.

    - Provide a function with signature `(ObjectRendering, size) -> PIL.Image | None` and pass it to `TextureRenderer(tex_lookup_fn=...)`.

- Control corner icon scaling:

    - `subicon_percent` controls the relative size of corner icons (default `0.4`).

- Derive different groupings or colors:

    - Extend `DEFAULT_GROUP_RULES` with more `GroupRule` functions.

    - Implement a different mapping in `group_to_color` if you want non-HSV-based palettes (e.g., fixed palette, colorblind-safe selections).

- Switch to a different registry preset:

    - `TEXTURE_MAP_REGISTRY["futurama"]` is included as an example of a radically different style.

    - You can register your own under a custom key for quick swapping.


## End-to-end examples

Basic rendering of a generated maze
```python
from grid_universe.examples.maze import generate
from grid_universe.renderer.texture import TextureRenderer

state = generate(width=9, height=9, seed=42)
renderer = TextureRenderer(resolution=640, asset_root="assets")
img = renderer.render(state)
img.save("maze_snapshot.png")
```

Use a custom texture map and smaller subicons
```python
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP
from grid_universe.components.properties import AppearanceName
from copy import deepcopy

custom_map = deepcopy(DEFAULT_TEXTURE_MAP)
# Override human dead pose and box texture
custom_map[(AppearanceName.HUMAN, tuple(["dead"]))] = "my_pack/hero_dead.png"
custom_map[(AppearanceName.BOX, tuple([]))] = "my_pack/box.png"

renderer = TextureRenderer(resolution=480, subicon_percent=0.3, texture_map=custom_map, asset_root="assets")
img = renderer.render(state)
img.save("custom_snapshot.png")
```

Pick a random variant from a directory deterministically per run
```python
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP
from grid_universe.components.properties import AppearanceName
from copy import deepcopy

variants = deepcopy(DEFAULT_TEXTURE_MAP)
# Suppose you have assets/skins/walls/ with multiple .png files;
# all will be candidates, chosen deterministically per state.seed.
variants[(AppearanceName.WALL, tuple([]))] = "skins/walls"

renderer = TextureRenderer(texture_map=variants, asset_root="assets")
img = renderer.render(state)
img.save("variant_walls.png")
```

Extend grouping to colorize boxes by pushability
```python
from grid_universe.renderer.texture import TextureRenderer, DEFAULT_TEXTURE_MAP, DEFAULT_GROUP_RULES
from grid_universe.renderer.texture import derive_groups  # if you make a local wrapper
from grid_universe.state import State
from grid_universe.types import EntityID

def box_group_rule(state: State, eid: EntityID) -> str | None:
    if eid in state.appearance and state.appearance[eid].name.name == "BOX":
        return "box:push" if eid in state.pushable else "box:static"
    return None

class BoxGroupingRenderer(TextureRenderer):
    def render(self, state: State):
        # Derive with custom ordering: keep default rules, then our box rule
        groups = derive_groups(state, rules=DEFAULT_GROUP_RULES + [box_group_rule])
        # Continue with normal rendering (groups are used internally by the default pipeline)
        return super().render(state)
```
Note: For a full override with custom group rules injected directly, you can copy `renderer.texture.render()` and replace the call to `derive_groups(...)` with your own rules list.


## Troubleshooting

- “Icons overlap or are too big.”

    - Adjust `subicon_percent` (e.g., `0.3`) to make corner icons smaller.

- “My object didn’t render.”

    - Ensure its `AppearanceName` exists in the texture map.

    - If your mapping points to a directory, confirm there are image files (`.png`/`.jpg`/`.jpeg`/`.gif`) and that filesystem permissions are OK.

    - Check that the path is relative to `asset_root` and that `asset_root` is correct.

- “Group coloring looks odd or too saturated.”

    - `apply_recolor_if_group` preserves tone (value), but you can adjust saturation behavior by modifying `recolor_image_keep_tone` parameters (`keep_saturation`, `saturation_mix`, `min_saturation`) if you expose or wrap them.

- “Performance is slow when rendering many frames.”

    - Reuse the same `TextureRenderer` instance to exploit the cache.

    - Avoid changing resolution between frames; that changes cache keys (`size`), causing misses.

    - Reduce the number of moving overlays (move-speed triangles) if they change frequently; overlays are part of the cache key.

    - Consider pre-baking recolored versions for large batches of frames, or simplifying group rules.

- “Textures look blurry.”

    - Images are resized to the cell size. If your base assets are much smaller than the cell, upscaling will blur. Use higher-resolution assets or increase grid resolution.

- “Random variant selection changes every run.”

    - Set `state.seed` in your `State` (via `Level` seed or generator seed). The directory selection uses `Random(state.seed)` for determinism.