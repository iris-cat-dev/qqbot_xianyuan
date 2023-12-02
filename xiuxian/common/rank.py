from . import singleton
from .game_data_manager import GameConfig

RANK = {
    '江湖好手': 56,
    '练气境初期': 55,  # '练气境初期': 54,
    '练气境中期': 54,
    '练气境圆满': 53,
    '筑基境初期': 52,  # '筑基境初期': 51,
    '筑基境中期': 51,
    '筑基境圆满': 50,
    '结丹境初期': 49,  # '结丹境初期': 48,
    '结丹境中期': 48,
    '结丹境圆满': 47,
    '元婴境初期': 46,  # '元婴境初期': 45,
    '元婴境中期': 45,
    '元婴境圆满': 44,
    '化神境初期': 43,  # '化神境中期': 41,
    '化神境中期': 42,
    '化神境圆满': 41,
    '炼虚境初期': 40,  # '炼虚境初期': 39,
    '炼虚境中期': 39,
    '炼虚境圆满': 38,
    '合体境初期': 37,  # '合体境初期': 36,
    '合体境中期': 36,
    '合体境圆满': 35,
    '大乘境初期': 34,  # '大乘境初期': 33,
    '大乘境中期': 33,
    '大乘境圆满': 32,
    '渡劫境初期': 31,  # '渡劫境初期': 30,
    '渡劫境中期': 30,
    '渡劫境圆满': 29,
    '真仙境初期': 28,  # '半步真仙': 37,
    '真仙境中期': 27,
    '真仙境圆满': 26,
    '玄仙境初期': 25,  # '真仙境初期': 36,
    '玄仙境中期': 24,
    '玄仙境圆满': 23,
    '地仙境初期': 22,  # '金仙境初期': 33,
    '地仙境中期': 21,
    '地仙境圆满': 20,
    '天仙境初期': 19,  # '太乙境圆满': 28,
    '天仙境中期': 18,
    '天仙境圆满': 17,
    '太乙境初期': 16,
    '太乙境中期': 15,
    '太乙境圆满': 14,
    '大罗境初期': 13,
    '大罗境中期': 12,
    '大罗境圆满': 11,
    '仙王境初期': 10,
    '仙王境中期': 9,
    '仙王境圆满': 8,
    '准帝境初期': 7,
    '准帝境中期': 6,
    '准帝境圆满': 5,
    '仙帝境初期': 4,
    '仙帝境中期': 3,
    '仙帝境圆满': 2,
    '天道之上': 1,
}

RANK_LIST = list(RANK.keys())
MAX_RANK = len(RANK_LIST)


@singleton
class Rank(GameConfig):

    def __init__(self):
        super().__init__("境界")

    def to_level(self, name: str) -> int:
        return RANK[name]

    def get_rank_info(self, name: str, next_count: int = 0):
        if next_count == 0:
            rank_info = self._data_source[name]
            rank_name = name
        else:
            idx = RANK_LIST.index(name)
            rank_name = RANK_LIST[idx + next_count]
            rank_info = self._data_source[RANK_LIST[idx + next_count]]

        rank_info["name"] = rank_name
        return rank_info

    def compare(self, name1: str, name2: str) -> int:
        if name1 == name2:
            return 0
        elif RANK[name1] > RANK[name2]:
            # 等级低于
            return -1
        else:
            # 等级高于
            return 1

    def is_max(self, name) -> bool:
        return RANK[name] == MAX_RANK

    def get_rank_exp(self, name) -> int:
        return self._data_source[name]["exp"]

    def get_rank_speed(self, name) -> int:
        return self._data_source[name]["speed"]

    def get_rank_rate(self, name) -> int:
        return self._data_source[name]["rate"]
