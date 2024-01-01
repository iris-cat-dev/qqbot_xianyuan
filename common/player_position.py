from datetime import datetime

from .model.player_position import TBPlayerPosition
from .world import World

world = World()


class PlayerPositionController:

    def __init__(self, user_id: str, channel_id: str):
        self._db: TBPlayerPosition = None
        self._db, _ = TBPlayerPosition.get_or_create(uid=user_id, channel_id=channel_id)
        self._channel_id = channel_id
        self._curr_position_info = None

    def show_env(self) -> str:
        if self._curr_position_info:
            return self._curr_position_info["desc"]

    def show_player(self):
        pass

    def show_npc(self):
        pass

    def show_item(self):
        pass

    def format_surrounding(self, surrounding):
        result = {}
        if surrounding["n"]:
            result["北"] = surrounding["n"]["name"]

        if surrounding["s"]:
            result["南"] = surrounding["s"]["name"]

        if surrounding["w"]:
            result["西"] = surrounding["w"]["name"]

        if surrounding["e"]:
            result["东"] = surrounding["e"]["name"]

        msg = ""
        for k, v in result.items():
            msg += f"{k}：{v}\n"
        return msg

    def move(self, direction: str) -> str:
        channel_map = world.load_map(self._channel_id)
        surrounding = channel_map.get_surroundings(self._db.position)
        position_info = surrounding[direction]
        self._curr_position_info = position_info
        if position_info is None:
            return ("道友这个方向没有路\n"
                    + f"当前位置：{self._db.position}\n"
                    + self.format_surrounding(surrounding))

        self._db.position = position_info["name"]
        self.save()
        surrounding = channel_map.get_surroundings(self._db.position)
        return (f"道友来到：{self._db.position}\n"
                + f"{self.show_env()}\n"
                + self.format_surrounding(surrounding))

    def save(self):
        self._db._channel_id = self._channel_id
        self._db.update_at = datetime.now()
        self._db.save()
