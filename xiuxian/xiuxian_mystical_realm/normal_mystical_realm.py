from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.console import Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from .rift_data_source import MysticalRealmConfig, MysticalRealmPlayerData
from ..common.bot_utils import xiuxian_send_message, get_input_cmd
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import Cooldown, check_player
from ..common.player_manager import check_user_state

normal_mystical_realm_lookup = on_fullmatch("常驻秘境查询", priority=5, permission=GROUP, block=True)
normal_mystical_realm_explore = on_startswith("常驻秘境探索", priority=5, permission=GROUP, block=True)
# normal_mystical_realm_complete = on_fullmatch("常驻秘境结算", priority=5, permission=GROUP, block=True)
normal_mystical_realm_break = on_fullmatch("常驻秘境终止", priority=5, permission=GROUP, block=True)
normal_mystical_realm_lookup_progress = on_fullmatch("秘境进度查询", priority=5, permission=GROUP, block=True)
normal_mystical_realm_select = on_startswith("秘境选择", priority=5, permission=GROUP, block=True)

rift_config = MysticalRealmConfig()
sql_manager = XiuxianSqlManager()


@normal_mystical_realm_lookup.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def normal_mystical_realm_lookup_(_: Bot, __: GroupMessageEvent):
    """
    查询秘境
    """
    msg = ""
    i = 1
    for key, value in rift_config.normal_mystical_realm_list:
        msg += f'{i}.【{key}】秘境等级：{value["rank"]} 预计耗时{value["time"]}分钟\n'
        i += 1
    await xiuxian_send_message(normal_mystical_realm_lookup, msg)


@normal_mystical_realm_explore.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def normal_mystical_realm_explore_(_: Bot, event: GroupMessageEvent):
    """
    探索秘境
    """
    user_id = event.user_id
    name, msg = get_input_cmd(event, 6)
    if not name:
        msg += "请输入：【常驻秘境探索+秘境名称】"
        return await xiuxian_send_message(normal_mystical_realm_explore, msg)

    mystical_realm_info = rift_config.get_normal_mystical_realm(name)
    if not mystical_realm_info:
        msg = f"秘境【{name}】不存在，请重新输入！"
        return await xiuxian_send_message(normal_mystical_realm_explore, msg)

    is_type, msg = check_user_state(user_id, 0)  # 需要无状态的用户
    if not is_type:
        await xiuxian_send_message(normal_mystical_realm_explore, msg)
    else:
        sql_manager.set_user_state(user_id, 3, mystical_realm_info["time"])
        player_data = MysticalRealmPlayerData(user_id)
        player_data.current_mystical_realm = mystical_realm_info
        player_data.save()

        msg = f'道友进入秘境：【{name}】，探索全程需要花费时间：{mystical_realm_info["time"]}分钟！'
        await xiuxian_send_message(normal_mystical_realm_explore, msg)


@normal_mystical_realm_lookup_progress.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def normal_mystical_realm_lookup_progress_(_: Bot, event: GroupMessageEvent):
    """
    秘境查看进度
    """
    user_id = event.user_id
    is_type, msg = check_user_state(user_id, 3)  # 需要在秘境的用户
    if not is_type:
        await xiuxian_send_message(normal_mystical_realm_lookup_progress, msg)


@normal_mystical_realm_break.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def normal_mystical_break_(_: Bot, event: GroupMessageEvent):
    """
    终止探索秘境
    """
    user_id = event.user_id
    is_type, msg = check_user_state(user_id, 3)  # 需要在秘境的用户
    if not is_type:
        await xiuxian_send_message(normal_mystical_realm_break, msg)
    else:
        player_data = MysticalRealmPlayerData(user_id)
        sql_manager.set_user_state(user_id, 0)
        if player_data.has_mystical_realm():
            msg = f"已终止【{player_data.current_mystical_realm['name']}】秘境的探索！"
            await xiuxian_send_message(normal_mystical_realm_break, msg)
        else:
            msg = "秘境已刷新，重置用户状态成功！"
            await xiuxian_send_message(normal_mystical_realm_break, msg)
