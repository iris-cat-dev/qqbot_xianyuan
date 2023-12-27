from nonebot import on_fullmatch, on_startswith


def full_match(msg: str, tips: str):
    return on_fullmatch(msg, priority=5, block=True, state={"tips": tips})


def starts_with(msg: str, tips: str):
    return on_startswith(msg, priority=5, block=True, state={"tips": tips})
