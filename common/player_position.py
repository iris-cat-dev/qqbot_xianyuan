from .world import World

world = World()


class PlayerPosition:

    def __init__(self, user_id: str, channel_id: str):
        pass

    def show_env(self):
        pass

    def show_player(self):
        pass

    def show_npc(self):
        pass

    def show_item(self):
        pass

    def walk(self, direction: str) -> str:
        pass
