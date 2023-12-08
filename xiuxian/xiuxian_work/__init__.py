from datetime import datetime

from nonebot import require, on_command, on_startswith, on_fullmatch
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger

from .work_data_source import WorkConfig, WorkPlayerData
from .work_handle import work_make_list, check_refresh, format_work_msg, work_check_success, format_work_list
from ..common.bot_utils import xiuxian_send_message, get_input_number, xiuxian_send_group_message
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.item_json import Items
from ..common.param_checker import check_player, Cooldown
from ..common.player_manager import check_user_state
from ..common.rank import Rank
from ..xiuxian_config import XiuConfig, GlobalGameData

# 定时任务
reset_refresh_scheduler = require("nonebot_plugin_apscheduler").scheduler
sql_manager = XiuxianSqlManager()
work_config = WorkConfig()
items = Items()
rank = Rank()

work_lookup = on_fullmatch("悬赏令", priority=15, block=True)
work_help = on_fullmatch("悬赏令帮助", priority=15, block=True)
work_refresh = on_fullmatch("悬赏令刷新", priority=15, block=True)
work_accept = on_startswith("悬赏令接取", priority=15, block=True)
work_complete = on_fullmatch("悬赏令结算", priority=15, block=True)
work_stop = on_fullmatch("悬赏令终止", priority=15, block=True)
last_work = on_command("最后的悬赏令", priority=15, block=True)

__work_help__ = f"""
悬赏令帮助信息:
指令：
1、悬赏令:获取对应实力的悬赏令
2、悬赏令刷新:刷新当前悬赏令,每日免费{work_config.free_refresh_count}次
3、悬赏令终止:终止当前悬赏令任务
4、悬赏令结算:结算悬赏奖励
5、悬赏令接取+编号：接取对应的悬赏令
""".strip()


# 重置悬赏令刷新次数
@reset_refresh_scheduler.scheduled_job("cron", hour=9, minute=35)
async def reset_refresh_scheduler_():
    user_list = sql_manager.get_user_list()
    for user_id in user_list:
        player_data = WorkPlayerData(user_id)
        player_data.work_list = []
        player_data.refresh_count = 0
        player_data.save()

    msg = "全部悬赏令已重置! "
    for group_id in GlobalGameData().groups:
        await xiuxian_send_group_message(group_id, msg)
    logger.info(msg)


@work_help.handle(parameterless=[Cooldown(at_sender=True)])
async def work_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(work_help, message=__work_help__)


@work_refresh.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_refresh_(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    user_info = sql_manager.get_user_info(user_id)

    player_data = WorkPlayerData(user_id)
    need_cost = work_config.refresh_cost
    if player_data.refresh_count > work_config.free_refresh_count:
        if user_info.stone < need_cost:
            msg = f"道友的灵石不足以刷新，下次刷新消耗灵石：{need_cost}枚"
            return await xiuxian_send_message(work_refresh, message=msg)
        else:
            sql_manager.sub_money(user_id, need_cost)

    work_list = work_make_list(user_id)
    msg = format_work_list(work_list)

    free_num = work_config.free_refresh_count - player_data.refresh_count
    free_num = free_num - 1
    if free_num < 0:
        msg += f"\n道友消耗灵石{need_cost}枚，成功刷新悬赏令"
        free_num = 0
    msg += f"(今日可用免费刷新次数：{free_num}次，超过后每次刷新消耗灵石：{need_cost}枚)"

    player_data.work_list = work_list
    player_data.refresh_count = player_data.refresh_count + 1
    player_data.save()

    await xiuxian_send_message(work_refresh, message=msg)


@work_accept.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_accept_(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    user_info = sql_manager.get_user_info(user_id)
    num, msg = get_input_number(event)
    if num is None or num < 1 or num > 3:
        msg += '请输入正确的任务序号'
        return await xiuxian_send_message(work_accept, msg)

    max_level = work_config.max_level
    if rank.compare(user_info.level, max_level) == 1:
        msg = f"道友的境界已过创业初期，悬赏令已经不能满足道友了！"
        return await xiuxian_send_message(work_accept, message=msg)

    if int(user_info.exp) >= int(rank.get_next_rank_exp(max_level)) * XiuConfig().closing_exp_upper_limit:
        # 获取下个境界需要的修为 * 1.5为闭关上限
        msg = f"道友的修为已经到达上限，悬赏令已无法在获得经验！"
        return await xiuxian_send_message(work_accept, message=msg)

    is_type, msg = check_user_state(user_id, 0)  # 需要无状态的用户
    if is_type:
        player_data = WorkPlayerData(user_id)
        work_info = player_data.work_list[num - 1]
        sql_manager.set_user_state(user_id, 2, work_info["name"])
        del player_data.work_list[num - 1]
        player_data.current_work = work_info
        player_data.save()
        msg = f'接取任务【{work_info["name"]}】成功!'

    await xiuxian_send_message(work_accept, message=msg)


@work_complete.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_complete_(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    is_refresh, msg = check_refresh(user_id)
    if is_refresh:
        return await xiuxian_send_message(work_complete, message=msg)

    is_type, msg = check_user_state(user_id, 2)  # 需要在悬赏令中的用户
    if is_type:
        user_cd = sql_manager.get_user_cd(user_id)
        work_time = datetime.strptime(user_cd.create_time, "%Y-%m-%d %H:%M:%S.%f")
        exp_time = (datetime.now() - work_time).total_seconds() // 60  # 时长计算

        work_player_data = WorkPlayerData(user_id)
        time2 = work_player_data.current_work["time"]
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd.scheduled_time}】，预计{time2 - exp_time}分钟后可结束"
        else:
            is_success, big_success, work_data = work_check_success(work_player_data.current_work)
            item_id = work_data["item_id"]
            give_exp = work_data["exp"]

            item_flag = False
            item_info = None
            item_msg = None
            if item_id != 0:
                item_flag = True
                item_info = items.get_data_by_item_id(item_id)
                item_msg = f"{item_info['level']}:{item_info['name']}"

            if big_success:  # 大成功
                sql_manager.add_exp(user_id, give_exp * 2)
                sql_manager.set_user_state(user_id, 0)
                msg = f"悬赏令结算，{msg}增加修为{give_exp * 2}"
                # todo 战利品结算sql
                if item_flag:
                    sql_manager.insert_backpack(user_id, item_id, item_info['name'], item_info['type'], 1)
                    msg += f"，额外获得奖励：{item_msg}!"

            else:
                sql_manager.add_exp(user_id, give_exp)
                sql_manager.set_user_state(user_id, 0)
                msg = f"悬赏令结算，{msg}增加修为{give_exp}"
                if is_success:  # 普通成功
                    if item_flag:
                        sql_manager.insert_backpack(user_id, item_id, item_info['name'], item_info['type'], 1)
                        msg += f"，额外获得奖励：{item_msg}!"

            work_player_data.current_work = {}
            work_player_data.save()

    else:
        msg = "没有查到你的悬赏令信息呢，请刷新！"
    await xiuxian_send_message(work_complete, message=msg)


@work_stop.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_stop_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()

    is_refresh, msg = check_refresh(user_id)
    if is_refresh:
        return await xiuxian_send_message(work_stop, message=msg)

    is_type, msg = check_user_state(user_id, 2)  # 需要在悬赏令中的用户
    if is_type:
        # TODO: check money
        stone = work_config.give_up_cost
        sql_manager.sub_money(user_id, stone)
        sql_manager.set_user_state(user_id, 0)
        msg = f"道友不讲诚信，被打了一顿，灵石减少{stone},悬赏令已终止！"
        await xiuxian_send_message(work_stop, message=msg)

    else:
        msg = "没有查到你的悬赏令信息呢，请刷新！"
        await xiuxian_send_message(work_stop, message=msg)


@work_lookup.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def work_lookup_(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    user_cd = sql_manager.get_user_cd(user_id)

    is_refresh, msg = check_refresh(user_id)
    if is_refresh:
        return await xiuxian_send_message(work_stop, message=msg)

    player_data = WorkPlayerData(user_id)
    if user_cd.type == 2:
        work_time = datetime.strptime(user_cd.create_time, "%Y-%m-%d %H:%M:%S.%f")
        exp_time = (datetime.now() - work_time).total_seconds() // 60  # 时长计算
        time2 = player_data.current_work["time"]
        if exp_time < time2:
            msg = f"进行中的悬赏令【{user_cd.scheduled_time}】，预计{time2 - exp_time}分钟后可结束"
        else:
            msg = f"进行中的悬赏令【{user_cd.scheduled_time}】，已结束，请输入【悬赏令结算】结算任务信息！"
    else:
        if not player_data.has_work():
            player_data.work_list = work_make_list(user_id)
            player_data.save()

        free_num = work_config.free_refresh_count - player_data.refresh_count
        if free_num < 0:
            free_num = 0
        need_cost = work_config.refresh_cost
        msg = format_work_list(player_data.work_list)
        msg += f"(今日可用免费刷新次数：{free_num}次，超过后每次刷新消耗灵石：{need_cost}枚)"

    await xiuxian_send_message(work_lookup, message=msg)


@last_work.handle(parameterless=[Cooldown(cd_time=1.3, at_sender=True), check_player()])
async def last_work_(_: Bot, __: GroupMessageEvent):
    pass
