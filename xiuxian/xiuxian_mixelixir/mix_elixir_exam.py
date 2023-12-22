import re

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent

from .mix_elixir_data_source import MixElixirExamPlayerData
from .mixelixir_handle import get_mix_elixir_exam_problem, format_problem, check_mix_elixir_exam_problem, \
    mix_elixir_exam_reward_obtained
from ..common.bot_utils import xiuxian_send_message, get_input_cmd
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import Cooldown, check_player

mix_elixir_exam_accept = on_fullmatch("炼丹考核开始", priority=6, permission=GROUP, block=True)
mix_elixir_exam_answer = on_startswith("炼丹考核解答", priority=6, permission=GROUP, block=True)

sql_manager = XiuxianSqlManager()


@mix_elixir_exam_accept.handle(parameterless=[Cooldown(), check_player()])
async def _mix_elixir(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    player_data = MixElixirExamPlayerData(user_id)
    if len(player_data.current_problem.keys()) > 0:
        problem = player_data.current_problem
        msg = "道友有未解答的题目，现有药材如下：\n"
    else:
        msg = "道友请听题，现有药材如下：\n"
        player_data.current_problem = get_mix_elixir_exam_problem()
        player_data.save()
        problem = player_data.current_problem

    msg += format_problem(problem)
    await xiuxian_send_message(mix_elixir_exam_accept, msg)


@mix_elixir_exam_answer.handle(parameterless=[Cooldown(), check_player()])
async def _mix_elixir(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    mode, msg = get_input_cmd(event, 6)
    pattern = r"([\u4e00-\u9fa5]+)(\d+)([\u4e00-\u9fa5]+)(\d+)([\u4e00-\u9fa5]+)(\d+)"
    matched = re.search(pattern, mode)
    msg = f"请输入正确的配方！例如：【炼丹考核解答+恒心草1红绫草2罗犀草3】"
    if matched is None:
        return await xiuxian_send_message(mix_elixir_exam_answer, msg)

    args = matched.groups()
    if len(args) < 6:
        return await xiuxian_send_message(mix_elixir_exam_answer, msg)

    player_data = MixElixirExamPlayerData(user_id)
    problem = player_data.current_problem
    if check_mix_elixir_exam_problem(args, problem):
        elixir = mix_elixir_exam_reward_obtained(problem)
        sql_manager.insert_backpack(user_id, elixir["id"], elixir['name'], "药材", 1)
        msg = f"恭喜道友回答正确！炼丹考核积分 +10，获得 【{elixir['name']}】x1"
        player_data.current_problem = {}
        player_data.point += 10
        player_data.save()
    else:
        msg = "回答错误！请道友深思熟虑后再回答！"
    await xiuxian_send_message(mix_elixir_exam_answer, msg)
