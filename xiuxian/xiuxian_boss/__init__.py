import json
import os
import random
import re
from pathlib import Path

from nonebot import get_bots, get_bot, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    GroupMessageEvent,
    MessageSegment
)
from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler

from .bossconfig import get_config, savef
from .makeboss import createboss, createboss_root
from .old_boss_info import old_boss_info
from .. import DRIVER
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_message, xiuxian_send_group_img_message
from ..common.param_checker import check_player, check_admin
from ..item_json import Items
from ..lay_out import put_bot, layout_bot_dict, Cooldown
from ..player_fight import Boss_fight
from ..read_buff import UserBuffDate
from ..utils import number_to, check_user, get_msg_pic
from ..xiuxian2_handle import XiuxianDateManage
from ..xiuxian_config import USERRANK, MAX_RANK
from ..xiuxian_config import XiuConfig
from ..xn_xiuxian_impart import XIUXIAN_IMPART_BUFF, leave_harm_time

config = get_config()
cache_help = {}
del_boss_id = XiuConfig().del_boss_id
group_boss = {}
groups = config['open']
battle_flag = {}
sql_message = XiuxianDateManage()
xiuxian_impart = XIUXIAN_IMPART_BUFF()

boss_help = on_fullmatch("世界boss帮助", priority=5, block=True)
set_group_boss = on_startswith("世界boss", priority=13, rule=check_admin(), block=True)
create = on_fullmatch("生成世界boss", priority=5, rule=check_admin(), block=True)
boss_info = on_fullmatch("查询世界boss", priority=6, permission=GROUP, block=True)
battle = on_startswith("讨伐世界boss", priority=6, permission=GROUP, block=True)
boss_delete = on_startswith("天罚世界boss", priority=7, rule=check_admin(), block=True)
boss_integral_info = on_fullmatch("世界积分查询", priority=10, permission=GROUP, block=True)
boss_integral_use = on_startswith("世界积分兑换", priority=6, permission=GROUP, block=True)

boss_time = config["Boss生成时间参数"]

__boss_help__ = f"""
世界Boss帮助信息:
指令：
1、生成世界boss:生成一只随机大境界的世界Boss,超管权限
2、查询世界boss:查询本群全部世界Boss,可加Boss编号查询对应Boss信息
3、世界boss+开启/关闭:开启后才可以生成世界Boss,管理员权限
4、讨伐世界boss+编号:与世界Boss对战
5、世界boss帮助:获取世界Boss帮助信息
6、天罚世界boss:删除世界Boss,必须加Boss编号,管理员权限
7、世界积分查询:查看自己的世界积分,和世界积分兑换商品
8、世界积分兑换+编号：兑换对应的商品
""".strip()


@DRIVER.on_startup
async def read_boss_():
    global group_boss
    group_boss.update(old_boss_info.read_boss_info())
    logger.info("历史boss数据读取成功")


@DRIVER.on_startup
async def set_boss_():
    groups_list = list(groups.keys())
    try:
        for group_id in groups_list:
            scheduler.add_job(
                func=send_bot,
                trigger='interval',
                hours=groups[str(group_id)]["hours"],
                minutes=groups[str(group_id)]['minutes'],
                id=f'set_boss_{group_id}',
                args=[group_id],
                misfire_grace_time=10
            )
            logger.success('开启群{}boss,每{}小时{}分钟刷新！'.format(group_id,
                                                                     groups[str(group_id)]["hours"],
                                                                     groups[str(group_id)]['minutes']))
    except Exception as e:
        logger.success(f'警告,定时群boss加载失败!,{e}!')


async def send_bot(group_id: str):
    # 初始化
    if not group_id in group_boss:
        group_boss[group_id] = []

    # 到boss生成上限了，直接跳过
    if len(group_boss[group_id]) >= config['Boss个数上限']:
        return

    boss_info = createboss()
    group_boss[group_id].append(boss_info)
    msg = f"已生成{len(group_boss[group_id]) + 1}.{boss_info['jj']}Boss:{boss_info['name']},诸位道友请击Boss得奖励吧!"
    await xiuxian_send_group_message(group_id, msg)
    logger.info(f"群{group_id}_已生成世界boss")


def is_in_groups(event: GroupMessageEvent):
    return str(event.group_id) in groups


PLAYERSDATA = Path() / "data" / "xiuxian" / "players"


def get_user_boss_fight_info(user_id):
    try:
        user_boss_fight_info = read_user_boss_fight_info(user_id)
    except:
        user_boss_fight_info = {'boss_integral': 0}
        save_user_boss_fight_info(user_id, user_boss_fight_info)
    return user_boss_fight_info


def read_user_boss_fight_info(user_id):
    user_id = str(user_id)

    FILEPATH = PLAYERSDATA / user_id / "boss_fight_info.json"
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def save_user_boss_fight_info(user_id, data):
    user_id = str(user_id)

    if not os.path.exists(PLAYERSDATA / user_id):
        print("目录不存在，创建目录")
        os.makedirs(PLAYERSDATA / user_id)

    FILEPATH = PLAYERSDATA / user_id / "boss_fight_info.json"
    data = json.dumps(data, ensure_ascii=False, indent=4)
    save_mode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=save_mode, encoding="UTF-8") as f:
        f.write(data)
        f.close()


@DRIVER.on_shutdown
async def save_boss_():
    global group_boss
    old_boss_info.save_boss(group_boss)
    logger.info("boss数据已保存")


@boss_help.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(boss_help, message=__boss_help__)


@boss_delete.handle(parameterless=[Cooldown(at_sender=True)])
async def boss_delete_(_: Bot, event: GroupMessageEvent):
    msg = str(event.message)
    boss_num = re.findall("\d+", msg)  # boss编号
    group_id = str(event.group_id)

    if not is_in_groups(event):  # 不在配置表内
        msg = f'本群尚未开启世界Boss,请联系管理员开启!'
        await xiuxian_send_message(boss_delete, message=msg)

    if boss_num:
        boss_num = int(boss_num[0])
    else:
        msg = f'请输入正确的世界Boss编号!'
        await xiuxian_send_message(boss_delete, message=msg)

    bosss = None
    try:
        bosss = group_boss[group_id]
    except:
        msg = f'本群尚未生成世界Boss,请等待世界boss刷新!'
        await xiuxian_send_message(boss_delete, message=msg)

    if not bosss:
        msg = f'本群尚未生成世界Boss,请等待世界boss刷新!'
        await xiuxian_send_message(boss_delete, message=msg)

    index = len(group_boss[group_id])
    if not (0 < boss_num <= index):
        msg = f'请输入正确的世界Boss编号!'
        await xiuxian_send_message(boss_delete, message=msg)

    group_boss[group_id].remove(group_boss[group_id][boss_num - 1])
    msg = f"该世界Boss被突然从天而降的神雷劈中,烟消云散了"
    await xiuxian_send_message(boss_delete, message=msg)


@battle.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def battle_(bot: Bot, event: GroupMessageEvent):
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id
    group_id = str(event.group_id)

    msg = str(event.message)
    boss_num = re.findall("\d+", msg)  # boss编号

    if not is_in_groups(event):  # 不在配置表内
        msg = f'本群尚未开启世界Boss,请联系管理员开启!'
        await xiuxian_send_message(battle, message=msg)

    if boss_num:
        boss_num = int(boss_num[0])
    else:
        msg = f'请输入正确的世界Boss编号!'
        await xiuxian_send_message(battle, message=msg)

    bosss = None
    try:
        bosss = group_boss[group_id]
    except:
        msg = f'本群尚未生成世界Boss,请等待世界boss刷新!'
        await xiuxian_send_message(battle, message=msg)

    if not bosss:
        msg = f'本群尚未生成世界Boss,请等待世界boss刷新!'
        await xiuxian_send_message(battle, message=msg)

    index = len(group_boss[group_id])

    if not (0 < boss_num <= index):
        msg = f'请输入正确的世界Boss编号!'
        await xiuxian_send_message(battle, message=msg)

    try:
        battle_flag[group_id]
    except:
        battle_flag[group_id] = False

    if battle_flag[group_id]:
        msg = f'当前有道友正在Boss战斗!'
        await xiuxian_send_message(battle, message=msg)

    if user_info.hp is None or user_info.hp == 0:
        # 判断用户气血是否为空
        XiuxianDateManage().update_user_hp(user_id)

    if user_info.hp <= user_info.exp / 10:
        time = leave_harm_time(user_id)
        msg = f"重伤未愈，动弹不得！距离脱离危险还需要{time}分钟！"
        await xiuxian_send_message(battle, message=msg)

    player = {"user_id": None, "道号": None, "气血": None, "攻击": None, "真元": None, '会心': None, '防御': 0}
    userinfo = XiuxianDateManage().get_user_real_info(user_id)
    user_weapon_data = UserBuffDate(userinfo.user_id).get_user_weapon_data()

    impart_data = xiuxian_impart.get_user_message(user_id)
    boss_atk = impart_data.boss_atk if impart_data.boss_atk is not None else 0

    if user_weapon_data != None:
        player['会心'] = int(user_weapon_data['crit_buff'] * 100)
    else:
        player['会心'] = 1

    player['user_id'] = userinfo.user_id
    player['道号'] = userinfo.user_name
    player['气血'] = userinfo.hp
    player['攻击'] = int(userinfo.atk * (1 + boss_atk))
    player['真元'] = userinfo.mp
    player['exp'] = userinfo.exp

    boss_info = group_boss[group_id][boss_num - 1]
    if boss_info['jj'] == "祭道之上":
        boss_rank = USERRANK[(boss_info['jj'])]
    else:
        boss_rank = USERRANK[(boss_info['jj'] + '中期')]

    user_rank = USERRANK[userinfo.level]
    boss_old_hp = boss_info['气血']  # 打之前的血量
    more_msg = ''
    battle_flag[group_id] = True
    result, victor, boss_info_new, get_stone = await Boss_fight(player, boss_info, bot_id=bot.self_id)
    boss_integral_rate = 30 + (MAX_RANK - boss_rank) * 2

    if victor == "Boss赢了":
        group_boss[group_id][boss_num - 1] = boss_info_new
        XiuxianDateManage().update_ls(user_id, get_stone, 1)
        # 新增boss战斗积分点数
        boss_now_hp = boss_info_new['气血']  # 打之后的血量
        boss_all_hp = boss_info['总血量']  # 总血量
        boss_integral = int(((boss_old_hp - boss_now_hp) / boss_all_hp) * boss_integral_rate)
        if boss_integral < 2:  # 摸一下不给
            boss_integral = 2

        if boss_rank - user_rank >= 6:  # 超过太多不给
            boss_integral = 1
            more_msg = "道友的境界超过boss太多了,不齿！"

        user_boss_fight_info = get_user_boss_fight_info(user_id)
        user_boss_fight_info['boss_integral'] += boss_integral
        save_user_boss_fight_info(user_id, user_boss_fight_info)

        msg = (f"道友不敌{boss_info['name']}，重伤逃遁，血量({boss_now_hp}/{boss_all_hp})，"
               f"临逃前收获灵石{get_stone}枚，{more_msg}获得世界积分：{boss_integral}点")

        battle_flag[group_id] = False

    elif victor == "群友赢了":
        # 新增boss战斗积分点数
        boss_all_hp = boss_info['总血量']  # 总血量
        boss_integral = int((boss_old_hp / boss_all_hp) * boss_integral_rate)
        if boss_integral < 2:  # 摸一下不给
            boss_integral = 2

        if boss_rank - user_rank >= 6:  # 超过太多不给
            boss_integral = 1
            more_msg = "道友的境界超过boss太多了,不齿！"

        group_boss[group_id].remove(group_boss[group_id][boss_num - 1])
        battle_flag[group_id] = False
        XiuxianDateManage().update_ls(user_id, get_stone, 1)
        user_boss_fight_info = get_user_boss_fight_info(user_id)
        user_boss_fight_info['boss_integral'] += boss_integral
        save_user_boss_fight_info(user_id, user_boss_fight_info)

        msg = f"恭喜道友击败{boss_info['name']}，收获灵石{get_stone}枚，{more_msg}获得世界积分：{boss_integral}点"

    # try:
    #     await send_forward_msg_list(bot, event, result)
    # except ActionFailed:
    #     msg += "Boss战消息发送错,可能被风控!"

    msg_list = []
    for item in result:
        msg_list.append(item["data"]["content"])

    await xiuxian_send_group_img_message(event.group_id, msg_list)
    await xiuxian_send_message(battle, message=msg)


@boss_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_info_(_: Bot, event: GroupMessageEvent):
    group_id = str(event.group_id)
    is_in_group = is_in_groups(event)
    if not is_in_group:  # 不在配置表内
        msg = f'本群尚未开启世界Boss,请联系管理员开启!'
        await xiuxian_send_message(create, message=msg)

    boss_list = None
    try:
        boss_list = group_boss[group_id]
    except:
        pass

    if not boss_list:
        msg = f'本群尚未生成世界Boss,请等待世界boss刷新!'
        await xiuxian_send_message(create, message=msg)

    message = str(event.message)
    boss_num = re.findall("\d+", message)  # boss编号

    is_fetch_one_boss = False  # True 查对应Boss
    if boss_num:
        boss_num = int(boss_num[0])
        index = len(group_boss[group_id])
        if not (0 < boss_num <= index):
            msg = f'请输入正确的世界Boss编号!'
            await xiuxian_send_message(create, message=msg)
        is_fetch_one_boss = True

    boss_msg = ""
    if is_fetch_one_boss:  # 查单个Boss信息
        boss = group_boss[group_id][boss_num - 1]
        boss_msg = f'''
世界Boss:{boss['name']}
境界：{boss['jj']}
剩余血量：{number_to(boss['气血'])}
攻击：{number_to(boss['攻击'])}
携带灵石：{boss['stone']}
        '''
        msg = boss_msg
        await xiuxian_send_message(boss_info, message=msg)
    else:
        i = 1
        for boss in boss_list:
            boss_msg += (f"{i}.【{boss['jj']}{boss['name']}】 "
                         f"血量：{number_to(boss['气血'])} "
                         f"攻击：{number_to(boss['攻击'])} "
                         f"携带灵石：{boss['stone']}\n")
            i += 1
        msg = boss_msg
        await xiuxian_send_message(boss_info, message=msg)


@create.handle(parameterless=[Cooldown(at_sender=True)])
async def create_(_: Bot, event: GroupMessageEvent):
    """
    生成世界boss
    """
    group_id = str(event.group_id)
    is_in_group = is_in_groups(event)
    if not is_in_group:  # 不在配置表内
        msg = f'本群尚未开启世界Boss,请联系管理员开启!'
        await xiuxian_send_message(create, message=msg)

    boss_info = createboss_root()
    if group_id not in group_boss:
        group_boss[group_id] = []

    if len(group_boss[group_id]) >= config['Boss个数上限']:
        msg = f"本群世界Boss已达到上限{config['Boss个数上限']}个，无法继续生成"
        await xiuxian_send_message(create, message=msg)

    group_boss[group_id].append(boss_info)
    msg = f"已生成{boss_info['jj']}Boss:{boss_info['name']},诸位道友请击败Boss获得奖励吧!"
    await xiuxian_send_message(create, message=msg)


@set_group_boss.handle(parameterless=[Cooldown(at_sender=True)])
async def set_group_boss_(_: Bot, event: GroupMessageEvent):
    """
    世界boss开启关闭
    """
    message = str(event.message)
    mode = message[6:]
    group_id = str(event.group_id)
    is_in_group = is_in_groups(event)  # True在，False不在

    if mode == '开启':
        if is_in_group:
            msg = f'本群已开启世界Boss,请勿重复开启!'
            await xiuxian_send_message(set_group_boss, message=msg)

        else:
            info = {
                str(group_id): {
                    "hours": config['Boss生成时间参数']["hours"],
                    "minutes": config['Boss生成时间参数']["minutes"]
                }
            }
            config['open'].update(info)
            savef(config)
            msg = f'已开启本群世界Boss!'
            await xiuxian_send_message(set_group_boss, message=msg)

    elif mode == '关闭':
        if is_in_group:
            try:
                del config['open'][str(group_id)]
            except:
                pass
            savef(config)
            msg = f'已关闭本群世界Boss!'
            await xiuxian_send_message(set_group_boss, message=msg)

        else:
            msg = f'本群未开启世界Boss!'
            await xiuxian_send_message(set_group_boss, message=msg)

    elif mode == '':
        if str(group_id) in groups:
            msg = __boss_help__ + "非指令:1、拥有定时任务:每{}小时{}分钟生成一只随机大境界的世界Boss".format(
                groups[str(group_id)]["hours"], groups[str(group_id)]["minutes"]
            )
        else:
            msg = __boss_help__
        await xiuxian_send_message(set_group_boss, message=msg)
    else:
        msg = f'请输入正确的指令:世界boss开启或关闭!'
        await xiuxian_send_message(set_group_boss, message=msg)


@boss_integral_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_integral_info_(bot: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()
    if not is_in_groups(event):  # 不在配置表内
        msg = f'本群尚未开启世界Boss,请联系管理员开启!'
        await xiuxian_send_message(boss_integral_info, message=msg)

    user_boss_fight_info = get_user_boss_fight_info(user_id)
    boss_integral_shop = config['世界积分商品']
    l_msg = [f"道友目前拥有的世界积分：{user_boss_fight_info['boss_integral']}点"]
    if boss_integral_shop != {}:
        for k, v in boss_integral_shop.items():
            msg = f"编号:{k}\n"
            msg += f"描述：{v['desc']}\n"
            msg += f"所需世界积分：{v['cost']}点"
            l_msg.append(msg)
    else:
        l_msg.append(f"世界积分商店内空空如也！")

    msg = ""
    for item in l_msg:
        msg += item + "\n"
    await xiuxian_send_message(boss_integral_info, message=msg)


@boss_integral_use.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def boss_integral_use_(_: Bot, event: GroupMessageEvent):
    user_id = event.get_user_id()
    message = str(event.message)
    shop_num = re.findall("\d+", message)  # boss编号

    is_in_group = is_in_groups(event)
    if not is_in_group:  # 不在配置表内
        msg = f'本群尚未开启世界Boss,请联系管理员开启!'
        await xiuxian_send_message(boss_integral_use, message=msg)

    if shop_num:
        shop_num = int(shop_num[0])
    else:
        msg = f'指令错误，请输入【世界积分兑换+编号】！'
        await xiuxian_send_message(boss_integral_use, message=msg)

    boss_integral_shop = config['世界积分商品']
    is_in = False
    cost = None
    shop_id = None
    if boss_integral_shop != {}:
        for k, v in boss_integral_shop.items():
            if shop_num == int(k):
                is_in = True
                cost = v['cost']
                shop_id = v['id']
                break
            else:
                continue
    else:
        msg = f"世界积分商店内空空如也！"
        await xiuxian_send_message(boss_integral_use, message=msg)

    if not is_in:
        msg = f"该编号不在商品列表内哦，请检查后再兑换"
        await xiuxian_send_message(boss_integral_use, message=msg)

    user_boss_fight_info = get_user_boss_fight_info(user_id)
    if user_boss_fight_info['boss_integral'] < cost:
        msg = f"道友的世界积分不满足兑换条件呢"
        await xiuxian_send_message(boss_integral_use, message=msg)

    else:
        user_boss_fight_info['boss_integral'] -= cost
        save_user_boss_fight_info(user_id, user_boss_fight_info)
        item_info = Items().get_data_by_item_id(shop_id)
        sql_message.send_back(user_id, shop_id, item_info['name'], item_info['type'], 1)
        msg = f"道友成功兑换获得：{item_info['name']}"
        await xiuxian_send_message(boss_integral_use, message=msg)
