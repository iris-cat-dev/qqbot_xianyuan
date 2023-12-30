from datetime import datetime
from transitions import Machine

from . import PlayerSingleton
from .model.player_state import TBPlayerState


class PlayerState(PlayerSingleton):
    states = ['发呆中', '修炼中', '疗伤中', "闭关疗伤中", "闭关中", "闭关修炼中"]

    def __init__(self, user_id):
        self._db, created = TBPlayerState.get_or_create(uid=user_id)
        self.machine = Machine(model=self, states=PlayerState.states, initial=self._db.state)

        self.machine.add_transition(trigger='闭关', source='发呆中', dest='闭关中', after=self.test1)

        self.machine.add_transition(trigger='修炼', source='发呆中', dest='修炼中')
        self.machine.add_transition(trigger='修炼', source='闭关中', dest='闭关修炼中')
        self.machine.add_transition(trigger='修炼', source='疗伤中', dest='修炼中')
        self.machine.add_transition(trigger='修炼', source='闭关疗伤中', dest='闭关修炼中')

        self.machine.add_transition(trigger='疗伤', source='发呆中', dest='疗伤中')
        self.machine.add_transition(trigger='疗伤', source='闭关中', dest='闭关疗伤中')
        self.machine.add_transition(trigger='疗伤', source='修炼中', dest='疗伤中')
        self.machine.add_transition(trigger='疗伤', source='闭关修炼中', dest='闭关疗伤中')

        self.machine.add_transition(trigger='结束疗伤', source='疗伤中', dest='发呆中')
        self.machine.add_transition(trigger='结束疗伤', source='闭关疗伤中', dest='闭关中')

        self.machine.add_transition(trigger='结束修炼', source='修炼中', dest='发呆中')
        self.machine.add_transition(trigger='结束修炼', source='闭关修炼中', dest='闭关中')

        self.machine.add_transition(trigger='出关', source='闭关疗伤中', dest='发呆中')
        self.machine.add_transition(trigger='出关', source='闭关修炼中', dest='发呆中')
        self.machine.add_transition(trigger='出关', source='闭关中', dest='发呆中')

    @property
    def state(self) -> int:
        return self._db.state

    @state.setter
    def state(self, state: str):
        self._db.state = state
        self.save()

    @property
    def update_at(self):
        return self._db.update_at

    @property
    def position(self) -> int:
        return self._db.position

    @position.setter
    def position(self, position: str):
        self._db.position = position
        self.save()

    def update(self, state: str) -> (bool, str):
        try:
            getattr(self, state)()
        except:
            if self.state == "发呆中":
                return False, "道友正在发呆，呆呆呆呆呆呆～"

            if state in str(self.state):
                return False, f"道友已在{self.state}！"

            return False, f"切换失败, 请先结束【{self.state[:-1]}】"

        return True, f"道友进入{self.state}!"

    def save(self) -> None:
        self._db.update_at = datetime.now()
        self._db.save()

    def test1(self):
        print("test1")
