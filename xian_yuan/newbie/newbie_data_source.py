from datetime import datetime
from typing import List, Any

from ...common import singleton
from ...common.game_data_manager import IGameConfig
from ...common.model.newbie_gift import NewbieGift


class NewbieGiftPlayerData:

    def __init__(self, uid: str):
        super().__init__()
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

    # @property
    # def is_sign_in(self):
    #     if self._sign_in_info is None:
    #         self._sign_in_info = SignInInfo.get_or_create(uid=self._uid)
    #         if not self._sign_in_info.update_at:
    #             return False
    #
    #     if not is_today(self._sign_in_info.update_at):
    #         return False
    #     return True
    #
    # @is_sign_in.setter
    # def is_sign_in(self, value):
    #     self._sign_in_info.update_at = datetime.datetime.now()
    #     self._sign_in_info.save()


@singleton
class NewbieGiftConfig(IGameConfig):

    def __init__(self):
        super().__init__("新手/礼包")

    @property
    def gift_list(self) -> List[Any]:
        return self._data_source
