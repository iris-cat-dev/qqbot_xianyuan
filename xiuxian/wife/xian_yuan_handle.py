import random

from .xian_yuan_data_source import XianYuanConfig, XianYuanPlayerData
from .xian_yuan_data_source import XianYuanGameData

config = XianYuanConfig()
game_data = XianYuanGameData()


def format_xian_yuan_info(girl):
    msg = f'仙子：{girl["name"]}\n'
    msg += f'境界：{girl["level"]}\n'
    msg += f'灵根：{girl["root"]}\n'
    msg += f'性格：{girl["personality"]}\n'
    msg += f'背景：{girl["background"]}\n'
    return msg


def format_xian_yuan_mission(mission):
    condition = "无"
    mission_type = mission["type"]
    if mission_type == "elixir":
        value_list = mission["value"]
        condition = f"需要丹药：{'、'.join(value_list)}"
    elif mission_type == "stone":
        condition = f"需要灵石：{mission["value"]}"

    msg = f'任务名称：{mission["name"]}\n'
    msg += f'任务描述：{mission["desc"]}\n'
    msg += f'任务条件：{condition}\n'
    return msg


def has_xian_yuan():
    if len(game_data.girl.keys()) == 0:
        return False, "当前还未生成仙缘"
    return True, ""


def create_xian_yuan():
    girl_list = config.girls
    girl = random.choice(girl_list)
    game_data.girl = girl
    game_data.save()
    return girl


def create_xian_yuan_mission(player_data: XianYuanPlayerData):
    if player_data.is_finish_special_mission is False:
        player_data.current_mission = game_data.girl["special_mission"]
    else:
        mission_list = config.missions
        mission = random.choice(mission_list)
        player_data.current_mission = mission
    player_data.save()
    return player_data.current_mission


def get_user_xian_yuan_rank_list():
    pass


def complete_mission(user_id: int):
    pass
