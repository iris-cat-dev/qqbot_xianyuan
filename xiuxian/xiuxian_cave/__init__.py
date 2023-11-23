from datetime import datetime

from nonebot import on_fullmatch, on_startswith, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..lay_out import Cooldown
from ..read_buff import save_player_info, get_player_info, UserBuffDate
from ..utils import check_user
from ..xiuxian2_handle import XiuxianDateManage
from ..xiuxian_cultivation import BLESSEDSPOTCOST

blessed_spot_creat = on_fullmatch("洞天福地购买", priority=10, permission=GROUP, block=True)
blessed_spot_info = on_fullmatch("洞天福地查看", priority=11, permission=GROUP, block=True)
blessed_spot_rename = on_startswith("洞天福地改名", priority=7, permission=GROUP, block=True)
ling_tian_up = on_fullmatch("灵田开垦", priority=5, permission=GROUP, block=True)

sql_message = XiuxianDateManage()

LINGTIANCONFIG = {
    "1": {
        "level_up_cost": 3500000
    },
    "2": {
        "level_up_cost": 5000000
    },
    "3": {
        "level_up_cost": 7000000
    },
    "4": {
        "level_up_cost": 10000000
    },
    "5": {
        "level_up_cost": 15000000
    }
}


@blessed_spot_creat.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def blessed_spot_creat_(bot: Bot, event: GroupMessageEvent):
    """
    洞天福地开启
    """
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id

    if int(user_info.blessed_spot_flag) != 0:
        msg = f"道友已经拥有洞天福地了，请发送洞天福地查看吧~"
        await xiuxian_send_message(blessed_spot_creat, message=msg)

    if user_info.stone < BLESSEDSPOTCOST:
        msg = f"道友的灵石不足{BLESSEDSPOTCOST}枚，无法购买洞天福地"
        await xiuxian_send_message(blessed_spot_creat, message=msg)

    else:
        sql_message.update_ls(user_id, BLESSEDSPOTCOST, 2)
        sql_message.update_user_blessed_spot_flag(user_id)
        mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
        mix_elixir_info['收取时间'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
        msg = f"恭喜道友拥有了自己的洞天福地，请收集聚灵旗来提升洞天福地的等级吧~"
        await xiuxian_send_message(blessed_spot_creat, message=msg)


@blessed_spot_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def blessed_spot_info_(_: Bot, event: GroupMessageEvent):
    """洞天福地信息"""
    _, user_info, _ = check_user(event)

    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(blessed_spot_info, message=msg)

    msg = f'\n道友的洞天福地:\n'
    user_buff_data = UserBuffDate(user_id).BuffInfo
    if user_info.blessed_spot_name == 0:
        blessed_spot_name = "尚未命名"
    else:
        blessed_spot_name = user_info.blessed_spot_name
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    msg += f"名字：{blessed_spot_name}\n"
    msg += f"修炼速度：增加{int(user_buff_data.blessed_spot) * 100}%\n"
    msg += f"灵田数量：{mix_elixir_info['灵田数量']}"
    await xiuxian_send_message(blessed_spot_info, message=msg)


@ling_tian_up.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def ling_tian_up_(bot: Bot, event: GroupMessageEvent):
    """
    洞天福地灵田升级
    """
    _, user_info, _ = check_user(event)

    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(ling_tian_up, message=msg)

    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_num = mix_elixir_info['灵田数量']
    if now_num == len(LINGTIANCONFIG) + 1:
        msg = f"道友的灵田已全部开垦完毕，无法继续开垦了！"
    else:
        cost = LINGTIANCONFIG[str(now_num)]['level_up_cost']
        if int(user_info.stone) < cost:
            msg = f"本次开垦需要灵石：{cost}，道友的灵石不足！"
        else:
            msg = f"道友成功消耗灵石：{cost}，灵田数量+1,目前数量:{now_num + 1}"
            mix_elixir_info['灵田数量'] = now_num + 1
            save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
            sql_message.update_ls(user_id, cost, 2)

    await xiuxian_send_message(ling_tian_up, message=msg)


@blessed_spot_rename.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def blessed_spot_rename_(_: Bot, event: GroupMessageEvent):
    """
    洞天福地改名
    """
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(blessed_spot_rename, message=msg)

    message = str(event.message)
    name = message[5:]
    arg = name
    if arg == "":
        msg = "请输入洞天福地的名字！"
        await xiuxian_send_message(blessed_spot_rename, message=msg)

    if len(arg) > 9:
        msg = f"洞天福地的名字不可大于 9 位,请重新命名"
    else:
        msg = f"道友的洞天福地成功改名为：{arg}"
        sql_message.update_user_blessed_spot_name(user_id, arg)

    await xiuxian_send_message(blessed_spot_rename, message=msg)
