import random

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from ..common import DRIVER
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_message, get_input_cmd, get_input_number, \
    xiuxian_send_group_img_message
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import check_player, check_admin, Cooldown
from ..common.player_fight import boss_fight, user_info_to_player_info, boss_info_to_player_info, \
    player_info_to_boss_info
from ..common.player_manager import leave_harm_time
from ..common.rank import Rank
from ..common.utils import number_to
from ..common.xiuxian2_handle import items

from .boss_point_shop import boss_point_shop_list, boss_point_shop_use, boss_point_shop_lookup
from .boss_data_source import BossConfig, BossGameData, BossPlayerData
from .boss_handle import check_group_open_boss, create_boss, check_input_boss

battle_flag = {}
sql_manager = XiuxianSqlManager()
boss_config = BossConfig()
boss_data = BossGameData()
rank = Rank()

boss_help = on_fullmatch("世界boss帮助", priority=5, block=True)
set_group_boss = on_startswith("世界boss", priority=13, rule=check_admin(), block=True)
boss_create = on_startswith("生成世界boss", priority=5, rule=check_admin(), block=True)
boss_info = on_fullmatch("世界boss查询", priority=6, permission=GROUP, block=True)
boss_battle = on_startswith("讨伐世界boss", priority=6, permission=GROUP, block=True)
boss_delete = on_startswith("天罚世界boss", priority=7, rule=check_admin(), block=True)

__boss_help__ = f"""
世界Boss帮助信息:
指令：
1、世界boss+开启/关闭:开启后才可以生成世界Boss,管理员权限
2、生成世界boss+大境界:生成一只随机大境界的世界Boss,超管权限
3、世界boss查询:查询本群全部世界Boss,可加Boss编号查询对应Boss信息
4、讨伐世界boss+编号:与世界Boss对战
5、天罚世界boss+编号:删除世界Boss,必须加Boss编号,管理员权限
6、世界积分查询:查看世界积分兑换商品
7、我的世界积分:查看我的世界积分
8、世界积分兑换+编号:兑换对应的商品
""".strip()


@DRIVER.on_startup
async def set_boss_scheduler():
    create_time = boss_config.boss_create_time
    try:
        for group_id in boss_data.group_list:
            scheduler.add_job(
                func=notify_bot_message,
                trigger='interval',
                hours=create_time["hours"],
                minutes=create_time['minutes'],
                id=f'set_boss_{group_id}',
                args=[group_id],
                misfire_grace_time=10
            )
            logger.success(f'开启群{group_id}boss,每{create_time["hours"]}小时{create_time["minutes"]}分钟刷新！')
    except Exception as e:
        logger.success(f'警告,定时群boss加载失败!,{e}!')


async def notify_bot_message(group_id: str):
    # 到boss生成上限了，直接跳过
    if len(boss_data.boss_list) >= boss_config.boss_max_num:
        return

    boss_info = create_boss()
    boss_data.boss_list.append(boss_info)
    boss_data.save()
    boss_id = len(boss_data.boss_list)

    msg = f"邪气弥漫，邪魔{boss_id}.{boss_info['rank']}:【{boss_info['name']}】出现，诸位道友请击败邪魔得奖励吧!"
    await xiuxian_send_group_message(group_id, msg)
    logger.info(f"群{group_id}_已生成世界boss")


@boss_help.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(boss_help, message=__boss_help__)


@boss_delete.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_delete_(_: Bot, event: GroupMessageEvent):
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_delete, msg)

    boss_num, msg = get_input_number(event)
    if not boss_num:
        msg += f'请输入：【天罚世界boss+数字】'
        await xiuxian_send_message(boss_delete, message=msg)

    index = len(boss_data.boss_list)
    if not (0 < boss_num <= index):
        msg = f'请输入正确的世界Boss编号!'
        await xiuxian_send_message(boss_delete, message=msg)

    boss_data.boss_list.remove(boss_data.boss_list[boss_num - 1])
    msg = f"该世界 boss【{boss_num}】被突然从天而降的神雷劈中,烟消云散了"
    await xiuxian_send_message(boss_delete, message=msg)


@boss_battle.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def battle_(bot: Bot, event: GroupMessageEvent):
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_delete, msg)

    boss_num, msg = get_input_number(event)
    if not boss_num:
        msg += f'请输入：【讨伐世界boss+数字】'
        return await xiuxian_send_message(boss_delete, msg)

    result, msg = check_input_boss(boss_num)
    if not result:
        return await xiuxian_send_message(boss_delete, msg)

    group_id = event.group_id
    try:
        battle_flag[group_id]
    except:
        battle_flag[group_id] = False

    if battle_flag[group_id]:
        msg = f'当前有道友正在Boss战斗!'
        return await xiuxian_send_message(boss_battle, message=msg)

    user_info = sql_manager.get_user_info(event.user_id)
    user_id = user_info.user_id
    if user_info.hp <= user_info.exp // 10:
        time = leave_harm_time(user_id)
        msg = f"重伤未愈，动弹不得！距离脱离危险还需要{time}分钟！"
        return await xiuxian_send_message(boss_battle, message=msg)

    boss_info = boss_data.boss_list[boss_num - 1]
    boss_rank = rank.to_level_index(boss_info['rank'])
    user_rank = rank.to_level_index(user_info.level)

    boss_old_hp = boss_info['hp']  # 打之前的血量
    boss_all_hp = boss_info['max_hp']  # 总血量
    battle_flag[group_id] = True
    more_msg = ""

    player_info1 = user_info_to_player_info(user_info)
    player_info2 = boss_info_to_player_info(boss_info)
    battle_list, victor, boss_info_new, get_stone = await boss_fight(player_info1, player_info2, bot_id=bot.self_id)
    boss_info_new = player_info_to_boss_info(boss_info_new)

    boss_integral_rate = 30 + boss_rank * 2
    boss_player_data = BossPlayerData(user_id)

    if victor == "Boss赢了":
        boss_data.boss_list[boss_num - 1] = boss_info_new
        sql_manager.add_money(user_id, get_stone)
        sql_manager.add_exp(user_id, get_stone)

        boss_now_hp = boss_info_new['hp']  # 打之后的血量
        boss_integral = int(((boss_old_hp - boss_now_hp) / boss_all_hp) * boss_integral_rate)
        if boss_integral < 2:  # 摸一下不给
            boss_integral = 2

        boss_player_data.point += boss_integral
        boss_player_data.save()

        msg = (f"道友不敌【{boss_info['name']}】，重伤逃遁，剩余血量({boss_now_hp}/{boss_all_hp})\n"
               f"临逃前收获奖励：\n"
               f"灵石:{get_stone}枚\n"
               f"修为:{get_stone // 2}点\n"
               f"世界积分:{boss_integral}点")

    elif victor == "群友赢了":
        # boss 战斗积分点数
        boss_integral = int((boss_old_hp / boss_all_hp) * boss_integral_rate)
        if user_rank - boss_rank >= 6:  # 超过太多不给
            boss_integral = 1
            more_msg = "道友的境界超过boss太多了,不齿！"

        sql_manager.add_money(user_id, get_stone)
        sql_manager.add_exp(user_id, get_stone)

        boss_data.boss_list.remove(boss_data.boss_list[boss_num - 1])
        boss_data.save()

        boss_player_data.point += boss_integral
        boss_player_data.save()

        goods_id_list = [1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109]
        item_id = random.choice(goods_id_list)
        item_info = items.get_data_by_item_id(item_id)
        item_msg = f"【{item_info['level']}:{item_info['name']}】"
        sql_manager.insert_backpack(user_id, item_id, item_info['name'], item_info['type'], 1)

        msg = (f"恭喜道友击败【{boss_info['name']}】，{more_msg}"
               f"获得奖励：\n"
               f"灵石:{get_stone}枚\n"
               f"修为:{get_stone // 2}点\n"
               f"世界积分:{boss_integral}点\n"
               f"获得物品:{item_msg}")

    battle_flag[group_id] = False
    msg_list = []
    for item in battle_list:
        msg_list.append(item["data"]["content"])

    if len(msg_list) > 20:
        msg_list = msg_list[:20]
        msg_list.append(f"以下省略 {len(battle_list) - 20} 行\n...")

    await xiuxian_send_group_img_message(event.group_id, msg_list)
    await xiuxian_send_message(boss_battle, message=msg)


@boss_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_info_(_: Bot, event: GroupMessageEvent):
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_delete, msg)

    result, msg = check_input_boss(1)
    if not result:
        return await xiuxian_send_message(boss_delete, msg)

    i = 1
    msg = ""
    for boss in boss_data.boss_list:
        msg += (f"{i}.【{boss['rank']}{boss['name']}】 "
                f"血量：{number_to(boss['hp'])} "
                f"攻击：{number_to(boss['atk'])} "
                f"携带灵石：{number_to(boss['stone'])}\n")
        i += 1
    await xiuxian_send_message(boss_info, message=msg)


@boss_create.handle(parameterless=[Cooldown(at_sender=True)])
async def create_(_: Bot, event: GroupMessageEvent):
    """
    生成世界 boss
    """
    result, msg = check_group_open_boss(event.group_id)
    if not result:
        return await xiuxian_send_message(boss_delete, msg)

    level_name, msg = get_input_cmd(event, 8)
    if not level_name:
        boss_info = create_boss()
    else:
        boss_info = create_boss(level_name)

    if len(boss_data.boss_list) >= boss_config.boss_max_num:
        msg = f"本群世界Boss已达到上限{boss_config.boss_max_num}个，无法继续生成"
        return await xiuxian_send_message(boss_create, message=msg)

    boss_data.boss_list.append(boss_info)
    boss_data.save()

    msg = f"已生成{boss_info['rank']}邪魔:【{boss_info['name']}】，诸位道友请击败邪魔获得奖励吧!"
    await xiuxian_send_message(boss_create, message=msg)


@set_group_boss.handle(parameterless=[Cooldown(at_sender=True)])
async def set_group_boss_(_: Bot, event: GroupMessageEvent):
    """
    世界boss开启/关闭
    """
    mode, msg = get_input_cmd(event, 6)
    if not mode:
        msg += ",请输入【世界boss+开启/关闭】"
        return
    group_id = event.group_id
    if mode == '开启':
        boss_data.group_list.append(group_id)
        boss_data.save()
        msg = f'已开启本群世界Boss!'
        await xiuxian_send_message(set_group_boss, message=msg)

    elif mode == '关闭':
        boss_data.group_list.remove(group_id)
        boss_data.save()
        msg = f'已关闭本群世界Boss!'
        await xiuxian_send_message(set_group_boss, message=msg)
