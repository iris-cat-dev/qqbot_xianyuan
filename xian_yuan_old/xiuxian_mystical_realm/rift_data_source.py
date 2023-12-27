from ..common import singleton, player_singleton
from ..common.game_data_manager import GameConfig, PlayerData


@singleton
class MysticalRealmConfig(GameConfig):

    def __init__(self):
        super().__init__()
        self.normal_mystical_realm_list = self.load_data("秘境/常驻秘境")

    def get_normal_mystical_realm(self, name):
        for key, value in self.normal_mystical_realm_list:
            if key == name:
                value["name"] = key
                return value
        return None


@player_singleton
class MysticalRealmPlayerData(PlayerData):

    def __init__(self, user_id: int):
        self.current_mystical_realm = {}
        self.sense = []
        super().__init__(user_id, "mystical_realm")

    def has_mystical_realm(self) -> bool:
        return len(self.current_mystical_realm) > 0
