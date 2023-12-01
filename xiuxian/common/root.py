from . import singleton
from .game_data_manager import GameConfig


@singleton
class Root(GameConfig):
    def __init__(self):
        super().__init__("灵根")


