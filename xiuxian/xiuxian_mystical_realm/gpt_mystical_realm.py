import json
import logging
import random

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent, Bot

from ..common.bot_utils import xiuxian_send_message, get_input_cmd
from ..common.zhipuai_agent import request_gpt

gpt_mystical_realm_start = on_fullmatch("探索龙陵墓穴", priority=5, permission=GROUP, block=True)
gpt_mystical_realm_next = on_startswith("继续", priority=5, permission=GROUP, block=True)

env = {
    "scene": "场景描写，表明方位",
    "environment": "环境描写",
    "discovery": [
        "发现的线索1",
        "发现的线索2",
    ]
}

action = {
    "point": "数字",
    "scene": "场景描写，表明方位",
    "environment": "环境描写",
    "discovery": [
        "发现的线索1",
        "发现的线索2",
    ]
}


def get_main_prompt(tip, json_obj):
    return (
        f"1. 假如你是一个中国古代背景修仙游戏的开发者，拥有丰富的游戏策划经验和文本编写能力。\n"
        f"2. 探索秘境桥段，龙陵墓穴，需要一个情景，使用“你”作为主语,可以包含：进入墓穴盗墓时环境的位置、宫殿或者诡异的发现，{tip}\n"
        f"3. 注意不需要输出其他额外描述只需要输出 json。严格按照json 模版输出，不要输出额外字段，额外描述，能够帮我填充 json， json模版: {json.dumps(json_obj)}。"
    )


props_entry = "接下来输出一段秘境入口的环境描述"
props_enter = "进入墓穴后可能会遭遇怪物、陷阱、战斗等。"

session = {}


def escape_word(resp: str):
    resp = resp.replace("，", ",")
    resp = json.loads(resp)
    print(resp)
    resp = json.loads(resp)
    return resp


def result_to_str(obj):
    msg = (f'{obj["scene"]}\n'
           f'{obj["environment"]}\n')
    discovery = obj["discovery"]
    for item in discovery:
        msg += f"[线索]：{item}\n"
    return msg


@gpt_mystical_realm_start.handle()
async def gpt_mystical_realm_start_(_: Bot, event: GroupMessageEvent):
    """
    探索秘境
    """
    try:
        result, text = request_gpt(get_main_prompt(props_entry, env))
        obj = escape_word(text)
        msg = result_to_str(obj)
        msg += "请你输入 【继续+下一步行动】"
        session[event.user_id] = {
            "pre": obj
        }
    except Exception as e:
        logging.exception(e)
        msg = "AI 错误，重新输入"
    return await xiuxian_send_message(gpt_mystical_realm_start, msg)


@gpt_mystical_realm_next.handle()
async def gpt_mystical_realm_next_(_: Bot, event: GroupMessageEvent):
    """
    继续秘境
    """
    try:
        cmd, msg = get_input_cmd(event, 2)
        user_session = session[event.user_id]
        pre_prompt = result_to_str(user_session["pre"]) + "以上是历史记录。\n 需要结合玩家输入和历史记录输出下一步的提示,注意已经出现过的内容线索不需要重复输出，不能照搬历史记录。\n"
        user_input = f"玩家输入：[{cmd}]\n"
        main_prompt = get_main_prompt(props_enter, action)
        result, text = request_gpt(pre_prompt + user_input + main_prompt)
        obj = escape_word(text)
        msg = result_to_str(obj)
        session[event.user_id] = {
            "pre": obj
        }
        msg += f"获得灵石：{random.randint(0,100)}\n"
        msg += "请你输入 【继续+下一步行动】"
    except Exception as e:
        print(e)
        msg = "AI 错误，重新输入"

    return await xiuxian_send_message(gpt_mystical_realm_start, msg)
