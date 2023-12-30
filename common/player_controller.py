import datetime
from typing import TypeVar, Callable

from . import PlayerSingleton
from .backpack import BackpackSystem
from .level import Level
from .model.player_info import PlayerInfo
from .player_state import PlayerState
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


class PlayerController(PlayerSingleton):
    def __init__(self, user_id):
        self._uid = user_id
        self.equipment = {}
        self.skills = []
        self._backpack: BackpackSystem = None
        self._player_info: PlayerInfo = None
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
        self._player_info.save()

    @property
    def root(self):
        return Root(self._player_info.root)

    @property
    def level(self):
        return Level(self._player_info.level)

    def add_exp(self, experience):
        self._player_info.exp += experience
        self._player_info.save()

    def level_up(self):
        pass

    def add_money(self, money) -> str:
        self._player_info.money += money
        self._player_info.save()
        return f"灵石：{money}枚"

    def sub_money(self, money) -> (bool, str):
        if self._player_info.money < money:
            return False, "灵石不足"

        self._player_info.money -= money
        self._player_info.save()
        return True, f"灵石：{money}枚"

    def equip_item(self, item):
        self.equipment[item.name] = item

    @property
    def backpack(self):
        return self.get_data(BackpackSystem)

    @property
    def state(self):
        return self.get_data(PlayerState)

    def get_data(self, cls: Callable[..., T]) -> T:
        return cls(self._uid)

    def save(self):
        self._player_info.save()
