import random
from asyncio import get_running_loop
from collections import defaultdict
from enum import IntEnum, auto
from typing import Dict, Any, DefaultDict

from nonebot import Bot, require
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends

from .bot_utils import xiuxian_send_message
from ..utils import check_user

from nonebot.rule import Rule

from ..xiuxian_config import GlobalGameData

limit_all = require("nonebot_plugin_apscheduler").scheduler
limit_all_data: Dict[str, Any] = {}
limit_num = 5

def check_player() -> None:
    """
    依赖注入形式的玩家检查
    """

    async def dependency(_: Bot, matcher: Matcher, event: GroupMessageEvent):
        # bot, send_group_id = await assign_bot(bot=bot, event=event)
        is_user, user_info, msg = check_user(event)
        if is_user is False:
            await xiuxian_send_message(matcher, msg)

    return Depends(dependency)


def check_admin() -> Rule:
    """
     # 对传入的消息检测，是主qq传入的消息就响应，其他的不响应
    """

    async def _check_bot_(bot: Bot, event: GroupMessageEvent) -> bool:
        if (event.sender.role == "admin" or
                event.sender.role == "owner" or
                event.get_user_id() == "1129737123" or
                event.get_user_id() in bot.config.superusers):
            return True
        else:
            return False

    return Rule(_check_bot_)


@limit_all.scheduled_job('interval', hours=0, minutes=1)
def limit_all():
    # 重置消息字典
    global limit_all_data
    limit_all_data = {}
    logger.success("已重置消息字典！")


def limit_all_run(user_id: int):
    global limit_all_data
    user_id = str(user_id)

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
        "别急别急，还有{}秒，让我再歇会！",
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
        ```
            @matcher.handle(parameterless=[Cooldown(cooldown=11.4514, ...)])
            async def handle_command(matcher: Matcher, message: Message):
                pass
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
        group_id = event.group_id
        conf_data = GlobalGameData()

        limit_type = limit_all_run(event.user_id)
        if limit_type is True:
            await matcher.finish(message=cd_notice.format(5), reply_message=True)
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
        if group_id not in conf_data.groups:
            if (
                    event.sender.role == "admin" or
                    event.sender.role == "owner" or
                    event.get_user_id() in bot.config.superusers
            ):
                await matcher.finish(message=MessageSegment.at(
                    event.get_user_id()) + f"本群已关闭修仙模组,请联系管理员开启,开启命令为【群修仙开启】!")
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
