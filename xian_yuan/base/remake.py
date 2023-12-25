from nonebot import on_fullmatch

from ..common.bot.depends import Player

replay = on_fullmatch("重入仙途", priority=7, block=True)

@replay.handle()
async def restart_(player: Player):
    """
    重入仙途
    """
    name, root_type = root.get_random_root()
    msg = sql_message.ramaker(name, root_type, user_id)
    sql_message.update_power2(user_id)  # 更新战力
    await xiuxian_send_message(replay, msg)
