import random

from . import singleton
from .game_data_manager import IGameConfig
from .rate_calculater import calculated


@singleton
class Root(IGameConfig):
    def __init__(self, user_root: str):
        super().__init__("灵根")
        self._user_root = user_root

    def get_root_info(self):
        return self._data_source[self._user_root]

    def get_root_speed(self):
        return self._data_source[self._user_root]["type_speeds"]

    def get_random_root(self):
        """
        获取灵根信息
        """
        rate_dict = {}
        for key, value in self._data_source.items():
            rate_dict[key] = value["type_rate"]
        lgen = calculated(rate_dict)
        if self._data_source[lgen]["type_flag"]:
            flag = random.choice(self._data_source[lgen]["type_flag"])
            root_name = random.sample(self._data_source[lgen]["type_list"], flag)
            return "、".join(root_name) + '属性灵根', lgen
        else:
            root_name = random.choice(self._data_source[lgen]["type_list"])
            return root_name, lgen
