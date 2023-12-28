from datetime import datetime

from .newbie_data_source import NewbieGiftPlayerData, NewbieGiftConfig
from ...common.bot.depends import Player
from ...common.bot.matcher import full_match

newbie_gift = full_match("新手礼包领取", "领取新手礼包！")


@newbie_gift.handle()
async def newbie_gift_(player: Player):
    player_data = player.get_data(NewbieGiftPlayerData)
    config = NewbieGiftConfig()

    if player_data.times > len(config.gift_list):
        msg = '您已经领完全部新手礼包！'
        return await newbie_gift.finish(msg)

    if player_data.update_at > datetime.now():
        msg = f"道友莫急，礼包还有{0}分钟可领取！"
        return await newbie_gift.finish(msg)

    msg = ["领取成功！获得物品："]
    gift = config.gift_list[player_data.times]
    msg += player.add_money(gift["money"])

    items = gift["items"]
    for item in items:
        msg += player.backpack.add_item(item["id"], item["count"])

    player_data.times += 1
    player.save()

    await newbie_gift.finish("\n".join(msg))
