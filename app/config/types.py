from .sources.maze_source import MazeConfig
from .sources.gameplay_source import GameplayConfig
from .sources.cipher_source import CipherConfig
from .sources.editor_source import EditorConfig

AppConfig = MazeConfig | GameplayConfig | CipherConfig | EditorConfig
