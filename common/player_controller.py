import datetime
from typing import TypeVar, Callable

from . import player_singleton
from .backpack import BackpackSystem
from .model.newbie_gift import NewbieGift
from .model.player_info import PlayerInfo
from .root import Root


class PlayerNoFoundException(Exception):

    def __init__(self):
        super().__init__('')


def create_player(uid: str, name: str):
    player = PlayerInfo(uid=uid,
                        name=name,
                        root="未知",
                        level="炼体境",
                        exp=0,
                        hp=100,
                        mp=10,
                        attack=10,
                        defense=1,
                        money=0,
                        created_at=datetime.datetime.now()
                        )
    player.save()
    return player


def get_player(uid: str):
    try:
        return PlayerController(uid)
    except:
        return None


T = TypeVar('T')


# @player_singleton
class PlayerController:
    def __init__(self, user_id):
        self._uid = user_id
        self._backpack: BackpackSystem = None
        self.equipment = {}
        self.skills = []
        self._player_info: PlayerInfo = None
        self._sign_in_info: NewbieGift = None
        self.init_user_db()

    def init_user_db(self):
        try:
            self._player_info = PlayerInfo.get(PlayerInfo.uid == self._uid)
        except Exception:
            raise PlayerNoFoundException()

    @property
    def uid(self):
        return self._uid

    @property
    def name(self):
        return self._player_info.name

    @name.setter
    def name(self, value):
        self._player_info.name = value

    @property
    def root(self):
        return Root(self._player_info.root)

    def add_exp(self, experience):
        pass

    def level_up(self):
        pass

    def add_money(self, money) -> str:
        self._player_info.money += money
        return f"灵石：{money}枚"

    def equip_item(self, item):
        self.equipment[item.name] = item

    @property
    def backpack(self):
        return self.get_data(BackpackSystem)

    def get_data(self, cls: Callable[..., T]) -> T:
        return cls(self._uid)

    def save(self):
        self._player_info.save()
