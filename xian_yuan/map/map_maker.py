import csv
import json

if __name__ == "__main__":
    map_list = []
    with open('/Users/bytedance/Project/chatgpt_qq_bot/nonebot_plugin_xiuxian3/data/地图/新手村.csv', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        y = 0
        for row in reader:
            x = 0
            for col in row:
                if col != "" and col != '\ufeff':
                    item = {
                        "name": col,
                        "coordinate": [x, y],
                        "npc": [
                        ],
                        "item": [
                        ],
                        "type": "",
                        "desc": ""
                    }
                    map_list.append(item)
                x += 1
            y += 1
    print(json.dumps(map_list))
