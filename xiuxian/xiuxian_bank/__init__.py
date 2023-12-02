import json
import os
import re
from datetime import datetime
from pathlib import Path

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger

from .bankconfig import get_config
from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player,Cooldown
from ..common.utils import check_user
from ..common.xiuxian2_handle import XiuxianDateManage

config = get_config()
BANKLEVEL = config["BANKLEVEL"]
sql_message = XiuxianDateManage()
PLAYERSDATA = Path() / "data" / "xiuxian" / "players"

bank_put = on_startswith("灵庄存灵石", priority=5, block=True)
bank_get = on_startswith("灵庄取灵石", priority=5, block=True)
bank_update = on_fullmatch("灵庄升级会员", priority=5, block=True)
bank_info = on_fullmatch("灵庄信息", priority=5, block=True)
bank_settlement = on_fullmatch("灵庄结算", priority=5, block=True)
bank_help = on_fullmatch("灵庄帮助", priority=5, block=True)

__bank_help__ = f"""
灵庄帮助信息:
指令：
1、灵庄存灵石+数量:指令后加存入的金额,获取利息
2、灵庄取灵石+数量:指令后加取出的金额,会先结算利息,再取出灵石
3、灵庄升级会员:灵庄利息倍率与灵庄会员等级有关,升级会员会提升利息倍率
4、灵庄信息:查询自己当前的灵庄信息
5、灵庄结算:结算利息
""".strip()


def get_blank_info(user_id):
    try:
        bankinfo = readf(user_id)
    except:
        bankinfo = {
            'savestone': 0,
            'savetime': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'banklevel': '1',
        }
    return bankinfo


@bank_help.handle(parameterless=[Cooldown(at_sender=True)])
async def bank_help_(_: Bot, event: GroupMessageEvent):
    """
    灵庄帮助
    """
    await xiuxian_send_message(bank_help, __bank_help__)


@bank_put.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def bank_put_(_: Bot, event: GroupMessageEvent):
    """
    灵庄存灵石+数量
    """
    user_id = event.get_user_id()
    _, user_info, _ = check_user(event)

    msg = str(event.message)
    stone_num = re.findall("\d+", msg)  # 灵石数

    bankinfo = get_blank_info(user_id)
    num = int(stone_num[0])
    if num <= 0:
        msg = f'请输入正确的金额！'
        await xiuxian_send_message(bank_put, msg)

    if int(user_info.stone) < num:
        msg = f"道友所拥有的灵石为{user_info.stone}枚，金额不足，请重新输入！"
        await xiuxian_send_message(bank_put, msg)

    max = BANKLEVEL[bankinfo['banklevel']]['savemax']
    nowmax = max - bankinfo['savestone']

    if num > nowmax:
        msg = (f"道友当前灵庄会员等级为{BANKLEVEL[bankinfo['banklevel']]['level']}，"
               f"可存储的最大灵石为{max}枚,当前已存{bankinfo['savestone']}枚灵石，可以继续存{nowmax}枚灵石！")
        await xiuxian_send_message(bank_put, msg)

    bankinfo, give_stone, timedeff = get_give_stone(bankinfo)
    userinfonowstone = int(user_info.stone) - num
    bankinfo['savestone'] += num
    sql_message.update_ls(user_id, num, 2)
    sql_message.update_ls(user_id, give_stone, 1)
    bankinfo['savetime'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    savef(user_id, bankinfo)
    msg = (f"道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚!\n道友存入灵石{num}枚，"
           f"当前所拥有灵石{userinfonowstone + give_stone}枚，灵庄存有灵石{bankinfo['savestone']}枚")

    await xiuxian_send_message(bank_put, msg)


@bank_get.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def bank_get_(_: Bot, event: GroupMessageEvent):
    """
    灵庄取灵石+数量
    """
    user_id = event.get_user_id()
    _, user_info, _ = check_user(event)

    msg = str(event.message)
    stone_num = re.findall("\d+", msg)  # 灵石数

    bankinfo = get_blank_info(user_id)
    num = int(stone_num[0])
    if num <= 0:
        msg = f'请输入正确的金额！'
        await xiuxian_send_message(bank_put, msg)

    if int(bankinfo['savestone']) < num:
        msg = f"道友当前灵庄所存有的灵石为{bankinfo['savestone']}枚，金额不足，请重新输入！"
        await xiuxian_send_message(bank_get, msg)

    # 先结算利息
    bankinfo, give_stone, timedeff = get_give_stone(bankinfo)

    userinfonowstone = int(user_info.stone) + num + give_stone
    bankinfo['savestone'] -= num
    sql_message.update_ls(user_id, num + give_stone, 1)
    savef(user_id, bankinfo)
    msg = (f"道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚!\n取出灵石{num}枚，"
           f"当前所拥有灵石{userinfonowstone}枚，灵庄存有灵石{bankinfo['savestone']}枚!")

    await xiuxian_send_message(bank_get, msg)


@bank_update.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def bank_update_(_: Bot, event: GroupMessageEvent):
    """
    灵庄会员升级
    """
    user_id = event.get_user_id()
    _, user_info, _ = check_user(event)
    bankinfo = get_blank_info(user_id)

    userlevel = bankinfo["banklevel"]
    if userlevel == str(len(BANKLEVEL)):
        msg = f"道友已经是本灵庄最大的会员啦！"
        await xiuxian_send_message(bank_update, msg)

    stonecost = BANKLEVEL[f'{int(userlevel)}']['levelup']
    if int(user_info.stone) < stonecost:
        msg = f"道友所拥有的灵石为{user_info.stone}枚，当前升级会员等级需求灵石{stonecost}枚金额不足，请重新输入！"
        await xiuxian_send_message(bank_update, msg)

    sql_message.update_ls(user_id, stonecost, 2)
    bankinfo['banklevel'] = f'{int(userlevel) + 1}'
    savef(user_id, bankinfo)
    msg = (f"道友成功升级灵庄会员等级，消耗灵石{stonecost}枚，当前为：{BANKLEVEL[f'{int(userlevel) + 1}']['level']}，"
           f"灵庄可存有灵石上限{BANKLEVEL[f'{int(userlevel) + 1}']['savemax']}枚")

    await xiuxian_send_message(bank_update, msg)


@bank_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def bank_put_(_: Bot, event: GroupMessageEvent):
    """
    灵庄信息
    """
    user_id = event.get_user_id()
    _, user_info, _ = check_user(event)
    bankinfo = get_blank_info(user_id)

    msg = f'''道友的灵庄信息：
    已存：{bankinfo['savestone']}灵石
    存入时间：{bankinfo['savetime']}
    灵庄会员等级：{BANKLEVEL[bankinfo['banklevel']]['level']}
    当前拥有灵石：{user_info.stone}
    当前等级存储灵石上限：{BANKLEVEL[bankinfo['banklevel']]['savemax']}枚
    '''
    await xiuxian_send_message(bank_info, msg)


@bank_settlement.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def bank_settlement_(_: Bot, event: GroupMessageEvent):
    """
    灵庄结算
    """
    user_id = event.get_user_id()
    bankinfo = get_blank_info(user_id)
    bankinfo, give_stone, timedeff = get_give_stone(bankinfo)
    sql_message.update_ls(user_id, give_stone, 1)
    savef(user_id, bankinfo)
    msg = f'道友本次结息时间为：{timedeff}小时，获得灵石：{give_stone}枚！'
    await xiuxian_send_message(bank_settlement, msg)


def get_give_stone(bankinfo):
    """
    获取利息：利息=give_stone,结算时间=timedeff
    """
    savetime = bankinfo['savetime']  # str
    nowtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # str
    timedeff = round((datetime.strptime(nowtime, '%Y-%m-%d %H:%M:%S') -
                      datetime.strptime(savetime, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600, 2)
    give_stone = int(bankinfo['savestone'] * timedeff * BANKLEVEL[bankinfo['banklevel']]['interest'])
    bankinfo['savetime'] = nowtime

    return bankinfo, give_stone, timedeff


def readf(user_id):
    user_id = str(user_id)
    FILEPATH = PLAYERSDATA / user_id / "bankinfo.json"
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def savef(user_id, data):
    user_id = str(user_id)
    if not os.path.exists(PLAYERSDATA / user_id):
        logger.info("用户目录不存在，创建目录")
        os.makedirs(PLAYERSDATA / user_id)
    FILEPATH = PLAYERSDATA / user_id / "bankinfo.json"
    data = json.dumps(data, ensure_ascii=False, indent=3)
    savemode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=savemode, encoding="UTF-8") as f:
        f.write(data)
        f.close()
    return True
