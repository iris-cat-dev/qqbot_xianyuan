from .game_data_manager import IGameConfig
from .model.backpack import Backpack


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
        self.items = []
        self.items += self.load_data("修炼物品/悬赏令")
        self.items += self.load_data("修炼物品/秘境藏宝图")

    def _cache(self):
        pass


class BackpackSystem:
    def __init__(self, uid: str):
        self._uid = uid

    def add_item(self, item_id: int, count: int = 1, is_bind: bool = False) -> str:

        user_item = Backpack.get_or_none(
            uid=self._uid,
            item_id=item_id
        )

        if user_item:
            user_item.count += count
        else:
            Backpack(
                uid=self._uid,
                item_id=item_id,
                count=count,
                is_bind=is_bind
            )
        msg = ""

    def del_item(self, item_id: int, count: int = 1) -> str:
        Backpack.delete()
