import os
import re
from datetime import datetime
from typing import Dict

from nonebot import require, on_command, on_startswith, on_fullmatch
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
)
from nonebot.log import logger

from .reward_data_source import PLAYERSDATA
from .work_handle import workhandle
from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..item_json import Items
from ..lay_out import Cooldown
from ..utils import check_user, check_user_type
from ..xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import USERRANK, XiuConfig

# 定时任务
resetrefreshnum = require("nonebot_plugin_apscheduler").scheduler

work = {}  # 悬赏令信息记录
refreshnum: Dict[str, int] = {}  # 用户悬赏令刷新次数记录
sql_message = XiuxianDateManage()  # sql类
items = Items()
lscost = 500000  # 刷新灵石消耗
count = 3  # TODO:免费次数 保存


class do_is_work:
    def __init__(self, user_id):
        self.user = user_id
        self.time = 0
        self.msg = 0
        self.world = []


# 重置悬赏令刷新次数
@resetrefreshnum.scheduled_job("cron", hour=0, minute=0)
async def resetrefreshnum_():
    global refreshnum
    refreshnum = {}
    logger.info("用户悬赏令刷新次数重置成功")


work_lookup = on_fullmatch("悬赏令", priority=15, block=True)
work_help = on_fullmatch("悬赏令帮助", priority=15, block=True)
work_flash = on_fullmatch("悬赏令刷新", priority=15, block=True)
work_accept = on_startswith("悬赏令接取", priority=15, block=True)
work_complete = on_fullmatch("悬赏令结算", priority=15, block=True)
work_stop = on_fullmatch("悬赏令终止", priority=15, block=True)
last_work = on_command("最后的悬赏令", priority=15, block=True)

__work_help__ = f"""
悬赏令帮助信息:
指令：
1、悬赏令:获取对应实力的悬赏令
2、悬赏令刷新:刷新当前悬赏令,每日免费{count}次
3、悬赏令终止:终止当前悬赏令任务
4、悬赏令结算:结算悬赏奖励
5、悬赏令接取+编号：接取对应的悬赏令
6、最后的悬赏令:用于接了悬赏令却境界突破导致卡住的道友使用
""".strip()


@work_help.handle(parameterless=[Cooldown(at_sender=True)])
async def work_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(work_help, message=__work_help__)


@last_work.handle(parameterless=[Cooldown(cd_time=1.3, at_sender=True), check_player()])
async def last_work_(_: Bot, event: GroupMessageEvent):
    isUser, user_info, msg = check_user(event)

    user_id = user_info.user_id
    user_level = user_info.level
    is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
    if (is_type and USERRANK[user_info.level] <= 22) or (
            is_type and user_info.exp >= sql_message.get_level_power("虚道境圆满")) or (
            is_type and int(user_info.exp) >= int(
        OtherSet().set_closing_type(user_level)) * XiuConfig().closing_exp_upper_limit
    ):
        user_cd_message = sql_message.get_user_cd(user_id)
        work_time = datetime.strptime(
            user_cd_message.create_time, "%Y-%m-%d %H:%M:%S.%f"
        )
        exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
        time2 = workhandle().do_work(
            # key=1, name=user_cd_message.scheduled_time  修改点
            key=1, name=user_cd_message.scheduled_time, level=user_level, exp=user_info.exp,
            user_id=user_info.user_id
        )
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd_message.scheduled_time}】，预计{time2 - exp_time}分钟后可结束"
            await xiuxian_send_message(last_work, message=msg)
        else:
            msg, give_stone, s_o_f, item_id, big_suc = workhandle().do_work(
                2,
                work_list=user_cd_message.scheduled_time,
                level=user_level,
                exp=user_info.exp,
                user_id=user_info.user_id
            )
            item_flag = False
            item_msg = None
            item_info = None
            if item_id != 0:
                item_flag = True
                item_info = items.get_data_by_item_id(item_id)
                item_msg = f"{item_info['level']}:{item_info['name']}"
            if big_suc:  # 大成功
                sql_message.update_ls(user_id, give_stone * 2, 1)
                sql_message.do_work(user_id, 0)
                msg = f"悬赏令结算，{msg}获得报酬{give_stone * 2}枚灵石"
                # todo 战利品结算sql
                if item_flag:
                    sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                    msg += f"，额外获得奖励：{item_msg}!"
                else:
                    msg += "!"
                await xiuxian_send_message(last_work, message=msg)

            else:
                sql_message.update_ls(user_id, give_stone, 1)
                sql_message.do_work(user_id, 0)
                msg = f"悬赏令结算，{msg}获得报酬{give_stone}枚灵石"
                if s_o_f:  # 普通成功
                    if item_flag:
                        sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                        msg += f"，额外获得奖励：{item_msg}!"
                    else:
                        msg += "!"
                    await xiuxian_send_message(last_work, message=msg)

                else:  # 失败
                    msg += "!"
                    await xiuxian_send_message(last_work, message=msg)
    else:
        msg = "不满足使用条件！"
        await xiuxian_send_message(last_work, message=msg)


@work_flash.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_flash_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()
    _, user_info, msg = check_user(event)

    stone_use = 0  # 悬赏令刷新提示是否扣灵石
    try:
        usernums = refreshnum[user_id]
    except KeyError:
        usernums = 0

    free_num = count - usernums - 1
    if free_num < 0:
        free_num = 0
        if int(user_info.stone) < lscost:
            msg = f"道友的灵石不足以刷新，下次刷新消耗灵石：{lscost}枚"
            await xiuxian_send_message(work_flash, message=msg)

        else:
            sql_message.update_ls(user_id, lscost, 2)
            stone_use = 1

    work_msg = workhandle().do_work(0, level=user_info.level, exp=user_info.exp, user_id=user_id)
    n = 1
    work_list = []
    work_msg_f = f"☆------道友的个人悬赏令------☆\n"
    for i in work_msg:
        work_list.append([i[0], i[3]])
        work_msg_f += f"{n}、{get_work_msg(i)}"
        n += 1

    work_msg_f += f"(悬赏令每日免费刷新次数：{count}，超过{count}次后，下次刷新消耗灵石{lscost},今日可免费刷新次数：{free_num}次)"
    if int(stone_use) == 1:
        work_msg_f += f"\n道友消耗灵石{lscost}枚，成功刷新悬赏令"

    work[user_id] = do_is_work(user_id)
    work[user_id].msg = work_msg_f
    work[user_id].world = work_list
    refreshnum[user_id] = usernums + 1
    msg = work[user_id].msg

    await xiuxian_send_message(work_flash, message=msg)


@work_accept.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_accept_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()
    message = str(event.message)
    _, user_info, msg = check_user(event)
    num = re.findall("\d+", message)[0]  # boss编号
    max_level = "真仙境初期"

    if USERRANK[user_info.level] <= 22:
        msg = f"道友的境界已过创业初期，悬赏令已经不能满足道友了！"
        await xiuxian_send_message(work_accept, message=msg)

    if user_info.exp >= sql_message.get_level_power(max_level):
        msg = f"道友的实力已过创业初期，悬赏令已经不能满足道友了！"
        await xiuxian_send_message(work_accept, message=msg)

    if int(user_info.exp) >= int(OtherSet().set_closing_type(max_level)) * XiuConfig().closing_exp_upper_limit:
        # 获取下个境界需要的修为 * 1.5为闭关上限
        msg = f"道友的修为已经到达上限，悬赏令已无法在获得经验！"
        await xiuxian_send_message(work_accept, message=msg)

    is_type, msg = check_user_type(user_id, 0)  # 需要无状态的用户
    if is_type:  # 接取逻辑
        if num is None or str(num) not in ['1', '2', '3']:
            msg = '请输入正确的任务序号'
            await xiuxian_send_message(work_accept, message=msg)

        work_num = 1
        try:
            if work[user_id]:
                work_num = int(num)  # 任务序号
            try:
                get_work = work[user_id].world[work_num - 1]
                sql_message.do_work(user_id, 2, get_work[0])
                del work[user_id]
                msg = f"接取任务【{get_work[0]}】成功"

            except IndexError:
                msg = "没有这样的任务"

        except KeyError:
            msg = "没有查到你的悬赏令信息呢，请刷新！"

    await xiuxian_send_message(work_accept, message=msg)


@work_complete.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_complete_(_: Bot, event: GroupMessageEvent):
    _, user_info, msg = check_user(event)
    user_id = user_info.user_id

    is_flash, msg = check_flash(user_id)
    if is_flash:
        await xiuxian_send_message(work_complete, message=msg)


    user_level = user_info.level
    is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
    if is_type:
        user_cd_message = sql_message.get_user_cd(user_id)
        work_time = datetime.strptime(
            user_cd_message.create_time, "%Y-%m-%d %H:%M:%S.%f"
        )
        exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
        time2 = workhandle().do_work(
            # key=1, name=user_cd_message.scheduled_time  修改点
            key=1, name=user_cd_message.scheduled_time, level=user_level, exp=user_info.exp,
            user_id=user_info.user_id
        )
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd_message.scheduled_time}】，预计{time2 - exp_time}分钟后可结束"
        else:
            msg, give_exp, s_o_f, item_id, big_suc = workhandle().do_work(2,
                                                                          work_list=user_cd_message.scheduled_time,
                                                                          level=user_level,
                                                                          exp=user_info.exp,
                                                                          user_id=user_info.user_id)
            item_flag = False
            item_info = None
            item_msg = None
            if item_id != 0:
                item_flag = True
                item_info = items.get_data_by_item_id(item_id)
                item_msg = f"{item_info['level']}:{item_info['name']}"
            if big_suc:  # 大成功
                sql_message.update_exp(user_id, give_exp * 2)
                sql_message.do_work(user_id, 0)
                msg = f"悬赏令结算，{msg}增加修为{give_exp * 2}"
                # todo 战利品结算sql
                if item_flag:
                    sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                    msg += f"，额外获得奖励：{item_msg}!"
                else:
                    msg += "!"
            else:
                sql_message.update_exp(user_id, give_exp)
                sql_message.do_work(user_id, 0)
                msg = f"悬赏令结算，{msg}增加修为{give_exp}"
                if s_o_f:  # 普通成功
                    if item_flag:
                        sql_message.send_back(user_id, item_id, item_info['name'], item_info['type'], 1)
                        msg += f"，额外获得奖励：{item_msg}!"
                    else:
                        msg += "!"
                else:  # 失败
                    msg += "!"

    else:
        msg = "没有查到你的悬赏令信息呢，请刷新！"
    await xiuxian_send_message(work_complete, message=msg)


@work_stop.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_stop_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()

    is_flash, msg = check_flash(user_id)
    if is_flash:
        await xiuxian_send_message(work_stop, message=msg)

    is_type, msg = check_user_type(user_id, 2)  # 需要在悬赏令中的用户
    if is_type:
        stone = 4000000
        sql_message.update_ls(user_id, stone, 2)
        sql_message.do_work(user_id, 0)
        msg = f"道友不讲诚信，被打了一顿，灵石减少{stone},悬赏令已终止！"
        await xiuxian_send_message(work_stop, message=msg)

    else:
        msg = "没有查到你的悬赏令信息呢，请刷新！"
        await xiuxian_send_message(work_stop, message=msg)


@work_lookup.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_lookup_(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    user_cd_message = sql_message.get_user_cd(user_id)

    is_flash, msg = check_flash(user_id)
    if is_flash:
        await xiuxian_send_message(work_lookup, message=msg)

    if (user_cd_message.scheduled_time is None) or (user_cd_message.type == 0):
        try:
            msg = work[user_id].msg
        except KeyError:
            msg = "你的悬赏令已过期，请刷新！"

    elif user_cd_message.type == 2:
        work_time = datetime.strptime(
            user_cd_message.create_time, "%Y-%m-%d %H:%M:%S.%f"
        )
        exp_time = (datetime.now() - work_time).seconds // 60  # 时长计算
        time2 = workhandle().do_work(key=1, name=user_cd_message.scheduled_time, user_id=user_id)
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd_message.scheduled_time}】，预计{time2 - exp_time}分钟后可结束"
        else:
            msg = f"进行中的悬赏令【{user_cd_message.scheduled_time}】，已结束，请输入【悬赏令结算】结算任务信息！"
    else:
        _, msg = check_user_type(user_id, 2)

    await xiuxian_send_message(work_lookup, message=msg)


def get_work_msg(work_):
    msg = f"{work_[0]},完成机率{work_[1]},基础报酬{work_[2]}修为,预计需{work_[3]}分钟{work_[4]}\n"
    return msg


def check_flash(user_id):
    msg = ""
    result = False
    user_cd_message = sql_message.get_user_cd(user_id)
    if (not os.path.exists(PLAYERSDATA / str(user_id) / "workinfo.json")
            and user_cd_message.type == 2):
        sql_message.do_work(user_id, 0)
        msg = f"悬赏令已更新，已重置道友的状态！"
        result = True
    return result, msg
