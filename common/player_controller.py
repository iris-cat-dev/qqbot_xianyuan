import datetime

from . import player_singleton
from .model.player_info import PlayerInfo
from .model.sign_in import SignInInfo
from .root import Root
from .utils import is_today


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


@player_singleton
class PlayerController:
    def __init__(self, user_id):
        self._uid = user_id
        self.inventory = []
        self.equipment = {}
        self.skills = []
        self._player_info: PlayerInfo = None
        self._sign_in_info: SignInInfo = None
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

    @property
    def is_sign_in(self):
        if self._sign_in_info is None:
            self._sign_in_info = SignInInfo.get_or_create(uid=self._uid)
            if not self._sign_in_info.update_at:
                return False

        if not is_today(self._sign_in_info.update_at):
            return False
        return True

    @is_sign_in.setter
    def is_sign_in(self, value):
        self._sign_in_info.update_at = datetime.datetime.now()
        self._sign_in_info.save()

    def add_exp(self, experience):
        pass

    def level_up(self):
        pass

    def add_item(self, item):
        self.inventory.append(item)

    def equip_item(self, item):
        self.equipment[item.name] = item

    def save(self):
        self._player_info.save()
