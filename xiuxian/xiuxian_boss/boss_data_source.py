from typing import List

from ..common import singleton, player_singleton
from ..common.game_data_manager import GameData, GameConfig, PlayerData


@singleton
class BossGameData(GameData):

    def __init__(self):
        self.group_list: List[int] = []
        self.boss_list: List[dict] = []
        super().__init__("boss")


@player_singleton
class BossPlayerData(PlayerData):

    def __init__(self, user_id: int):
        self.point = 0
        super().__init__(user_id, "boss_shop")


@singleton
class BossConfig(GameConfig):

    def __init__(self):
        super().__init__("领主/领主参数")

    @property
    def boss_name_list(self) -> List[str]:
        return self._data_source["Boss名字"]

    @property
    def boss_max_num(self) -> int:
        return self._data_source["Boss个数上限"]

    @property
    def boss_magnification(self) -> dict:
        """
        boss 倍率
        """
        return self._data_source["Boss倍率"]

    @property
    def boss_create_time(self) -> dict:
        return self._data_source["Boss生成时间"]


@singleton
class BossPointShopConfig(GameConfig):

    def __init__(self):
        super().__init__("领主/积分商品")

    @property
    def goods_list(self) -> List[dict]:
        return self._data_source
