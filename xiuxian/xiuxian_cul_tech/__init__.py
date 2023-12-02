# 修仙功法 Cultivation Technique
from nonebot import on_fullmatch, Bot, on_startswith
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player,Cooldown
from ..common.item_json import Items
from ..common.read_buff import UserBuffDate, get_user_buff, get_main_info_msg, get_sec_msg
from ..common.xiuxian2_handle import XiuxianDateManage

buff_info = on_fullmatch("我的功法", priority=25, permission=GROUP, block=True)
buff_help = on_fullmatch("功法帮助", priority=5, permission=GROUP, block=True)
buff_learn = on_startswith("功法修炼", priority=5, permission=GROUP, block=True)
__buff_help__ = f"""功法帮助信息:
指令：
1、我的功法:查看自身功法信息
2、功法修炼+功法名称:修炼背包中的指定功法
"""

sql_message = XiuxianDateManage()
items = Items()


@buff_help.handle(parameterless=[Cooldown(at_sender=True)])
async def buff_help_(_: Bot, event: GroupMessageEvent):
    """
    功法帮助
    """
    await xiuxian_send_message(buff_info, __buff_help__)


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

    main_buff_name = main_buff_data["name"] if main_buff_data is not None else '无'
    sec_buff_name = sec_buff_data["name"] if sec_buff_data is not None else '无'

    msg = (f"道友的主功法：{main_buff_name}\n"
           f"{main_buff_msg}\n"
           f"道友的神通：{sec_buff_name}\n"
           f"{sec_buff_msg}")
    await xiuxian_send_message(buff_info, message=msg)


@buff_learn.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def buff_learn_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()
    message = str(event.message)
    arg = message[4:]  #
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await xiuxian_send_message(buff_learn, message=msg)

    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    for back in back_msg:
        if arg == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            break

    if not in_flag:
        msg = f"请检查该道具【{arg}】 是否在背包内！"
        await xiuxian_send_message(buff_learn, message=msg)

    user_buff_info = UserBuffDate(user_id).BuffInfo
    skill_info = items.get_data_by_item_id(goods_id)
    skill_type = skill_info['item_type']
    if skill_type == "神通":
        if int(user_buff_info.sec_buff) == int(goods_id):
            msg = f"道友已学会该神通：【{skill_info['name']}】，请勿重复学习！"
        else:  # 学习sql
            sql_message.update_back_j(user_id, goods_id)
            sql_message.updata_user_sec_buff(user_id, goods_id)
            msg = f"恭喜道友学会神通：【{skill_info['name']}】！"
    elif skill_type == "功法":
        if int(user_buff_info.main_buff) == int(goods_id):
            msg = f"道友已学会该功法：【{skill_info['name']}】，请勿重复学习！"
        else:  # 学习sql
            sql_message.update_back_j(user_id, goods_id)
            sql_message.updata_user_main_buff(user_id, goods_id)
            msg = f"恭喜道友学会功法：【{skill_info['name']}】！"
    else:
        msg = "发生未知错误！"

    await xiuxian_send_message(buff_learn, message=msg)
