import random

from ...common.bot.depends import Player, GameData
from ...common.bot.matcher import full_match

newbie_gift = full_match("新手礼包领取", "领取新手礼包！")


@newbie_gift.handle()
async def newbie_gift_(player: Player, game_data: GameData):
    if player.is_sign_in:
        msg = '贪心的人是不会有好运的！'
    else:
        stone = random.randint(game_data.sign_in_stone_lower_limit, game_data.sign_in_stone_upper_limit)
        stone = player.l * game_data.sign_in_stone_lower_limit + stone

        player.is_sign_in = True
        player.money += stone
        player.save()
        msg = f'签到成功，获取{stone}枚灵石!'

    await newbie_gift.finish(newbie_gift, msg)
