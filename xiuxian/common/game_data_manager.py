import json
import os
from pathlib import Path

DATA_ROOT = Path() / "data" / "xiuxian"
PLAYER_ROOT = Path() / "data" / "xiuxian" / "players"
CONFIG_ROOT = Path() / "nonebot_plugin_xiuxian3" / "data"


def _read_json(filepath, default=None):
    if not os.path.exists(filepath) and default is not None:
        return default
    with open(filepath, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def _save_json(filepath, data):
    data = json.dumps(data, ensure_ascii=False, indent=4)
    save_mode = "w" if os.path.exists(filepath) else "x"
    with open(filepath, mode=save_mode, encoding="UTF-8") as f:
        f.write(data)
        f.close()


class GameData:

    def __init__(self, name):
        self.name = name
        self._load_data(name)

    def save(self):
        save_dict = self.__dict__
        name = self.name
        self._save_data(name, save_dict)

    def _load_data(self, name):
        self.__dict__ = _read_json(DATA_ROOT / f"{name}.json", self.__dict__)

    def _save_data(self, name, data):
        return _save_json(DATA_ROOT / f"{name}.json", data)


class PlayerData:

    def __init__(self, user_id: int, name: str):
        self.name = name
        self.user_id = str(user_id)
        self._load_data(name)

    def save(self):
        save_dict = self.__dict__
        name = self.name
        self._save_data(name, save_dict)

    def _load_data(self, name):
        self.__dict__ = _read_json(PLAYER_ROOT / self.user_id / f"{name}.json", self.__dict__)

    def _save_data(self, name, data):
        return _save_json(PLAYER_ROOT / self.user_id / f"{name}.json", data)


class GameConfig:

    def __init__(self, name: str = None):
        self._data_source = {}
        if name is not None:
            self._load_data(name)

    def load_data(self, name):
        return _read_json(CONFIG_ROOT / f"{name}.json")

    def _load_data(self, name):
        self._data_source = _read_json(CONFIG_ROOT / f"{name}.json")
