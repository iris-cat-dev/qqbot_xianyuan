from datetime import datetime

from nonebot import on_fullmatch, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from . import check_has_blessed_spot
from ..common.bot_utils import xiuxian_send_message
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import check_player, Cooldown
from ..common.item_json import Items
from ..common.read_buff import save_player_info, read_player_info
from ..common.xiuxian2_handle import XiuxianDateManage

vein_get = on_fullmatch("灵矿收取", priority=8, permission=GROUP, block=True)
vein_add = on_fullmatch("灵矿开垦", priority=5, permission=GROUP, block=True)
vein_up = on_fullmatch("灵矿升级", priority=5, permission=GROUP, block=True)
vein_help = on_fullmatch("灵矿帮助", priority=5, permission=GROUP, block=True)

VEIN_LEVEL_UP_CONFIG = {
    "0": {
        "level_up_cost": 500000
    },
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
sql_manager = XiuxianSqlManager()

items = Items()
VEIN_GET_CONFIG = {
    "time_cost": 1,  # 单位小时
    "加速基数": 0.05,
    "stone": 20000,
    "max_stone": 80000
}

__vein_help__ = f"""
灵矿帮助信息:
指令：
1、灵矿开垦:增加灵矿的数量
2、灵矿收取:洞天福地中购买灵矿
3、灵矿查询:查询灵矿的状态
灵矿 1 个小时可收取一次
""".strip()



@vein_help.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(vein_help, message=__vein_help__)


@vein_add.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def vein_add_(_: Bot, event: GroupMessageEvent):
    """
    灵矿升级
    """
    user_id = event.user_id
    user_info = sql_manager.get_user_info(user_id)
    has_bs, msg = check_has_blessed_spot(user_id)
    if has_bs is False:
        await xiuxian_send_message(vein_add, message=msg)

    vein_info = {
        'num': 0,
        '收取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    vein_info = read_player_info(user_id, "vein", vein_info)
    now_num = vein_info['num']
    if now_num == len(VEIN_LEVEL_UP_CONFIG):
        msg = f"道友的灵矿已全部开垦完毕，无法继续开垦了！"
    else:
        cost = VEIN_LEVEL_UP_CONFIG[str(now_num)]['level_up_cost']
        if int(user_info.stone) < cost:
            msg = f"本次开垦需要灵石：{cost}，道友的灵石不足！"
        else:
            now_num = now_num + 1
            vein_info['num'] = now_num
            msg = f"道友成功消耗灵石：{cost}，开垦灵矿数量 +1 , 目前数量:{now_num}"
            save_player_info(user_id, vein_info, "vein")
            sql_message.update_ls(user_id, cost, 2)
    await xiuxian_send_message(vein_add, message=msg)


@vein_get.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def vein_get_(_: Bot, event: GroupMessageEvent):
    """
    灵矿收取
    """
    user_id = event.user_id
    has_bs, msg = check_has_blessed_spot(user_id)
    if has_bs is False:
        await xiuxian_send_message(vein_get, message=msg)

    vein_info = read_player_info(user_id, "vein")
    last_time = vein_info['收取时间']

    if last_time != 0:
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_diff = round((datetime.strptime(now_time, '%Y-%m-%d %H:%M:%S') -
                           datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600,
                          2)
        real_need_time = round(VEIN_GET_CONFIG['time_cost'] * (1 - VEIN_GET_CONFIG['加速基数']), 2)
        if time_diff >= real_need_time:

            stone = vein_info['num'] * VEIN_GET_CONFIG["stone"]
            sql_message.update_ls(user_id, stone, 1)

            msg = f'随着一队人马陆续的到来，道友灵矿场的灵石已运输到洞府，一共收获灵石：{stone}枚！'
            vein_info['收取时间'] = now_time
            save_player_info(user_id, vein_info, "vein")
            await xiuxian_send_message(vein_get, message=msg)

        else:
            minute = round((real_need_time - time_diff) * 60)
            msg = f"道友的采矿队伍未归来，下次收取时间为：{minute} 分钟之后"
            await xiuxian_send_message(vein_get, message=msg)
