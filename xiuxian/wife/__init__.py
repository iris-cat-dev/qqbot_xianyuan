from nonebot import Bot, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import Cooldown

__xianyuan_help__ = f"""
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
xian_yuan_lookup = on_fullmatch("仙缘查询", priority=5, permission=GROUP, block=True)
xian_yuan_task_accept = on_fullmatch("仙缘任务接取", priority=5, permission=GROUP, block=True)
xian_yuan_task_complete = on_fullmatch("仙缘任务完成", priority=5, permission=GROUP, block=True)
xian_yuan_task_confession = on_startswith("表白", priority=5, permission=GROUP, block=True)



@xian_yuan_help.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(xian_yuan_help, __xianyuan_help__)


@xian_yuan_lookup.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_lookup_(_: Bot, event: GroupMessageEvent):
    msg = "当前还未生成仙缘"

    await xiuxian_send_message(xian_yuan_lookup, msg)


@xian_yuan_task_accept.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_task_accept_(_: Bot, event: GroupMessageEvent):
    msg = "当前还未生成仙缘"
    await xiuxian_send_message(xian_yuan_task_accept, msg)


@xian_yuan_task_complete.handle(parameterless=[Cooldown(at_sender=True)])
async def xian_yuan_task_complete_(_: Bot, event: GroupMessageEvent):
    msg = "当前还未生成仙缘"
    await xiuxian_send_message(xian_yuan_task_complete, msg)

