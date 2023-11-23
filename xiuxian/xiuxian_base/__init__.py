from datetime import datetime
from nonebot import on_command, on_fullmatch
from nonebot import require
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..lay_out import assign_bot, Cooldown
from ..utils import check_user
from ..xiuxian2_handle import XiuxianDateManage, XiuxianJsonDate
from ..xiuxian_config import JsonConfig
from ..xn_xiuxian_impart import XIUXIAN_IMPART_BUFF
from .level_up import level_up, level_up_zj, level_up_dr
from .ranking_list import ranking_list, ranking_list_zl, ranking_list_zm, ranking_list_ls

# 定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler
sql_message = XiuxianDateManage()
xiuxian_impart = XIUXIAN_IMPART_BUFF()

run_xiuxian = on_fullmatch("我要修仙", priority=8, block=True)
open_xiuxian = on_command("启用修仙功能", aliases={'禁用修仙功能'}, permission=SUPERUSER, priority=5, block=True)
check_in = on_fullmatch("修仙签到", priority=13, permission=GROUP, block=True)
replay = on_fullmatch("重入仙途", permission=GROUP, priority=7, block=True)
rename = on_command("改名", priority=5, permission=GROUP, block=True)
reset = on_command("重置状态", permission=SUPERUSER, priority=12, block=True)


@scheduler.scheduled_job("cron", hour=0, minute=0)
async def xiuxian_check_in_reset():
    """
     重置每日签到
    """
    sql_message.singh_remake()
    logger.info("每日修仙签到重置成功！")


@run_xiuxian.handle(parameterless=[Cooldown(at_sender=True)])
async def run_xiuxian_(bot: Bot, event: GroupMessageEvent):
    """加入修仙"""
    bot, _ = await assign_bot(bot=bot, event=event)
    user_id = event.get_user_id()
    # 获取为用户名
    user_name = (
        event.sender.card if event.sender.card else event.sender.nickname
    )
    root, root_type = XiuxianJsonDate().linggen_get()  # 获取灵根，灵根类型
    rate = sql_message.get_root_rate(root_type)  # 灵根倍率
    power = 100 * float(rate)  # 战力=境界的 power 字段 * 灵根的 rate 字段
    create_time = str(datetime.now())
    msg = sql_message.create_user(
        user_id, root, root_type, int(power), create_time, user_name
    )
    await xiuxian_send_message(run_xiuxian, msg)


@check_in.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def sign_in_(_: Bot, event: GroupMessageEvent):
    """
    修仙签到
    """
    msg = sql_message.get_sign(event.get_user_id())
    await xiuxian_send_message(check_in, msg)


@replay.handle(parameterless=[Cooldown(90, at_sender=True), check_player()])
async def restart_(bot: Bot, event: GroupMessageEvent):
    """
    重开游戏
    """
    isUser, user_info, msg = check_user(event)
    user_id = user_info.user_id
    name, root_type = XiuxianJsonDate().linggen_get()
    msg = sql_message.ramaker(name, root_type, user_id)
    sql_message.update_power2(user_id)  # 更新战力
    await xiuxian_send_message(replay, msg)


@rename.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def rename_(_: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """
    修改道号
    """
    user_id = event.get_user_id()
    user_name = args.extract_plain_text().strip()
    len_username = len(user_name.encode('gbk'))
    if len_username > 20:
        msg = "道号长度过长，请修改后重试！"
        await xiuxian_send_message(rename, message=msg)

    msg = sql_message.update_user_name(user_id, user_name)
    await xiuxian_send_message(rename, message=msg)


@reset.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def reset_(_: Bot, __: GroupMessageEvent, args: Message = CommandArg()):
    """
    重置用户状态。
    单用户：重置状态 @xxx
    多用户：重置状态
    """
    give_qq = None  # 艾特的时候存到这里
    for arg in args:
        if arg.type == "at":
            give_qq = arg.data.get("qq", "")
    if give_qq:
        sql_message.restate(give_qq)
        msg = '{}用户信息重置成功！'.format(give_qq)
        await xiuxian_send_message(reset, message=msg)
    else:
        sql_message.restate()
        msg = '所有用户信息重置成功！'
        await xiuxian_send_message(reset, message=msg)


@open_xiuxian.handle()
async def open_xiuxian_(_: Bot, event: GroupMessageEvent):
    """群修仙开关配置"""
    group_msg = str(event.message)
    group_id = str(event.group_id)
    if "启用" in group_msg:
        JsonConfig().write_data(1, group_id)  # 添加
        msg = "当前群聊修仙模组已启用！"
    elif "禁用" in group_msg:
        JsonConfig().write_data(2, group_id)  # 删除
        msg = "当前群聊修仙模组已禁用！"
    else:
        msg = "指令错误，请输入：启用修仙功能/禁用修仙功能"
    await xiuxian_send_message(open_xiuxian, message=msg)
