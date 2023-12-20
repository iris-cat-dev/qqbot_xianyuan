from ..common import singleton, player_singleton
from ..common.game_data_manager import GameData, PlayerData, GameConfig


@singleton
class XianYuanGameData(GameData):

    def __init__(self):
        self.wife={}
        super().__init__("xianyuan")


@player_singleton
class XianYuanPlayerData(PlayerData):

    def __init__(self, user_id: int):
        self.current_mission = {}
        self.point = 0
        super().__init__(user_id, "xianyuan")



@singleton
class XianYuanGameData(GameConfig):

    def __init__(self):
        super().__init__("仙子.json")



