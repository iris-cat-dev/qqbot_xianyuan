from ..common import player_singleton
from ..common.game_data_manager import PlayerData


@player_singleton
class MixElixirExamPlayerData(PlayerData):

    def __init__(self, user_id: int):
        self.current_problem = {}
        self.point = 0
        super().__init__(user_id, "mix_elixir_exam")
