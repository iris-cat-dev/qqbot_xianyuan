from nonebot import Bot, get_driver
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.message import event_preprocessor


from typing import TypeVar, Callable

DRIVER = get_driver()

T = TypeVar('T')

def singleton(cls: Callable[..., T]) -> Callable[..., T]:
    instances = {}

    def getinstance(*args, **kwargs) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getinstance


@event_preprocessor
async def do_something(bot: Bot, event: GroupMessageEvent):
    pass
