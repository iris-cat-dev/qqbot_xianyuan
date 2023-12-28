from .game_data_manager import IGameConfig


class Item:

    def __init__(self):
        self.id = None
        self.name = None
        self.level = None
        self.desc = None
        self.price = None


class ItemDataSource(IGameConfig):

    def __init__(self):
        super().__init__()
        self._id_cache = {}
        self._name_cache = {}
        self.items = []
        self.items += self.load_data("修炼物品/悬赏令")
        self.items += self.load_data("修炼物品/秘境藏宝图")

        self._cache()

    def _cache(self):
        for item in self.items:
            self._id_cache[item["id"]] = item
            self._name_cache[item["name"]] = item

    def find_by_id(self, item_id: int):
        return self._id_cache.get(item_id, None)

    def find_by_name(self, item_name: str):
        return self._name_cache.get(item_name, None)
