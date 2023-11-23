from nonebot import Bot
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends

from .bot_utils import xiuxian_send_message
from ..lay_out import assign_bot
from ..utils import check_user


def check_player() -> None:
    """
    依赖注入形式的玩家检查
    """

    async def dependency(bot: Bot, matcher: Matcher, event: GroupMessageEvent):
        bot, send_group_id = await assign_bot(bot=bot, event=event)
        is_user, user_info, msg = check_user(event)
        if is_user is False:
            await xiuxian_send_message(matcher, msg)

    return Depends(dependency)
