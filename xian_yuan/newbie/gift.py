from datetime import datetime

from .newbie_data_source import NewbieGiftPlayerData, NewbieGiftConfig
from ...common.bot.depends import Player
from ...common.bot.matcher import full_match
from ...common.utils import time_diff_min

newbie_gift = full_match("新手礼包领取", "领取新手礼包！")

config = NewbieGiftConfig()


def check_gift(player_data: NewbieGiftPlayerData) -> (bool, str):
    if player_data.times >= len(config.gift_list):
        msg = '您已经领完全部新手礼包！'
        return False, msg

    diff = time_diff_min(player_data.update_at, datetime.now(), 30 * player_data.times)
    if diff > 0:
        msg = f"下个礼包还有{diff}分钟可领取！"
        return False, msg

    return True, ""


@newbie_gift.handle()
async def newbie_gift_(player: Player):
    player_data = player.get_data(NewbieGiftPlayerData)

    result, msg = check_gift(player_data)
    if not result:
        return await newbie_gift.finish(msg)

    msg_list = ["领取成功！获得物品："]
    gift = config.gift_list[player_data.times]
    msg = player.add_money(gift["money"])
    msg_list.append(msg)

    if "items" in gift.keys():
        items = gift["items"]
        for item in items:
            msg = player.backpack.add_item(item["id"], item["count"])
            msg_list.append(msg)

    player_data.times += 1

    # check next gift
    result, msg = check_gift(player_data)
    msg_list.append(msg)

    await newbie_gift.finish("\n".join(msg_list))
