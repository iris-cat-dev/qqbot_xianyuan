from ..common.game_data_manager import IGameData


class GlobalGameData(IGameData):

    def __init__(self):
        super().__init__("global")

    def get_game_data(self) -> dict:
        pass

