from nonebot import on_fullmatch, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..lay_out import Cooldown
from ..utils import number_to
from ..xiuxian2_handle import XiuxianDateManage

ranking_list = on_fullmatch("排行榜", priority=7, permission=GROUP, block=True)
ranking_list_ls = on_fullmatch("灵石排行榜", priority=7, permission=GROUP, block=True)
ranking_list_zl = on_fullmatch("战力排行榜", priority=7, permission=GROUP, block=True)
ranking_list_zm = on_fullmatch("宗门排行榜", priority=7, permission=GROUP, block=True)

sql_message = XiuxianDateManage()


@ranking_list.handle(parameterless=[Cooldown(at_sender=True)])
async def ranking_list_(_: Bot, __: GroupMessageEvent):
    """
    境界排行榜
    """
    p_rank = sql_message.realm_top()
    msg = f"✨位面境界排行榜TOP10✨\n"
    num = 0
    for i in p_rank:
        num += 1
        msg += f"第{num}位 {i[0]} {i[1]},修为{number_to(i[2])}\n"
    await xiuxian_send_message(ranking_list, msg)


@ranking_list_ls.handle(parameterless=[Cooldown(at_sender=True)])
async def ranking_list_ls_(_: Bot, __: GroupMessageEvent):
    a_rank = sql_message.stone_top()
    msg = f"✨位面灵石排行榜TOP10✨\n"
    num = 0
    for i in a_rank:
        num += 1
        msg += f"第{num}位  {i[0]}  灵石：{number_to(i[1])}枚\n"
    await xiuxian_send_message(ranking_list_ls, msg)


@ranking_list_zl.handle(parameterless=[Cooldown(at_sender=True)])
async def ranking_list_zl_(_: Bot, __: GroupMessageEvent):
    c_rank = sql_message.power_top()
    msg = f"✨位面战力排行榜TOP10✨\n"
    num = 0
    for i in c_rank:
        num += 1
        msg += f"第{num}位  {i[0]}  战力：{number_to(i[1])}\n"
    await xiuxian_send_message(ranking_list_zl, msg)


@ranking_list_zm.handle(parameterless=[Cooldown(at_sender=True)])
async def ranking_list_zm_(_: Bot, __: GroupMessageEvent):
    s_rank = sql_message.scale_top()
    msg = f"✨位面宗门建设排行榜TOP10✨\n"
    num = 0
    for i in s_rank:
        num += 1
        msg += f"第{num}位  {i[1]}  建设度：{number_to(i[2])}\n"
        if num == 10:
            break
    await xiuxian_send_message(ranking_list_zm, msg)
