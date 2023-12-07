import functools
import threading

from nonebot import Bot, get_driver
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.message import event_preprocessor

from typing import TypeVar, Callable

DRIVER = get_driver()

T = TypeVar('T')


def singleton(cls: Callable[..., T]) -> Callable[..., T]:
    instances = {}
    lock = threading.RLock()

    def getinstance(*args, **kwargs) -> T:
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getinstance


def player_singleton(cls: Callable[..., T]) -> Callable[..., T]:
    instances = {}
    lock = threading.RLock()

    @functools.wraps(cls)
    def wrapper(user_id, *args, **kwargs) -> T:
        with lock:
            if user_id not in instances:
                instances[user_id] = cls(user_id, *args, **kwargs)
        return instances[user_id]

    return wrapper


@event_preprocessor
async def do_something(bot: Bot, event: GroupMessageEvent):
    pass
