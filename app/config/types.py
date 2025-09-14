from .sources.maze_source import MazeConfig
from .sources.gameplay_source import GameplayConfig
from .sources.cipher_source import CipherConfig

AppConfig = MazeConfig | GameplayConfig | CipherConfig
