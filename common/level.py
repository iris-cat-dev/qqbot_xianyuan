from . import singleton
from .game_data_manager import IGameConfig




@singleton
class Rank(IGameConfig):
    RANK_LIST = list(RANK.keys())
    MAX_RANK = 1
    MIN_RANK = 56

    def __init__(self):
        super().__init__("境界")

    def to_level(self, name: str) -> int:
        return RANK[name]

    def to_level_index(self, name: str) -> int:
        if len(name) == 3:
            name = name + "中期"
        return self.MIN_RANK - RANK[name]

    def to_big_rank(self, name) -> str:
        """
        取境界前3位，去除初期、中期、圆满
        """
        if name == '江湖好手':
            big_rank = '江湖好手'
        elif name == '天道之上':
            big_rank = '天道之上'
        else:
            big_rank = name[:3]
        return big_rank

    def get_rank_info(self, name: str, next_count: int = 0) -> dict:
        if next_count == 0:
            rank_info = self._data_source[name]
            rank_name = name
        else:
            idx = self.RANK_LIST.index(name)
            rank_name = self.RANK_LIST[idx + next_count]
            rank_info = self._data_source[self.RANK_LIST[idx + next_count]]

        rank_info["name"] = rank_name
        return rank_info

    def get_big_rank_info(self, name: str):
        big_rank = self.to_big_rank(name)
        if len(big_rank) == 3:
            big_rank += "中期"
        return self.get_rank_info(big_rank)

    def compare(self, name1: str, name2: str) -> int:
        if name1 == name2:
            return 0

        elif RANK[name1] > RANK[name2]:
            # 等级1 低于 等级2
            return -1
        else:
            # 等级高于
            return 1

    def compare_big_rank(self, name1: str, name2: str) -> int:
        if name1[:3] == name2[:3]:
            return 0

        elif RANK[name1] > RANK[name2]:
            # 等级1 低于 等级2
            return -1
        else:
            # 等级高于
            return 1

    def is_max(self, name) -> bool:
        return RANK[name] == self.MAX_RANK

    def get_rank_exp(self, name) -> int:
        return self._data_source[name]["exp"]

    def get_next_rank_exp(self, name) -> int:
        if self.is_max(name):
            return 0

        need_rank = self.get_rank_info(name, 1)
        return need_rank["exp"]

    def get_rank_speed(self, name) -> int:
        return self._data_source[name]["speed"]

    def get_rank_rate(self, name) -> int:
        return self._data_source[name]["rate"]
