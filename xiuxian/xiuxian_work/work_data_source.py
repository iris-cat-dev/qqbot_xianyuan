from ..common import singleton
from ..common.game_data_manager import GameConfig, PlayerData


@singleton
class RewardConfig(GameConfig):

    def __init__(self):
        super().__init__("悬赏令/等级奖励")

    @property
    def level_price_data(self) -> object:
        return self._data_source


@singleton
class WorkConfig(GameConfig):
    def __init__(self):
        super().__init__("悬赏令/config")
        self.work1 = self.load_data("悬赏令/暗杀")
        self.work2 = self.load_data("悬赏令/灵材")
        self.work3 = self.load_data("悬赏令/镇妖")

    @property
    def free_refresh_count(self) -> int:
        return self._data_source["free_refresh_count"]

    @property
    def refresh_cost(self) -> int:
        return self._data_source["refresh_cost"]

    @property
    def give_up_cost(self) -> int:
        return self._data_source["give_up_cost"]

    @property
    def max_level(self) -> str:
        return self._data_source["max_level"]

    @property
    def work_list(self) -> []:
        return [self.work1, self.work2, self.work3]


class WorkPlayerData(PlayerData):

    def __init__(self, user_id: int):
        self.work_list = []
        self.current_work = {}
        self.refresh_count = 0
        super().__init__(user_id, "work")

    def has_work(self):
        return len(self.work_list) > 0

