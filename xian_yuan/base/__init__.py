import random
from datetime import datetime

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.qq import Bot, MessageEvent, MessageCreateEvent
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from .level_up import level_up, level_up_zj, level_up_dr
from .ranking_list import ranking_list, ranking_list_zl, ranking_list_zm, ranking_list_ls
from ..common.bot_utils import xiuxian_send_message, get_input_cmd
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import check_player, Cooldown
from ..common.rank import Rank
from ..common.root import Root
from ..xiuxian_config import XiuConfig

join_xiuxian = on_fullmatch("我要修仙", priority=8, block=True)
rename = on_startswith("改名", priority=5, block=True)

sql_manager = XiuxianSqlManager()
root = Root()
game_config = XiuConfig()


@scheduler.scheduled_job("cron", hour=0, minute=0)
async def xiuxian_check_in_reset():
    """
     重置每日签到
    """
    sql_message.check_in_reset()
    logger.info("每日修仙签到重置成功！")


@join_xiuxian.handle()
async def join_xiuxian_(_: Bot, event: MessageCreateEvent):
    """
    加入修仙
    """
    user_id = event.get_user_id()
    # 获取为用户名
    user_name = event.author.username
    root_name, root_type = root.get_random_root()  # 获取灵根，灵根类型
    root_speed = root.get_root_speed(root_type)  # 灵根倍率
    power = 100 * root_speed  # 战力=境界的 power 字段 * 灵根的 rate 字段
    create_time = str(datetime.now())
    msg = sql_message.create_user(user_id, root_name, root_type, int(power), create_time, user_name)
    await xiuxian_send_message(join_xiuxian, msg)



@rename.handle(parameterless=[Cooldown(), check_player()])
async def rename_(_: Bot, event: MessageEvent):
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

    msg = sql_manager.update_user_name(user_id, user_name)
    await xiuxian_send_message(rename, message=msg)


