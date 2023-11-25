import json
import os
from pathlib import Path

config_key = ["Boss灵石", "Boss名字", "Boss倍率", "Boss个数上限", "Boss生成时间参数", 'open', "世界积分商品"]
CONFIG = {
}

def get_config():
    try:
        config = readf()
        for key in config_key:
            if key not in list(config.keys()):
                config[key] = CONFIG[key]
        savef(config)
    except:
        config = CONFIG
        savef(config)
    return config


CONFIGJSONPATH = Path(__file__).parent
FILEPATH = CONFIGJSONPATH / 'config.json'


def readf():
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def savef(data):
    data = json.dumps(data, ensure_ascii=False, indent=3)
    savemode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=savemode, encoding="UTF-8") as f:
        f.write(data)
        f.close()
    return True
