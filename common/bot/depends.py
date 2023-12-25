from typing import Annotated

from nonebot.consts import STARTSWITH_KEY
from nonebot.internal.adapter import Event
from nonebot.internal.params import Depends
from nonebot.typing import T_State

from ..game_data import GlobalGameData
from ..player_controller import PlayerController


def _starts_with_args() -> str:
    def _startswith(event: Event, state: T_State) -> str:
        start_key = state[STARTSWITH_KEY]
        msg = event.get_plaintext()
        return msg[len(start_key):]

    return Depends(_startswith)


def _get_player() -> PlayerController:
    def _get_player_impl(event: Event) -> PlayerController:
        return PlayerController(event.get_user_id())

    return Depends(_get_player_impl)


def _get_game_data() -> GlobalGameData:
    def _get_game_data_impl() -> GlobalGameData:
        return GlobalGameData()

    return Depends(_get_game_data_impl)


Player = Annotated[PlayerController, _get_player()]
GameData = Annotated[GlobalGameData, _get_game_data()]
StartsWithArgs: Annotated[str, _starts_with_args()]
