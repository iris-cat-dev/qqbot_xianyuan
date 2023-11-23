# 修仙功法 Cultivation Technique
from nonebot import on_fullmatch, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..lay_out import Cooldown
from ..read_buff import UserBuffDate, get_user_buff, get_main_info_msg, get_sec_msg

buff_info = on_fullmatch("我的功法", priority=25, permission=GROUP, block=True)
buff_help = on_fullmatch("功法帮助", priority=5, permission=GROUP, block=True)
__buff_help__ = f"""
                功法帮助信息:
                指令：
                1、我的功法:查看自身功法信息
                """

@buff_help.handle(parameterless=[Cooldown(at_sender=True)])
async def buff_help_(_: Bot, event: GroupMessageEvent):
    """
    功法帮助
    """
    await xiuxian_send_message(event, __buff_help__)


@buff_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def buff_info_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()

    main_buff_data = UserBuffDate(user_id).get_user_main_buff_data()
    if main_buff_data is not None:
        s, main_buff_msg = get_main_info_msg(str(get_user_buff(user_id).main_buff))
    else:
        main_buff_msg = ''

    sec_buff_data = UserBuffDate(user_id).get_user_sec_buff_data()
    sec_buff_msg = get_sec_msg(sec_buff_data)

    msg = f"""
            道友的主功法：{main_buff_data["name"] if main_buff_data is not None else '无'}
            {main_buff_msg}
            道友的神通：{sec_buff_data["name"] if sec_buff_data is not None else '无'}
            {sec_buff_msg}
            """
    await xiuxian_send_message(event, message=msg)
