import random
from datetime import datetime

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from .level_up import level_up, level_up_zj, level_up_dr
from .ranking_list import ranking_list, ranking_list_zl, ranking_list_zm, ranking_list_ls
from ..common.bot_utils import xiuxian_send_message, get_input_cmd
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import check_player, Cooldown
from ..common.rank import Rank
from ..common.root import Root
from ..common.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_config import GlobalGameData, XiuConfig

open_xiuxian = on_startswith("群修仙", priority=5, block=True)
run_xiuxian = on_fullmatch("我要修仙", priority=8, block=True)
check_in = on_fullmatch("修仙签到", priority=13, permission=GROUP, block=True)
replay = on_fullmatch("重入仙途", permission=GROUP, priority=7, block=True)
reset = on_startswith("重置状态", priority=12, block=True)
rename = on_startswith("改名", priority=5, permission=GROUP, block=True)


sql_message = XiuxianDateManage()
sql_manager = XiuxianSqlManager()
root = Root()


@scheduler.scheduled_job("cron", hour=0, minute=0)
async def xiuxian_check_in_reset():
    """
     重置每日签到
    """
    sql_message.check_in_reset()
    logger.info("每日修仙签到重置成功！")


@run_xiuxian.handle(parameterless=[Cooldown(at_sender=True)])
async def run_xiuxian_(_: Bot, event: GroupMessageEvent):
    """
    加入修仙
    """
    user_id = event.user_id
    # 获取为用户名
    user_name = (
        event.sender.card if event.sender.card else event.sender.nickname
    )
    root_name, root_type = root.get_random_root()  # 获取灵根，灵根类型
    root_speed = root.get_root_speed(root_type)  # 灵根倍率
    power = 100 * root_speed  # 战力=境界的 power 字段 * 灵根的 rate 字段
    create_time = str(datetime.now())
    msg = sql_message.create_user(
        user_id, root_name, root_type, int(power), create_time, user_name
    )
    await xiuxian_send_message(run_xiuxian, msg)


@check_in.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def sign_in_(_: Bot, event: GroupMessageEvent):
    """
    修仙签到
    """
    user_info = sql_manager.get_user_info(event.user_id)
    stone = random.randint(XiuConfig().sign_in_stone_lower_limit, XiuConfig().sign_in_stone_upper_limit)
    level_num = Rank().to_level_index(user_info.level)
    stone = level_num * XiuConfig().sign_in_stone_lower_limit + stone
    sql_manager.add_money(user_info.user_id, stone)
    sql_manager.set_sign_in(user_info.user_id, 1)
    if user_info.is_sign == 1:
        msg = '贪心的人是不会有好运的！'
    else:
        msg = f'签到成功，获取{stone}枚灵石!'
    await xiuxian_send_message(check_in, msg)


@replay.handle(parameterless=[Cooldown(30, at_sender=True), check_player()])
async def restart_(_: Bot, event: GroupMessageEvent):
    """
    重入仙途
    """
    user_id = event.get_user_id()
    name, root_type = root.get_random_root()
    msg = sql_message.ramaker(name, root_type, user_id)
    sql_message.update_power2(user_id)  # 更新战力
    await xiuxian_send_message(replay, msg)


@rename.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def rename_(_: Bot, event: GroupMessageEvent):
    """
    改名
    """
    user_id = event.get_user_id()
    user_name, msg = get_input_cmd(event, 2)
    if not user_name:
        msg += "请输入：【改名+道号】"
        return await xiuxian_send_message(open_xiuxian, message=msg)

    length = len(user_name.encode('gbk'))
    if length > 20:
        msg = "道号太长会遭天谴的，请修改后重试！"
        await xiuxian_send_message(rename, message=msg)

    msg = sql_message.update_user_name(user_id, user_name)
    await xiuxian_send_message(rename, message=msg)


@open_xiuxian.handle()
async def open_xiuxian_(_: Bot, event: GroupMessageEvent):
    """
    群修仙开关配置
    """
    group_id = event.group_id
    cmd, msg = get_input_cmd(event, 3)
    if not cmd:
        msg += "请输入：【群修仙+开启/关闭】"
        return await xiuxian_send_message(open_xiuxian, message=msg)

    global_data = GlobalGameData()
    if "开启" == cmd:
        if group_id not in global_data.groups:
            global_data.groups.append(group_id)
        msg = "当前群聊修仙模组已启用！"

    elif "关闭" == cmd:
        if group_id in global_data.groups:
            global_data.groups.remove(group_id)
        msg = "当前群聊修仙模组已禁用！"
    else:
        msg = "指令错误！请输入：【群修仙+开启/关闭】"

    global_data.save()
    await xiuxian_send_message(open_xiuxian, message=msg)
