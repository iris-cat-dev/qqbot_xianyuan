from nonebot import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.message import event_preprocessor


@event_preprocessor
async def do_something(bot: Bot, event: GroupMessageEvent):
    pass
