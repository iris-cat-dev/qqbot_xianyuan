import functools
import threading
from typing import TypeVar, Callable

from nonebot import get_driver

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
    def getinstance(user_id, *args, **kwargs) -> T:
        with lock:
            if user_id not in instances:
                instances[user_id] = cls(user_id, *args, **kwargs)
        return instances[user_id]

    return getinstance

