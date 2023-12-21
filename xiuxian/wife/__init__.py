from nonebot import Bot, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP

from .xian_yuan_data_source import XianYuanConfig, XianYuanGameData, XianYuanPlayerData
from .xian_yuan_handle import create_xian_yuan, has_xian_yuan, format_xian_yuan_info, create_xian_yuan_mission, \
    format_xian_yuan_mission
from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import Cooldown

__xian_yuan_help__ = f"""
仙缘帮助信息:
指令：
1、仙缘查询：查询当前存在的仙缘与好感度排名。
2、仙缘任务接取：接取仙缘任务
3、仙缘任务完成：完成仙缘任务
4、表白+主角名字：对仙缘主角表白，成功可成为道侣，好感度越高概率越高。
玩法介绍：
每天定时生成一场仙缘，完成仙缘任务有机会获得剧情主角的好感，最终可表白成为道侣，一同踏上修仙之旅。
""".strip()

xian_yuan_help = on_fullmatch("仙缘帮助", priority=5, permission=GROUP, block=True)
xian_yuan_create = on_fullmatch("仙缘生成", priority=5, permission=GROUP, block=True)
xian_yuan_lookup = on_fullmatch("仙缘查询", priority=5, permission=GROUP, block=True)
xian_yuan_task_accept = on_fullmatch("仙缘任务接取", priority=5, permission=GROUP, block=True)
xian_yuan_task_complete = on_fullmatch("仙缘任务完成", priority=5, permission=GROUP, block=True)
xian_yuan_task_confession = on_startswith("表白", priority=5, permission=GROUP, block=True)

game_data = XianYuanGameData()


@xian_yuan_help.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(xian_yuan_help, __xian_yuan_help__)


@xian_yuan_create.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_create_(_: Bot, __: GroupMessageEvent):
    msg = "一阵香风拂过，一道倩影徐徐走来，发送【仙缘查询】来了解更多仙子的故事吧！"
    create_xian_yuan()
    await xiuxian_send_message(xian_yuan_create, msg)


@xian_yuan_lookup.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_lookup_(_: Bot, __: GroupMessageEvent):
    ret, msg = has_xian_yuan()
    if ret is False:
        return await xiuxian_send_message(xian_yuan_lookup, msg)
    msg = "寻找到仙缘如下：\n"
    msg += format_xian_yuan_info(game_data.girl)
    msg += "发送【仙缘任务接取】接取仙子的任务！\n"
    msg += "☆------好感排行版------☆\n"
    msg += "暂无道友得到仙子青睐！"
    await xiuxian_send_message(xian_yuan_lookup, msg)


@xian_yuan_task_accept.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_task_accept_(_: Bot, event: GroupMessageEvent):
    ret, msg = has_xian_yuan()
    if ret is False:
        return await xiuxian_send_message(xian_yuan_lookup, msg)

    user_id = event.user_id
    player_data = XianYuanPlayerData(user_id)
    msg = "道友已接取任务：\n"
    if len(player_data.current_mission.keys()) > 0:
        msg += format_xian_yuan_mission(player_data.current_mission)
        return await xiuxian_send_message(xian_yuan_lookup, msg)

    mission = create_xian_yuan_mission(player_data)
    msg += format_xian_yuan_mission(mission)
    await xiuxian_send_message(xian_yuan_task_accept, msg)


@xian_yuan_task_complete.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_task_complete_(_: Bot, event: GroupMessageEvent):
    ret, msg = has_xian_yuan()
    if ret is False:
        return await xiuxian_send_message(xian_yuan_lookup, msg)


    msg = "开发中。。。"
    await xiuxian_send_message(xian_yuan_task_complete, msg)
