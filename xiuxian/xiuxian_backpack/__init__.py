import asyncio
import random
import re
from datetime import datetime

from nonebot import on_command, require, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment,
    GROUP_ADMIN,
    GROUP_OWNER,
    ActionFailed
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from .back_util import (
    get_user_back_msg, check_equipment_can_use,
    get_use_equipment_sql, check_use_elixir,
    get_use_jlq_msg, get_no_use_equipment_sql
)
from .backconfig import get_config, savef
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_img_message
from ..common.param_checker import check_player
from ..item_json import Items
from ..lay_out import Cooldown, CooldownIsolateLevel
from ..read_buff import (
    get_weapon_info_msg, get_armor_info_msg,
    get_sec_msg, get_main_info_msg
)
from ..utils import (
    check_user, get_msg_pic
)
from ..xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import XiuConfig

items = Items()
config = get_config()
groups = config['open']  # list，群交流会使用
auction = {}
AUCTIONSLEEPTIME = 120  # 交友初始等待时间（秒）
cache_help = {}
auction_offer_flag = False  # 交友标志
AUCTIONOFFERSLEEPTIME = 10  # 每次交友增加交友剩余的时间（秒）
auction_offer_time_count = 0  # 计算剩余时间
auction_offer_all_count = 0  # 控制线程等待时间
auction_time_config = config['交友会定时参数']  #
sql_message = XiuxianDateManage()

# 定时任务
set_auction_by_scheduler = require("nonebot_plugin_apscheduler").scheduler
reset_day_num_scheduler = require("nonebot_plugin_apscheduler").scheduler

my_back = on_fullmatch('我的背包', priority=10, permission=GROUP, block=True)
use = on_startswith("使用", priority=15, permission=GROUP, block=True)
no_use_zb = on_startswith("卸下", priority=5, permission=GROUP, block=True)
back_help = on_fullmatch("背包帮助", priority=8, permission=GROUP, block=True)

__back_help__ = f"""
背包帮助信息:
指令：
1、我的背包:查看自身背包前98个物品的信息
2、使用+物品名字：使用物品,丹药可批量使用
3、卸下+装备名字：卸载目标装备
""".strip()


# 重置丹药每日使用次数
@reset_day_num_scheduler.scheduled_job("cron", hour=0, minute=0, )
async def reset_day_num_scheduler_():
    sql_message.day_num_reset()
    logger.info("每日丹药使用次数重置成功！")


@back_help.handle(parameterless=[Cooldown(at_sender=True)])
async def back_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(back_help, message=__back_help__)


@my_back.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def mind_back_(_: Bot, event: GroupMessageEvent):
    """
    我的背包
    """
    user_id = event.user_id
    msg_list = get_user_back_msg(user_id)
    if len(msg_list) > 0:
        # try:
        #     for item in msg_list:
        #         msg += f"{item}\n"
        # except ActionFailed:
        #     msg = "查看背包失败"
        #     await xiuxian_send_message(my_back, msg)
        await xiuxian_send_group_img_message(event.group_id, msg_list)
    else:
        msg = '道友的背包空空如也！'
        await xiuxian_send_message(my_back, msg)


@no_use_zb.handle(parameterless=[Cooldown(at_sender=True)])
async def no_use_zb_(_: Bot, event: GroupMessageEvent):
    """
    卸载物品（只支持装备）
    """
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    arg = str(event.message)[2:]

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await xiuxian_send_message(no_use_zb, message=msg)

    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    for back in back_msg:
        if arg == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            goods_type = back.goods_type
            break

    if not in_flag:
        msg = f"请检查该道具 {arg} 是否在背包内！"
        await xiuxian_send_message(no_use_zb, message=msg)

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            sql_str, item_type = get_no_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, 0)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, 0)
            msg = f"成功卸载装备{arg}！"

        else:
            msg = f"装备没有被使用，无法卸载！"

    else:
        msg = f"只有装备支持卸下！"

    await xiuxian_send_message(no_use_zb, message=msg)


@use.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def use_(bot: Bot, event: GroupMessageEvent):
    """
    使用物品
    """
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    message = str(event.message)
    arg = message[2:]  #

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await xiuxian_send_message(use, message=msg)

    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_num = None
    for back in back_msg:
        if arg == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            goods_type = back.goods_type
            goods_num = back.goods_num
            break

    if not in_flag:
        msg = f"请检查该道具 {arg} 是否在背包内！"
        await xiuxian_send_message(use, message=msg)

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            msg = f"该装备已被装备，请勿重复装备！"
            await xiuxian_send_message(use, message=msg)

        else:  # 可以装备
            sql_str, item_type = get_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, goods_id)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, goods_id)

            msg = f"成功装备{arg}！"
            await xiuxian_send_message(use, message=msg)

    elif goods_type == "技能":
        pass

    elif goods_type == "丹药":
        try:
            num_str = re.findall("\d+", message)[0]  # boss编号
            num = int(num_str)
            if num > int(goods_num):
                msg = f"丹药数量不足，一共{goods_num}枚！"
                await xiuxian_send_message(use, message=msg)
        except:
            num = 1

        msg = check_use_elixir(user_id, goods_id, num)
        await xiuxian_send_message(use, message=msg)

    elif goods_type == "聚灵旗":
        msg = get_use_jlq_msg(user_id, goods_id)
        await xiuxian_send_message(use, message=msg)

    else:
        msg = '该类型物品调试中，未开启！'
        await xiuxian_send_message(use, message=msg)


def get_auction_id_list():
    auctions = config['auctions']
    auction_id_list = []
    for k, v in auctions.items():
        auction_id_list.append(v['id'])
    return auction_id_list


def get_auction_price_by_id(id):
    auctions = config['auctions']
    auction_info = None
    for k, v in auctions.items():
        if int(v['id']) == int(id):
            auction_info = auctions[k]
            break
    return auction_info


def is_in_groups(event: GroupMessageEvent):
    return str(event.group_id) in groups


def get_auction_msg(auction_id):
    item_info = items.get_data_by_item_id(auction_id)
    _type = item_info['type']
    msg = None
    if _type == "装备":
        if item_info['item_type'] == "防具":
            msg = get_armor_info_msg(auction_id, item_info)
        if item_info['item_type'] == '法器':
            msg = get_weapon_info_msg(auction_id, item_info)

    if _type == "技能":
        if item_info['item_type'] == '神通':
            msg = f"{item_info['level']}神通-{item_info['name']}:"
            msg += get_sec_msg(item_info)
        if item_info['item_type'] == '功法':
            msg = f"{item_info['level']}功法-"
            msg += get_main_info_msg(auction_id)[1]

    if _type == "丹药":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果:{item_info['desc']}"

    return msg
