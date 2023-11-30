import random
from asyncio import get_running_loop
from collections import defaultdict
from enum import IntEnum, auto
from typing import DefaultDict, Dict, Any

from nonebot import require
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Depends

from .xiuxian_config import JsonConfig

limit_all = require("nonebot_plugin_apscheduler").scheduler
limit_all_data: Dict[str, Any] = {}
limit_num = 5


@limit_all.scheduled_job('interval', hours=0, minutes=1)
def limit_all():
    # 重置消息字典
    global limit_all_data
    limit_all_data = {}
    logger.success("已重置消息字典！")


def limit_all_run(user_id: str):
    global limit_all_data
    user_id = str(user_id)
    num = None
    tip = None
    try:
        num = limit_all_data[user_id]["num"]
        tip = limit_all_data[user_id]["tip"]
    except:
        limit_all_data[user_id] = {"num": 0, "tip": False}
        num = 0
        tip = False
    num += 1
    if num > limit_num and tip == False:
        tip = True
        limit_all_data[user_id]["num"] = num
        limit_all_data[user_id]["tip"] = tip
        return True
    if num > limit_num and tip == True:
        limit_all_data[user_id]["num"] = num
        return False
    else:
        limit_all_data[user_id]["num"] = num
        return None


cd_notice = random.choice(
    [
        "慢...慢一..点❤，还有{}秒，让我再歇会！",
        "冷静一下，还有{}秒，让我再歇会！",
        "时间还没到，还有{}秒，歇会歇会~~"
    ]
)


class CooldownIsolateLevel(IntEnum):
    """
    命令冷却的隔离级别
    """
    GLOBAL = auto()  # 全局使用同一个冷却计时
    GROUP = auto()  # 群组内使用同一个冷却计时
    USER = auto()  # 每个用户同一个冷却计时
    GROUP_USER = auto()  # 群组内每个用户使用同一个冷却计时


def Cooldown(
        cd_time: float = 0.5,
        at_sender: bool = True,
        isolate_level: CooldownIsolateLevel = CooldownIsolateLevel.USER,
        parallel: int = 1,
) -> None:
    """依赖注入形式的命令冷却

    用法:
        ```python
        @matcher.handle(parameterless=[Cooldown(cooldown=11.4514, ...)])
        async def handle_command(matcher: Matcher, message: Message):
            ...
        ```

    参数:
        cd_time: 命令冷却间隔
        at_sender: 是否at
        isolate_level: 命令冷却的隔离级别, 参考 `CooldownIsolateLevel`
        parallel: 并行执行的命令数量
    """
    if not isinstance(isolate_level, CooldownIsolateLevel):
        raise ValueError(
            f"invalid isolate level: {isolate_level!r}, "
            "isolate level must use provided enumerate value."
        )
    running: DefaultDict[str, int] = defaultdict(lambda: parallel)
    time_sy: Dict[str, int] = {}

    def increase(key: str, value: int = 1):
        running[key] += value
        if running[key] >= parallel:
            del running[key]
            del time_sy[key]
        return

    async def dependency(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
        group_id = str(event.group_id)
        conf_data = JsonConfig().read_data()

        limit_type = limit_all_run(str(event.get_user_id()))
        if limit_type is True:
            await matcher.finish(message=cd_notice, reply_message=True)
        elif limit_type is False:
            await matcher.finish()
        else:
            pass

        loop = get_running_loop()

        if isolate_level is CooldownIsolateLevel.GROUP:
            key = str(
                event.group_id
                if isinstance(event, GroupMessageEvent)
                else event.user_id,
            )
        elif isolate_level is CooldownIsolateLevel.USER:
            key = str(event.user_id)
        elif isolate_level is CooldownIsolateLevel.GROUP_USER:
            key = (
                f"{event.group_id}_{event.user_id}"
                if isinstance(event, GroupMessageEvent)
                else str(event.user_id)
            )
        else:
            key = CooldownIsolateLevel.GLOBAL.name
        if group_id not in conf_data["group"]:
            if (
                    event.sender.role == "admin" or
                    event.sender.role == "owner" or
                    event.get_user_id() in bot.config.superusers
            ):
                await matcher.finish(message=MessageSegment.at(
                    event.get_user_id()) + f"本群已关闭修仙模组,请联系管理员开启,开启命令为【启用修仙功能】!")
            else:
                await matcher.finish()
        else:
            pass
        if running[key] <= 0:
            if cd_time >= 1.5:
                time = int(cd_time - (loop.time() - time_sy[key]))
                if time <= 1:
                    time = 1
                await matcher.finish(group_id=int(group_id), message=cd_notice.format(time))
            else:
                await matcher.finish()
        else:
            time_sy[key] = int(loop.time())
            running[key] -= 1
            loop.call_later(cd_time, lambda: increase(key))
        return

    return Depends(dependency)
