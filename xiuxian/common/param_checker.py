from nonebot import Bot
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends

from .bot_utils import xiuxian_send_message
from ..lay_out import assign_bot
from ..utils import check_user

from nonebot.rule import Rule


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
