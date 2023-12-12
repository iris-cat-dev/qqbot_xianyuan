from ..common import singleton
from ..common.game_data_manager import GameConfig, PlayerData


@singleton
class BlessedSpotConfig(GameConfig):

    def __init__(self):
        self.price = 0
        super().__init__("洞天福地/blessed_spot")


@singleton
class GardenConfig(GameConfig):

    def __init__(self):
        super().__init__("洞天福地/灵田")


@singleton
class VeinConfig(GameConfig):

    def __init__(self):
        super().__init__("洞天福地/灵矿")


class BlessedSpotPlayerData(PlayerData):

    def __init__(self, user_id):
        self.has_blessed_spot = False
        self.garden_list = []
        self.vein_list = []
        super().__init__(user_id, "blessed_spot")
