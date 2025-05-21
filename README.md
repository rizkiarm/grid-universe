# Grid Universe

Grid Universe is a flexible gridworld environment built on a pure Entity-Component-System (ECS) architecture. It offers fully customizable movement and objective rules, along with advanced mechanics such as power-ups, keys and doors, moving objects, enemies, portals, and more. The platform is compatible with Gymnasium for reinforcement learning (RL) training, and includes a Streamlit web app featuring a comprehensive ECS state inspector.

Designed from the ground up, Grid Universe serves as an ideal environment for research and teaching in reinforcement learning, puzzle games, and agent-based AI.

## Key Features

- **Modern ECS Architecture:** Built with native Python dataclasses and immutable data structures via [`pyrsistent`](https://github.com/tobgu/pyrsistent) for robust, maintainable code.
- **Composable Components:** Includes agents, pushable/moving objects, portals, keys/doors, power-up statuses, pathfinding, and more.
- **Extensible Movement Rules:** Supports classic, wrap-around, slippery, windy, gravity-based, and other customizable movement mechanics.
- **Flexible Objectives:** Multiple built-in and extendable objectives such as reaching exits, collecting items, pushing boxes, unlocking doors, and more.
- **AI Capabilities:** Pathfinding using straight-line seeking or A* search; supports directional movement logic.
- **Multi-Agent Ready:** Core ECS design supports multiple agents, with single-agent support in UI and RL wrappers by default.
- **Powerful Level Generation:** Flexible, scriptable level generation (see `levels/maze.py`) and support for fully custom levels.
- **Reinforcement Learning Integration:** Native Gymnasium environment (`gym_env.py`) for seamless RL experimentation.
- **Interactive Streamlit App:** Highly customizable web app for environment exploration and visualization.
- **Tile-Based Rendering:** Efficient visualizations using [`Pillow`](https://pillow.readthedocs.io/en/stable/) for rendering environments.
- **Comprehensive Testing:** Ensured code reliability with strong test coverage using [`pytest`](https://docs.pytest.org/).

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [Testing](#testing)
- [Extending](#extending)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

**Requirements:**
- Python 3.11+
- [pyrsistent](https://github.com/tobgu/pyrsistent)
- [Pillow](https://pillow.readthedocs.io/en/stable/)

**Extra Dependencies:**
- [gymnasium](https://github.com/Farama-Foundation/Gymnasium)
- [numpy](https://numpy.org)
- [Streamlit](https://streamlit.io)

Install dependencies:

```
pip install -e .
```

Install with extra dependencies:

```
pip install -e .[gym] # Gymnasium API
pip install -e .[app] # Streamlit App
pip install -e .[dev] # Development
```

### Devcontainer

The project includes a `.devcontainer` directory supporting [Dev Containers](https://containers.dev).
- `.devcontainer/devcontainer.json`: Specifies a ready-to-use Python environment, ports, and setup commands.
- `.devcontainer/setup.sh`: Initializes a virtual environment, installs dependencies, and ensures a consistent shell environment.

---

## Quick Start

### Streamlit App

The `app/main.py` file provides an interactive web interface for Grid Universe using [Streamlit](https://streamlit.io/).

**Features:**
- **Game:** Play using keyboard or UI, see agent HP, inventory, powerup status, and receive live feedback.
- **Config:** Customize level generation, maze size, objects, movement/objective rules, powerups, items, etc.
- **State:** Inspect the full, real-time ECS state in JSON form (for debugging, RL, and teaching).

To run the web app locally:
```
streamlit run app/main.py
```

Alternatively, you can access the hosted version at [grid-universe.streamlit.app](https://grid-universe.streamlit.app/)

### Functional API

Create a random env, interact, and render using the Functional API:

```
from grid_universe.step import step
from grid_universe.actions import Action
from grid_universe.renderer.texture import render
from grid_universe.levels.maze import generate

# Create the initial state which defines the env
state = generate(width=7, height=7)

# Take a step (move up)
next_state = step(state, Action.UP)

# Render to PIL Image
image = render(next_state)
```

### Gymnasium API

Gymnasium API is a thin wrapper of the functional API.

Create a random env, interact, and render using the Gymnasium API:

```
from grid_universe.gym_env import GridUniverseEnv
from grid_universe.actions import GymAction

# Create the env
env = GridUniverseEnv(render_mode="texture", width=7, height=7)
obs, info = env.reset()

# Take a step (move up)
_, reward, terminated, truncated, info = env.step(GymAction.UP)

# Render with window
env.render(mode="human")

# Render to PIL Image
img = env.render()
```

The RL env returns a dict:

- `obs["image"]`: RGBA numpy array (height × width × 4) of the current grid.
- `obs["agent"]`: Feature vector (health, max_health, score, key counts, active powerups, etc.).

---

## Project Structure
```
app/
    main.py            # Streamlit App
    ...
grid_universe/
    actions.py         # Action types (Move, PickUp, UseKey, etc.)
    components/        # ECS component classes (Agent, Position, Wall, etc.)
    entity.py          # EntityID generator
    gym_env.py         # RL environment API (gymnasium)
    levels/            # Level generators
    moves.py           # Movement rules and variants
    objectives.py      # Win conditions
    renderer/          # Texture/tile rendering (Pillow)
    state.py           # Immutable State dataclass (ECS world state)
    step.py            # Main ECS step/reducer logic
    systems/           # ECS systems: movement, enemy, portal, hazard, etc.
    types.py           # Core tags, RenderType enums, typing
    utils/             # Utility functions (inventory, powerups, etc.)
tests/
    ...                # pytest-based unit and integration tests
assets/images/
        ...            # image assets
```
### Entity-Component-System

- **Entity**: An integer ID (see `entity.py`)
- **Component**: Data-only classes (see `components/`)
- **System**: Pure functions processing State (see `systems/`)

---

## Core Concepts

### Actions and Movement

**Supported Actions:**
Move (Up, Down, Left, Right), PickUp, UseKey, Wait

**Movement Rules:**
- **default:** Classic 4-way movement
- **wrap:** Wrap-around grid
- **slippery:** Slides continuously until blocked
- **windy:** Random wind gusts alter movement
- **gravity:** Entities fall until blocked

*See `moves.py` for implementation details.*

### Objectives

**Win Conditions:**
- **default:** Collect required items and reach the exit
- **exit:** Go to the exit
- **collect:** Collect all required items
- **push:** Push all boxes to exits
- **unlock:** Unlock all doors

*See `objectives.py` for details.*

### Objects & Interactions

- Agents, Boxes (pushable & moving), Walls, Keys/Doors, Exits
- Enemies and Hazards (damage, lethal, etc.)
- **PowerUps:** Phasing, Immunity, Faster Movement Speed (with usage or time limits)
- **Portals:** Teleport entities
- Rewardable items, Required items

### Level Generation

- Customizable, procedurally-generated mazes
  *Example: `levels/maze.py`*
- Configure number of items, keys/doors, hazards, enemies, and more

### Rendering

- Tile-based rendering using Pillow
  *See `renderer/texture.py`*
- Layered rendering: background, main, corner icons per tile
- Easily swap out tile sets by changing the texture map

---

## Extending

- Add new Components: define in `components/`
- Add new Systems: put functions in `systems/`
- Add new movement rules: add to `moves.py` and register in `MOVE_FN_REGISTRY`
- Add new objectives: add to `objectives.py` and register in `OBJECTIVE_FN_REGISTRY`
- Add new tile graphics: extend or override `TEXTURE_MAP` in `renderer/texture.py`

---

## Testing

Tests use `pytest`. To run all tests:
```
pytest
```
- Includes coverage of systems, integration, unit actions, and edge cases.

---

## Contributing

Contributions are welcome!

To contribute:
1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Add tests for your changes.
4. Run the test suite and ensure all tests pass.
5. Submit a pull request and describe your changes.

### Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for all code formatting, linting, and import sorting.

Before submitting a pull request, please run:
```
pytest
ruff format .
ruff check . --fix
```

---

## License

This project is licensed under the [MIT License](LICENSE).
