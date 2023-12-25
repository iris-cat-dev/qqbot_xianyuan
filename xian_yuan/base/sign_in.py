from nonebot import on_fullmatch

sign_in = on_fullmatch("修仙签到", priority=13, block=True)


@sign_in.handle()
async def sign_in_():
    """
    修仙签到
    """
    user_info = sql_manager.get_user_info(event.get_user_id())
    stone = random.randint(game_config.sign_in_stone_lower_limit, game_config.sign_in_stone_upper_limit)
    level_num = Rank().to_level_index(user_info.level)
    stone = level_num * game_config.sign_in_stone_lower_limit + stone
    sql_manager.add_money(user_info.user_id, stone)
    sql_manager.set_sign_in(user_info.user_id, 1)
    if user_info.is_sign == 1:
        msg = '贪心的人是不会有好运的！'
    else:
        msg = f'签到成功，获取{stone}枚灵石!'
    await xiuxian_send_message(sign_in, msg)
