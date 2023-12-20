from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent, MessageSegment

from .draw_user_info import draw_user_info_img
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_img_message
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import check_player, Cooldown
from ..common.player_manager import get_cultivation_rate, get_total_hp, get_total_mp, get_total_attack, \
    get_total_critical, get_total_defense, get_attack_info
from ..common.rank import Rank
from ..common.root import Root
from ..common.read_buff import UserBuffDate
from ..common.utils import number_to
from ..common.xiuxian2_handle import XiuxianDateManage
from ..xiuxian_config import XiuConfig
from ..xiuxian_sect import SectConfig

xiuxian_message = on_fullmatch("我的修仙信息", priority=23, permission=GROUP, block=True)
mind_state = on_fullmatch("我的状态", priority=7, permission=GROUP, block=True)
xiuxian_stone = on_fullmatch("我的灵石", priority=4, permission=GROUP, block=True)
cultivation_rate = on_fullmatch("我的修炼效率", priority=4, permission=GROUP, block=True)
my_attack = on_fullmatch("我的攻击力", priority=4, permission=GROUP, block=True)

sql_message = XiuxianDateManage()
sql_manager = XiuxianSqlManager()

root = Root()
rank = Rank()


@xiuxian_message.handle(parameterless=[Cooldown(cd_time=XiuConfig().user_info_cd, at_sender=True), check_player()])
async def xiuxian_message_(_: Bot, event: GroupMessageEvent):
    """
    我的修仙信息
    """
    user_id = event.get_user_id()
    user_info = sql_message.get_user_real_info(user_id)
    user_name = user_info.user_name
    user_num = user_info.id
    rank_ = sql_message.get_exp_rank(user_id)
    user_rank = int(rank_[0])
    stone = sql_message.get_stone_rank(user_id)
    user_stone = int(stone[0])
    if user_name:
        pass
    else:
        user_name = "无名氏(发送【改名+道号】更新)"

    root_speed = root.get_root_speed(user_info.root_type)  # 灵根倍率
    realm_rate = Rank().get_rank_speed(user_info.level)  # 境界倍率
    sect_id = user_info.sect_id
    if sect_id:
        sect_info = sql_message.get_sect_info(sect_id)
        sectmsg = sect_info.sect_name
        sectzw = SectConfig().sect_config_data()[f"{user_info.sect_position}"]["title"]
    else:
        sectmsg = '无宗门'
        sectzw = '无'

    # 判断突破的修为
    if rank.is_max(user_info.level):
        exp_meg = "位面至高"
    else:
        need_exp = rank.get_rank_info(user_info.level, 1)["exp"]
        get_exp = need_exp - user_info.exp
        if get_exp > 0:
            exp_meg = f"还需{number_to(get_exp)}修为可突破！"
        else:
            exp_meg = "可突破！"

    user_buff_data = UserBuffDate(user_id)
    user_main_buff_date = user_buff_data.get_user_main_buff_data()
    user_sec_buff_date = user_buff_data.get_user_sec_buff_data()
    user_weapon_data = user_buff_data.get_user_weapon_data()
    user_armor_data = user_buff_data.get_user_armor_buff_data()
    main_buff_name = '无'
    sec_buff_name = '无'
    weapon_name = '无'
    armor_name = '无'
    if user_main_buff_date is not None:
        main_buff_name = f"{user_main_buff_date['name']}({user_main_buff_date['level']})"
    if user_sec_buff_date is not None:
        sec_buff_name = f"{user_sec_buff_date['name']}({user_sec_buff_date['level']})"
    if user_weapon_data is not None:
        weapon_name = f"{user_weapon_data['name']}({user_weapon_data['level']})"
    if user_armor_data is not None:
        armor_name = f"{user_armor_data['name']}({user_armor_data['level']})"

    level_rate = rank.get_rank_rate(user_info.level)
    DETAIL_MAP = {
        '道号': f'{user_name}',
        '境界': f'{user_info.level}',
        '修为': f'{number_to(user_info.exp)}',
        '灵石': f'{user_info.stone}',
        '战力': f'{number_to(int(user_info.exp * root_speed * realm_rate))}',
        '灵根': f'{user_info.root}({user_info.root_type}+{int(root_speed * 100)}%)',
        '突破': f'{exp_meg}概率：{level_rate + int(user_info.level_up_rate)}%',
        '宗门': sectmsg,
        '宗门职位': sectzw,
        '功法': main_buff_name,
        '神通': sec_buff_name,
        "法器": weapon_name,
        "防具": armor_name,
        '注册位数': f'道友是踏入修仙世界的第{int(user_num)}人',
        '修为排行': f'道友的修为排在第{int(user_rank)}位',
        '灵石排行': f'道友的灵石排在第{int(user_stone)}位',
    }
    if XiuConfig().user_info_image:
        img_res = await draw_user_info_img(user_id, DETAIL_MAP)
        await xiuxian_send_img_message(xiuxian_message, img_res)


@mind_state.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def mind_state_(bot: Bot, event: GroupMessageEvent):
    """
    我的状态信息
    """
    user_info = sql_manager.get_user_info(event.user_id)
    user_id = user_info.user_id

    if user_info.hp is None or user_info.hp == 0 or user_info.hp == 0:
        sql_message.update_user_hp(user_id)

    level_up_rate = rank.get_rank_rate(user_info.level)  # 对应境界突破的概率
    user_level_uprate = int(user_info.level_up_rate)  # 用户失败次数加成
    cultivation_rate_info = get_cultivation_rate(event.user_id)

    total_hp = get_total_hp(user_id)
    total_mp = get_total_mp(user_id)
    total_attack = get_total_attack(user_id)
    total_critical = get_total_critical(user_id)
    total_defense = get_total_defense(user_id)

    msg = f"""道号: {user_info.user_name}
气血: {number_to(user_info.hp)}/{number_to(total_hp)}
真元: {number_to(user_info.mp)}/{number_to(total_mp)}
攻击: {number_to(total_attack)}
攻击修炼: {user_info.atkpractice}级(提升攻击力{user_info.atkpractice * 4}%)
会心: {total_critical}%
减伤率: {total_defense}%
会心伤害增益: {int(1.5 * 100)}%
修炼效率: {int(cultivation_rate_info["total"] * 100)}%
突破概率：{level_up_rate + user_level_uprate}%
"""
    await xiuxian_send_message(mind_state, message=msg)


@xiuxian_stone.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def xiuxian_stone_(_: Bot, event: GroupMessageEvent):
    """
    我的灵石信息
    """
    user_info = sql_manager.get_user_info(event.user_id)
    msg = f"道友当前身上灵石：{user_info.stone}"
    await xiuxian_send_message(xiuxian_stone, msg)


@cultivation_rate.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def cultivation_rate_(_: Bot, event: GroupMessageEvent):
    """
    我的修炼速度
    """
    info = get_cultivation_rate(event.user_id)
    msg = (f"道友当前修炼速度: {int(info['total'] * 100)}%\n"
           f"灵根: +{int(info['root_rate'] * 100)}%\n"
           f"境界: +{int(info['level_rate'] * 100)}%\n"
           f"功法: +{int(info['main_buff_rate'] * 100)}%\n"
           f"洞天福地: +{int(info['blessed_spot_rate'] * 100)}%")
    await xiuxian_send_message(xiuxian_stone, msg)


@my_attack.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def my_attack_(_: Bot, event: GroupMessageEvent):
    """
    我的攻击力
    """
    info = get_attack_info(event.user_id)
    msg = (f"道友攻击力: {info['total']}\n"
           f"基础攻击: +{info['base_atk']}\n"
           f"丹药加成: +{info['atk_buff']}\n"
           f"攻击修炼: +{int(info['atk_practice'] * 100)}%\n"
           f"功法加成: +{int(info['main_buff_attack'] * 100)}%\n"
           f"武器加成: +{int(info['weapon_attack'] * 100)}%"
           )
    await xiuxian_send_message(xiuxian_stone, msg)
