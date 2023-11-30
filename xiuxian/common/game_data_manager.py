import json
import os
from pathlib import Path

DATA_ROOT = Path() / "data" / "xiuxian"


class GameDate:

    def __init__(self, name):
        self.name = name
        self._load_data(name)

    def save(self):
        save_dict = self.__dict__
        name = self.name
        self._save_data(name, save_dict)

    def _load_data(self, name):
        self.__dict__ = self._read_json(DATA_ROOT / f"{name}.json", self.__dict__)

    def _save_data(self, name, data):
        return self._save_json(DATA_ROOT / f"{name}.json", data)

    def _read_json(self, filepath, default=None):
        if not os.path.exists(filepath) and default is not None:
            return default
        with open(filepath, "r", encoding="UTF-8") as f:
            data = f.read()
        return json.loads(data)

    def _save_json(self, filepath, data):
        data = json.dumps(data, ensure_ascii=False, indent=4)
        save_mode = "w" if os.path.exists(filepath) else "x"
        with open(filepath, mode=save_mode, encoding="UTF-8") as f:
            f.write(data)
            f.close()
