from ...common.bot.depends import Player, StartsWithArgs
from ...common.bot.matcher import full_match, starts_with
from ...common.player_controller import get_player, create_player

join_xiuxian = full_match("我要修仙", "加入修仙游戏")
rename = starts_with("改名", "< 改名+道号 > 修改道号")


@join_xiuxian.handle()
async def join_xiuxian_(event):
    """
    加入修仙
    """
    uid = event.get_user_id()
    name = event.member.nick
    if get_player(uid) is not None:
        msg = "道友已经加入修仙世界！"
        return await join_xiuxian.finish(msg)

    player = create_player(uid, name)
    msg = ("必死之境逢仙缘，仙路崎岖意更坚！\n"
           "欢迎来到修仙世界！\n"
           f"当前境界: 【{player.level}】 \n"
           f"灵根: 【{player.root}】 \n"
           f"请尽快获得修仙功法，踏入修仙世界的大门！\n"
           f"输入 < 修仙帮助 > 更多获取仙界信息。\n"
           f"输入 < 新手礼包领取 > 领取新手福利！")

    return await join_xiuxian.finish(msg)


@rename.handle()
async def rename_(player: Player, name: StartsWithArgs):
    """
    改名
    """
    if len(name) > 10:
        msg = "道号太长会遭天谴的，请修改后重试！"
        return await rename.reject(msg)

    player.name = name
    player.save()

    msg = f"您的道号已修改为：{player.name}"
    await rename.finish(msg)
