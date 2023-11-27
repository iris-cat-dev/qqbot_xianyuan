import random
from datetime import datetime

from nonebot import on_fullmatch, on_startswith, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..item_json import Items
from ..lay_out import Cooldown
from ..read_buff import get_player_info, save_player_info
from ..utils import check_user
from ..xiuxian2_handle import XiuxianDateManage, xiuxian_impart
from ..xiuxian_config import USERRANK

garden_get = on_fullmatch("灵田收取", priority=8, permission=GROUP, block=True)
garden_up = on_fullmatch("灵田开垦", priority=5, permission=GROUP, block=True)
garden_help = on_fullmatch("灵田帮助", priority=5, permission=GROUP, block=True)

LING_TIAN_CONFIG = {
    "1": {
        "level_up_cost": 1000000
    },
    "2": {
        "level_up_cost": 2000000
    },
    "3": {
        "level_up_cost": 4000000
    },
    "4": {
        "level_up_cost": 80000000
    },
    "5": {
        "level_up_cost": 160000000
    }
}
sql_message = XiuxianDateManage()
items = Items()


__garden_help__ = f"""
灵田帮助信息:
指令：
1、灵田开垦:查看自己的洞天福地
2、灵田收取:购买洞天福地
灵田 4 个小时可收取一次
""".strip()

@garden_help.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(garden_help, message=__garden_help__)



@garden_up.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def garden_up_(bot: Bot, event: GroupMessageEvent):
    """
    灵田升级
    """
    _, user_info, _ = check_user(event)

    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(garden_up, message=msg)

    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_num = mix_elixir_info['灵田数量']
    if now_num == len(LING_TIAN_CONFIG) + 1:
        msg = f"道友的灵田已全部开垦完毕，无法继续开垦了！"
    else:
        cost = LING_TIAN_CONFIG[str(now_num)]['level_up_cost']
        if int(user_info.stone) < cost:
            msg = f"本次开垦需要灵石：{cost}，道友的灵石不足！"
        else:
            msg = f"道友成功消耗灵石：{cost}，灵田数量+1,目前数量:{now_num + 1}"
            mix_elixir_info['灵田数量'] = now_num + 1
            save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
            sql_message.update_ls(user_id, cost, 2)

    await xiuxian_send_message(garden_up, message=msg)


@garden_get.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def garden_get_(_: Bot, event: GroupMessageEvent):
    """
    灵田收取
    """
    _, user_info, _ = check_user(event)

    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(garden_get, message=msg)

    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    GETCONFIG = {
        "time_cost": 4,  # 单位小时
        "加速基数": 0.05
    }
    last_time = mix_elixir_info['收取时间']
    if last_time != 0:
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
        time_deff = round((datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S') -
                          datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600,
                         2)
        if time_deff >= round(GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['药材速度'])), 2):
            yaocai_id_list = items.get_random_id_list_by_rank_and_item_type(USERRANK[user_info.level], ['药材'])
            # 加入传承
            impart_data = xiuxian_impart.get_user_message(user_id)
            impart_reap_per = impart_data.impart_reap_per if impart_data is not None else 0
            num = mix_elixir_info['灵田数量'] + mix_elixir_info['收取等级'] + impart_reap_per
            msg = ''
            if not yaocai_id_list:
                sql_message.send_back(user_info.user_id, 3001, '恒心草', '药材', num)  # 没有合适的，保底
                msg += f"道友成功收获药材：恒心草 {num} 个！\n"
            else:
                i = 1
                give_dict = {}
                while i <= num:
                    id = random.choice(yaocai_id_list)
                    try:
                        give_dict[id] += 1
                        i += 1
                    except LookupError:
                        give_dict[id] = 1
                        i += 1
                for k, v in give_dict.items():
                    goods_info = items.get_data_by_item_id(k)
                    msg += f"道友成功收获药材：{goods_info['name']} {v} 个！\n"
                    sql_message.send_back(user_info.user_id, k, goods_info['name'], '药材', v)

            mix_elixir_info['收取时间'] = now_time
            save_player_info(user_id, mix_elixir_info, "mix_elixir_info")
            await xiuxian_send_message(garden_get, message=msg)

        else:
            hour = round((GETCONFIG['time_cost'] * (1 - (GETCONFIG['加速基数'] * mix_elixir_info['药材速度'])) - time_deff) * 60)
            msg = f"道友的灵田还不能收取，下次收取时间为：{hour}分钟之后"
            await xiuxian_send_message(garden_get, message=msg)
