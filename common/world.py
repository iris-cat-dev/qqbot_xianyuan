from .game_data_manager import IGameConfig


class Map(object):

    def __init__(self, map_list: list):
        self._name_cache = {}
        self._coord_cache = {}

        for map_item in map_list:
            self._name_cache[map_item["name"]] = map_item
            self._coord_cache[(map_item["coordinate"][0],map_item["coordinate"][1])] = map_item

    def get_item(self, x, y):
        if (x, y) not in self._coord_cache:
            return None
        return self._coord_cache[(x, y)]

    def get_surroundings(self, name: str) -> dict:
        curr_name = self._name_cache[name]
        curr_pos = curr_name["coordinate"]
        x = curr_pos[0]
        y = curr_pos[1]
        return {
            "n": self.get_item(x, y - 1),
            "s": self.get_item(x, y + 1),
            "w": self.get_item(x - 1, y),
            "e": self.get_item(x + 1, y)
        }

class World(IGameConfig):

    def __init__(self):
        super().__init__()

        self._world_map = self.load_data("地图/世界")

    def load_map(self, channel_id: str) -> Map | None:
        if channel_id not in self._world_map:
            return None

        sub_map_name = self._world_map[channel_id]
        return Map(self.load_data(f"地图/{sub_map_name}"))
