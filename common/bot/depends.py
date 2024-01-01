from typing import Annotated

from nonebot.consts import STARTSWITH_KEY
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from ..player_controller import PlayerController, PlayerNoFoundException
from ..player_position import PlayerPositionController


def _starts_with_args() -> str:
    async def _startswith(event: Event, state: T_State, matcher: Matcher) -> str:
        start_key = state[STARTSWITH_KEY]
        msg = event.get_plaintext()
        matcher_state = matcher.state
        if len(msg) <= len(start_key):
            await matcher.finish(f"参数不正确，{matcher_state['tips']}", at_sender=True)

        return msg[len(start_key):]

    return Depends(_startswith)


def _get_player() -> PlayerController:
    async def _get_player_impl(event: Event, matcher: Matcher) -> PlayerController:

        try:
            return PlayerController(event.get_user_id())
        except PlayerNoFoundException:
            msg = "您还没有加入修仙，请输入 <我要修仙> 加入修仙游戏!"
            await matcher.finish(msg, at_sender=True)

    return Depends(_get_player_impl)


def _get_player_position() -> PlayerPositionController:
    async def _get_player_impl(event: Event, matcher: Matcher) -> PlayerPositionController:

        try:
            return PlayerPositionController(event.get_user_id(), event.channel_id)
        except PlayerNoFoundException:
            msg = "您还没有加入修仙，请输入 <我要修仙> 加入修仙游戏!"
            await matcher.finish(msg, at_sender=True)

    return Depends(_get_player_impl)


Player = Annotated[PlayerController, _get_player()]
PlayerPosition = Annotated[PlayerPositionController, _get_player_position()]
StartsWithArgs = Annotated[str, _starts_with_args()]
