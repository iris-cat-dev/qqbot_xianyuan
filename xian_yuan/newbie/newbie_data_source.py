from datetime import datetime
from typing import List, Any

from ...common.game_data_manager import IGameConfig
from ...common.model.newbie_gift import NewbieGift


class NewbieGiftPlayerData:

    def __init__(self, uid: str):
        self._db, created = NewbieGift.get_or_create(uid=uid)

    @property
    def times(self) -> int:
        return self._db.times

    @times.setter
    def times(self, times: int):
        self._db.times = times
        self.save()

    @property
    def update_at(self):
        return self._db.update_at

    def save(self):
        self._db.update_at = datetime.now()
        self._db.save()



class NewbieGiftConfig(IGameConfig):

    def __init__(self):
        super().__init__("新手/礼包")

    @property
    def gift_list(self) -> List[Any]:
        return self._data_source
