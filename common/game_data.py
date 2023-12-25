from ..common import singleton
from ..common.game_data_manager import IGameData


@singleton
class GlobalGameData(IGameData):

    def __init__(self):
        super().__init__("global")
