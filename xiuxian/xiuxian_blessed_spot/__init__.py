from datetime import datetime
from .garden import garden_get, garden_up, garden_help
from .vein import vein_help, vein_get, vein_up
from nonebot import on_fullmatch, on_startswith, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..lay_out import Cooldown
from ..read_buff import save_player_info, get_player_info, UserBuffDate, read_player_info
from ..utils import check_user
from ..xiuxian2_handle import XiuxianDateManage

blessed_spot_creat = on_fullmatch("洞天福地购买", priority=10, permission=GROUP, block=True)
blessed_spot_info = on_fullmatch("我的洞天福地", priority=11, permission=GROUP, block=True)
blessed_spot_rename = on_startswith("洞天福地改名", priority=7, permission=GROUP, block=True)
blessed_help = on_fullmatch("洞天福地帮助", priority=5, permission=GROUP, block=True)

sql_message = XiuxianDateManage()

BLESSEDSPOT_COST = 500000

__buff_help__ = f"""
洞天福地帮助信息:
指令：
1、洞天福地购买:购买洞天福地
2、我的洞天福地:查看自己的洞天福地
3、洞天福地改名+名字：修改自己洞天福地的名字
4、灵田系统:输入【灵田帮助】
5、灵矿系统:输入【灵矿帮助】
""".strip()


@blessed_help.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(blessed_help, message=__buff_help__)


@blessed_spot_creat.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def blessed_spot_creat_(bot: Bot, event: GroupMessageEvent):
    """
    洞天福地购买
    """
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id

    if int(user_info.blessed_spot_flag) != 0:
        msg = f"道友已经拥有洞天福地了，请发送洞天福地查看吧~"
        await xiuxian_send_message(blessed_spot_creat, message=msg)

    if user_info.stone < BLESSEDSPOT_COST:
        msg = f"道友的灵石不足{BLESSEDSPOT_COST}枚，无法购买洞天福地"
        await xiuxian_send_message(blessed_spot_creat, message=msg)

    else:
        sql_message.update_ls(user_id, BLESSEDSPOT_COST, 2)
        sql_message.update_user_blessed_spot_flag(user_id)
        mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
        mix_elixir_info['收取时间'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
        msg = f"恭喜道友拥有了自己的洞天福地，请收集聚灵旗来提升洞天福地的等级吧~"
        await xiuxian_send_message(blessed_spot_creat, message=msg)


@blessed_spot_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def blessed_spot_info_(_: Bot, event: GroupMessageEvent):
    """
    洞天福地信息
    """
    _, user_info, _ = check_user(event)

    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(blessed_spot_info, message=msg)

    msg = f'道友的洞天福地:\n'
    user_buff_data = UserBuffDate(user_id).BuffInfo
    if user_info.blessed_spot_name == 0:
        blessed_spot_name = "尚未命名"
    else:
        blessed_spot_name = user_info.blessed_spot_name
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    vein_info = read_player_info(user_id, "vein")

    msg += f"名字：{blessed_spot_name}\n"
    msg += f"修炼速度：增加{int(user_buff_data.blessed_spot) * 100}%\n"
    msg += f"灵田数量：{mix_elixir_info['灵田数量']}\n"
    msg += f"灵矿数量：{vein_info['num']}"
    await xiuxian_send_message(blessed_spot_info, message=msg)


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
    name = message[6:]
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
