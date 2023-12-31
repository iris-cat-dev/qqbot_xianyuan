from .game_data_manager import IGameConfig


class World(IGameConfig):

    def __init__(self):
        super().__init__()

        self._world_map = self.load_data("地图/世界")

    def load_map(self, channel_id: str):
        if channel_id not in self._world_map["channel_id"]:
            return None

        sub_map_name = self._world_map["channel_id"]
        return self.load_data(f"地图/{sub_map_name}")
