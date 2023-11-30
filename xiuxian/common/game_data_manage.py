import json
import os
from pathlib import Path
from typing import List


class GameDateManage:

    def __init__(self):
        pass



    def read_json(self, filepath):
        with open(filepath, "r", encoding="UTF-8") as f:
            data = f.read()
        return json.loads(data)

    def save_json(self, filepath, data):
        data = json.dumps(data, ensure_ascii=False, indent=4)
        save_mode = "w" if os.path.exists(filepath) else "x"
        with open(filepath, mode=save_mode, encoding="UTF-8") as f:
            f.write(data)
            f.close()

