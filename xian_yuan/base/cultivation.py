from datetime import datetime

from ...common.bot.depends import Player, StartsWithArgs
from ...common.bot.matcher import full_match, starts_with

in_closing = full_match("闭关", "")
out_closing = full_match("出关", "")
enter_cul = full_match("修炼", "")
enter_heal = full_match("疗伤", "")
exit_state = starts_with("结束", "")


@in_closing.handle()
async def in_closing_(player: Player):
    """
    闭关
    """
    result, msg = player.state.update("闭关")
    await in_closing.finish(msg)


@out_closing.handle()
async def out_closing_(player: Player):
    """
    出关
    """
    result, msg = player.state.update("出关")
    await out_closing.finish(msg)


@enter_cul.handle()
async def enter_cul_(player: Player):
    result, msg = player.state.update("修炼")
    await enter_cul.finish(msg)


@enter_heal.handle()
async def enter_heal_(player: Player):
    result, msg = player.state.update("疗伤")
    await enter_heal.finish(msg)


@exit_state.handle()
async def exit_state_(player: Player, state: StartsWithArgs):
    result, msg = player.state.update("结束" + state)
    await exit_state.finish(msg)


@out_closing.handle()
async def out_closing_(player: Player):
    """
    出关
    """
    user_info = sql_manager.get_user_info(event.user_id)
    user_id = user_info.user_id
    user_level = user_info.level
    user_exp = user_info.exp

    rank_speed = rank.get_rank_speed(user_level)
    hp_speed = game_config.closing_hp * rank_speed
    mp_speed = game_config.closing_mp * rank_speed
    max_exp = rank.get_next_rank_exp(user_level) * game_config.closing_exp_upper_limit  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - user_exp
    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    now_time = datetime.now()
    user_cd_info = sql_manager.get_user_cd(user_id)
    is_type, msg = check_user_state(user_id, 1)  # 用户状态为 1
    if not is_type:
        return await xiuxian_send_message(out_closing, message=msg)

    in_closing_time = datetime.strptime(user_cd_info.create_time, "%Y-%m-%d %H:%M:%S.%f")  # 进入闭关的时间
    exp_time = round(date_diff(now_time, in_closing_time) / 60, 2)  # 闭关时长计算(分钟) = second // 60
    cultivation_rate_info = get_cultivation_rate(event.user_id)
    exp = int(exp_time * game_config.closing_exp * (cultivation_rate_info["total"]))

    msg = f"闭关结束，共闭关{exp_time}分钟"
    if str(event.message) == "灵石出关":
        user_stone = user_info.stone  # 用户灵石数
        if exp <= user_stone:
            cost_stone = exp
            exp = exp * 2
        else:
            exp = exp + user_stone
            cost_stone = user_stone
        sql_manager.sub_money(user_id, cost_stone)
        msg += f"，消耗灵石{cost_stone}枚"

    result_msg = send_hp_mp(user_info, int(exp * hp_speed), int(exp * mp_speed))  # 先回血
    sql_manager.set_user_state(user_id, 0)
    if exp >= user_get_exp_max:
        # 用户获取的修为到达上限
        exp = user_get_exp_max
        msg += ",本次闭关到达上限"
    sql_manager.add_exp(user_id, exp)
    msg += f"\n增加修为：{exp} {result_msg}"
    await xiuxian_send_message(out_closing, message=msg)


def send_hp_mp(user_info, hp, mp):
    max_hp = get_total_hp(user_info.user_id)
    max_mp = get_total_mp(user_info.user_id)

    msg = ""
    if user_info.hp < max_hp:
        if user_info.hp + hp < max_hp:
            new_hp = user_info.hp + hp
            msg = f"\n回复气血：{hp}\n目前气血：{number_to(new_hp)}/{number_to(max_hp)}"
        else:
            new_hp = max_hp
            msg = f"\n气血已回满!\n目前气血：{number_to(max_hp)}"
    else:
        new_hp = user_info.hp

    if user_info.mp < max_mp:
        if user_info.mp + mp < max_mp:
            new_mp = user_info.mp + mp
            msg += f"\n回复真元：{mp}\n目前真元：{number_to(new_mp)}/{number_to(max_mp)}"
        else:
            new_mp = max_mp
            msg += f"\n真元已回满!\n目前真元：{number_to(max_mp)}"
    else:
        new_mp = user_info.mp

    mew_attack = user_info.exp // 10
    sql_manager.update_user_attribute(user_info.user_id, new_hp, new_mp, mew_attack)
    return msg
