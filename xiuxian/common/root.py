import random

from . import singleton
from .game_data_manager import GameConfig
from ..xiuxian2_handle import OtherSet


@singleton
class Root(GameConfig):
    def __init__(self):
        super().__init__("灵根")

    def get_root(self, type_name):
        return self._data_source[type_name]

    def get_root_speed(self, type_name):
        return self._data_source[type_name]["type_speeds"]

    def get_random_root(self):
        """
        获取灵根信息
        """
        rate_dict = {}
        for key, value in self._data_source.items():
            rate_dict[key] = value["type_rate"]
        lgen = OtherSet().calculated(rate_dict)
        if self._data_source[lgen]["type_flag"]:
            flag = random.choice(self._data_source[lgen]["type_flag"])
            root_name = random.sample(self._data_source[lgen]["type_list"], flag)
            for j in root_name:
                if j == root_name[-1]:
                    root_name += j
                    break
                root_name += (j + "、")
            return root_name + '属性灵根', lgen
        else:
            root_name = random.choice(self._data_source[lgen]["type_list"])
            return root_name, lgen
