from .item_data_source import ItemDataSource
from .model.backpack import Backpack


class BackpackSystem:
    def __init__(self, uid: str):
        self._uid = uid

    def add_item(self, item_id: int, count: int = 1, is_bind: bool = False) -> str:

        if count <= 0:
            return "数量必须大于0"

        items = ItemDataSource()
        item = items.find_by_id(item_id)
        if item is None:
            return "物品不存在"

        user_item = Backpack.get_or_none(
            uid=self._uid,
            item_id=item_id
        )

        if user_item:
            user_item.count += count
        else:
            user_item = Backpack(
                uid=self._uid,
                item_id=item_id,
                count=count,
                is_bind=is_bind
            )

        user_item.save()

        if "sub_level" in item:
            msg = f"【{item['sub_level'] + item['name']}】x {count}"
        else:
            msg = f"【{item['name']}】x {count}"
        return msg

    def del_item(self, item_id: int, count: int = 1) -> str:
        Backpack.delete()
