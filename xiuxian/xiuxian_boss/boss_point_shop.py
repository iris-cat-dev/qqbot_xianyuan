from nonebot import Bot, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP

from .boss_handle import check_group_open_boss
from .boss_data_source import BossPointShopConfig, BossPlayerData
from ..common.bot_utils import xiuxian_send_message, get_input_number
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.item_json import Items
from ..common.param_checker import check_player, Cooldown

boss_point_shop_list = on_fullmatch("积分查询", priority=10, permission=GROUP, block=True)
boss_point_shop_use = on_startswith("积分兑换", priority=6, permission=GROUP, block=True)
boss_point_shop_lookup = on_fullmatch("我的积分", priority=10, permission=GROUP, block=True)

sql_manager = XiuxianSqlManager()
shop_config = BossPointShopConfig()


@boss_point_shop_lookup.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_integral_lookup_info_(_: Bot, event: GroupMessageEvent):
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_point_shop_lookup, msg)

    point = BossPlayerData(event.user_id).point
    msg = f"道友目前拥有的讨伐邪魔积分：{point}点"
    await xiuxian_send_message(boss_point_shop_lookup, message=msg)


@boss_point_shop_list.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_integral_info_(_: Bot, event: GroupMessageEvent):
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_point_shop_lookup, msg)

    user_point = BossPlayerData(event.user_id).point
    boss_integral_shop = shop_config.goods_list
    l_msg = [f"道友目前拥有的讨伐邪魔积分：{user_point}点"]
    i = 1
    for v in boss_integral_shop:
        msg = f"编号:{i}\n"
        msg += f"描述：{v['desc']}\n"
        msg += f"所需积分：{v['cost']}点"
        l_msg.append(msg)
        i += 1

    msg = ""
    for item in l_msg:
        msg += item + "\n"
    await xiuxian_send_message(boss_point_shop_list, message=msg)


@boss_point_shop_use.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_integral_use_(_: Bot, event: GroupMessageEvent):
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_point_shop_use, msg)

    user_id = event.user_id
    shop_num, msg = get_input_number(event)
    if not shop_num:
        msg += f'请输入【积分购买+编号】！'
        return await xiuxian_send_message(boss_point_shop_use, message=msg)

    boss_integral_shop = shop_config.goods_list
    if shop_num < 0 or shop_num >= len(boss_integral_shop):
        msg = f"该编号不在商品列表内哦，请检查后再兑换"
        return await xiuxian_send_message(boss_point_shop_use, message=msg)

    goods = boss_integral_shop[shop_num - 1]
    cost = goods["cost"]
    shop_id = goods["id"]

    player_data = BossPlayerData(event.user_id)
    user_point = player_data.point
    if user_point < cost:
        msg = f"道友的世界积分不满足兑换条件呢"
        await xiuxian_send_message(boss_point_shop_use, message=msg)

    else:
        player_data.point -= cost
        player_data.save()

        item_info = Items().get_data_by_item_id(shop_id)
        sql_manager.insert_backpack(user_id, shop_id, item_info['name'], item_info['type'], 1)
        msg = f"道友成功兑换获得：{item_info['name']}"
        await xiuxian_send_message(boss_point_shop_use, message=msg)
