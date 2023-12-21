from ..common import singleton, player_singleton
from ..common.game_data_manager import GameData, PlayerData, GameConfig


@singleton
class XianYuanGameData(GameData):

    def __init__(self):
        self.girl = {}
        super().__init__("xianyuan")


@player_singleton
class XianYuanPlayerData(PlayerData):

    def __init__(self, user_id: int):
        self.current_mission = {}
        self.is_finish_special_mission = False
        self.point = 0
        super().__init__(user_id, "xianyuan")


@singleton
class XianYuanConfig(GameConfig):

    def __init__(self):
        super().__init__("仙缘/仙子")
        self._missions = self.load_data("仙缘/普通任务")

    @property
    def girls(self):
        return self._data_source

    @property
    def missions(self):
        return self._missions
