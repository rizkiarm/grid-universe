# ECS Maze

A modular, extensible, entity-component-system (ECS) gridworld environment for research & teaching in RL, puzzle games, and agent-based AI.

**Features:**
- ECS architecture using Python dataclasses and immutable data structures (`pyrsistent`)
- Rich object model: agents, pushable boxes, moving enemies, portals, keys/doors, powerups, hazards, and more
- Multiple movement models (classic, wrap-around, slippery, windy, gravity, etc.)
- Flexible level generation (`levels/generator.py`) and custom level support
- RL gymnasium environment (`gym_env.py`)
- High-quality tile-based rendering (`Pillow`)
- Good test coverage (`pytest`)

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [Web App & Devcontainer](#web-app--devcontainer)
- [Testing](#testing)
- [Extending](#extending)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

**Requirements:**
- Python 3.10+
- [pyrsistent](https://github.com/tobgu/pyrsistent)
- [Pillow](https://pillow.readthedocs.io/en/stable/)
- [gymnasium](https://github.com/Farama-Foundation/Gymnasium)

Install dependencies:

```
pip install -e .
```

Install with dev dependencies:

```
pip install -e .[dev]
```

### Devcontainer

The project includes a `.devcontainer` directory supporting [Dev Containers](https://containers.dev).
- **.devcontainer/devcontainer.json:** Specifies a ready-to-use Python environment, ports, and setup commands.
- **.devcontainer/setup.sh:** Initializes a virtual environment, installs dependencies, and ensures a consistent shell environment.

## Quick Start

Render and interact with a random maze in Python:

```
from ecs_maze.gym_env import ECSMazeEnv
import numpy as np

env = ECSMazeEnv(render_mode="texture", width=7, height=7)
obs, info = env.reset()
img = env.render()    # returns PIL.Image

# Take a step (move right)
_, reward, terminated, truncated, info = env.step(3)  # 3 = RIGHT

# Render with window:
env.render(mode="human")
```

## Project Structure
```
ecs_maze/
    actions.py         # Action types (Move, PickUp, UseKey, etc.)
    components/        # ECS component classes (Agent, Position, Wall, etc.)
    entity.py          # EntityID generator
    gym_env.py         # RL environment API (gymnasium)
    levels/            # Level and maze generators
    moves.py           # Movement rules and variants
    renderer/          # Texture/tile rendering (Pillow)
    state.py           # Immutable State dataclass (ECS world state)
    step.py            # Main ECS step/reducer logic
    systems/           # ECS systems: movement, enemy, portal, hazard, etc.
    types.py           # Core tags, RenderType enums, typing
    utils/             # Utility functions (maze gen, inventory, powerups, etc.)
tests/
    ...                # pytest-based unit and integration tests
```
### Entity-Component-System

- **Entity**: An integer ID (see `entity.py`)
- **Component**: Data-only classes (see `components/`)
- **System**: Pure functions processing State (see `systems/`)

## Core Concepts

### Actions and Movement

Supported actions: Move (with direction), PickUp, UseKey, Wait.

Multiple movement rules:
- **default**: classic 4-way
- **wrap**: wrap-around grid
- **slippery**: slides until blocked
- **windy**: random wind gusts affect moves
- **gravity**: falls until blocked
(see `moves.py`)

### Objects & Interactions

- Agents, Boxes (pushable & moving), Walls, Keys/Doors, Exits
- Enemies and Hazards (damage, lethal, etc.)
- PowerUps: Ghost, Shield, Hazard Immunity, Double Speed
- Portals: teleport entities
- Rewardable items, Required items

### Level Generation

Customizable procedurally-generated mazes:
- See `levels/generator.py`
- Control number of items, keys/doors, hazards, etc.

### Rendering

- Tile-based rendering using Pillow (see `renderer/texture.py`)
- Layered icons: background, main, corner icons per tile
- Easily swap out tile sets by setting texture map

---

## Streamlit Demo App (`app.py`)
The `app.py` file provides an interactive web interface for ECS Maze using [Streamlit](https://streamlit.io/).
**Features:**
- Play and visualize the maze directly in your browser.
- Configure maze size, objects, items, movement rules, powerups, hazards, and more via sidebar controls.
- Use keyboard or on-screen buttons for agent actions.
- View agent health, inventory, active powerups, and current reward.

To run the web app locally:
```
streamlit run app.py
```

---

## Testing

Tests use `pytest`. To run all tests:
```
pytest
```
- Includes coverage of systems, integration, unit actions, and edge cases.

## Extending

- Add new Components: define in `components/`
- Add new Systems: put pure functions in `systems/`
- Add new movement rules: add to `moves.py` and register
- Add new tile graphics: extend or override `TEXTURE_MAP` in `renderer/texture.py`


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
