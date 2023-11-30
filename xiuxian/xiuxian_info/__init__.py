from nonebot import on_fullmatch
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent, MessageSegment

from .draw_user_info import draw_user_info_img
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_img_message
from ..common.param_checker import check_player
from ..data_source import jsondata
from ..lay_out import Cooldown
from ..read_buff import UserBuffDate
from ..utils import check_user, number_to
from ..xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import XiuConfig

xiuxian_message = on_fullmatch("我的修仙信息", priority=23, permission=GROUP, block=True)
mind_state = on_fullmatch("我的状态", priority=7, permission=GROUP, block=True)
xiuxian_stone = on_fullmatch("我的灵石", priority=4, permission=GROUP, block=True)

sql_message = XiuxianDateManage()



@xiuxian_message.handle(parameterless=[Cooldown(cd_time=XiuConfig().user_info_cd, at_sender=True), check_player()])
async def xiuxian_message_(bot: Bot, event: GroupMessageEvent):
    """
    我的修仙信息
    """
    user_id = event.get_user_id()
    user_info = sql_message.get_user_real_info(user_id)
    user_name = user_info.user_name
    user_num = user_info.id
    rank = sql_message.get_exp_rank(user_id)
    user_rank = int(rank[0])
    stone = sql_message.get_stone_rank(user_id)
    user_stone = int(stone[0])
    if user_name:
        pass
    else:
        user_name = "无名氏(发送改名+道号更新)"

    level_rate = sql_message.get_root_rate(user_info.root_type)  # 灵根倍率
    realm_rate = jsondata.level_data()[user_info.level]["spend"]  # 境界倍率
    sect_id = user_info.sect_id
    if sect_id:
        sect_info = sql_message.get_sect_info(sect_id)
        sectmsg = sect_info.sect_name
        sectzw = jsondata.sect_config_data()[f"{user_info.sect_position}"]["title"]
    else:
        sectmsg = '无宗门'
        sectzw = '无'

    # 判断突破的修为
    list_all = len(OtherSet().level) - 1
    now_index = OtherSet().level.index(user_info.level)
    if list_all == now_index:
        exp_meg = "位面至高"
    else:
        is_updata_level = OtherSet().level[now_index + 1]
        need_exp = sql_message.get_level_power(is_updata_level)
        get_exp = need_exp - user_info.exp
        if get_exp > 0:
            exp_meg = "还需{}修为可突破！".format(number_to(get_exp))
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

    DETAIL_MAP = {
        '道号': f'{user_name}',
        '境界': f'{user_info.level}',
        '修为': f'{number_to(user_info.exp)}',
        '灵石': f'{user_info.stone}',
        '战力': f'{number_to(int(user_info.exp * level_rate * realm_rate))}',
        '灵根': f'{user_info.root}({user_info.root_type}+{int(level_rate * 100)}%)',
        '突破状态': f'{exp_meg}概率：{jsondata.level_rate_data()[user_info.level] + int(user_info.level_up_rate)}%',
        '攻击力': f'{number_to(user_info.atk)}，攻修等级{user_info.atkpractice}级',
        '所在宗门': sectmsg,
        '宗门职位': sectzw,
        '主修功法': main_buff_name,
        '副修神通': sec_buff_name,
        "法器": weapon_name,
        "防具": armor_name,
        '注册位数': f'道友是踏入修仙世界的第{int(user_num)}人',
        '修为排行': f'道友的修为排在第{int(user_rank)}位',
        '灵石排行': f'道友的灵石排在第{int(user_stone)}位',
    }
    if XiuConfig().user_info_image:
        img_res = await draw_user_info_img(user_id, DETAIL_MAP)
        await xiuxian_send_img_message(xiuxian_message, img_res)

    else:
        try:
            msg = f"""{user_name}道友的信息
灵根为：{user_info.root}({user_info.root_type}+{int(level_rate * 100)}%)
当前境界：{user_info.level}(境界+{int(realm_rate * 100)}%)
当前灵石：{number_to(user_info.stone)}
当前修为：{number_to(user_info.exp)}(修炼效率+{int((level_rate * realm_rate) * 100)}%)
当前主修功法为：{user_main_buff_date['name']}({user_main_buff_date['level']})
当前副修神通为：{user_sec_buff_date['name']}({user_sec_buff_date['level']})
你的战力为：{number_to(int(user_info.exp * level_rate * realm_rate))}
你的攻击力为{number_to(user_info.atk)}，攻修等级{user_info.atkpractice}级
你是踏入修仙世界的第{int(user_num)}人
你的修为排在第{int(user_rank)}位
你的灵石排在第{int(user_stone)}位"""
            await xiuxian_send_message(xiuxian_message, message=msg)

        except TypeError:
            msg = f"""{user_name}道友的信息
灵根为：{user_info.root}({user_info.root_type}+{int(level_rate * 100)}%)
当前境界：{user_info.level}(境界+{int(realm_rate * 100)}%)
当前灵石：{number_to(user_info.stone)}
当前修为：{number_to(user_info.exp)}(修炼效率+{int((level_rate * realm_rate) * 100)}%)
你的战力为：{number_to(int(user_info.exp * level_rate * realm_rate))}
你的攻击力为{number_to(user_info.atk)}，攻修等级{user_info.atkpractice}级
你是踏入修仙世界的第{int(user_num)}人
你的修为排在第{int(user_rank)}位
你的灵石排在第{int(user_stone)}位"""
            await xiuxian_send_message(xiuxian_message, message=msg)


@mind_state.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def mind_state_(bot: Bot, event: GroupMessageEvent):
    """
    我的状态信息
    """
    isUser, user_info, msg = check_user(event)
    user_id = user_info.user_id

    if user_info.hp is None or user_info.hp == 0 or user_info.hp == 0:
        sql_message.update_user_hp(user_id)
    user_info = sql_message.get_user_real_info(user_id)

    level_rate = sql_message.get_root_rate(user_info.root_type)  # 灵根倍率
    realm_rate = jsondata.level_data()[user_info.level]["spend"]  # 境界倍率
    user_buff_data = UserBuffDate(user_id)
    main_buff_data = user_buff_data.get_user_main_buff_data()
    user_weapon_data = user_buff_data.get_user_weapon_data()
    if user_weapon_data is not None:
        crit_buff = int(user_weapon_data['crit_buff'] * 100)
    else:
        crit_buff = 1

    user_armor_data = user_buff_data.get_user_armor_buff_data()
    if user_armor_data is not None:
        def_buff = int(user_armor_data['def_buff'] * 100)
    else:
        def_buff = 0

    main_buff_rate_buff = main_buff_data['ratebuff'] if main_buff_data is not None else 0
    main_hp_buff = main_buff_data['hpbuff'] if main_buff_data is not None else 0
    main_mp_buff = main_buff_data['mpbuff'] if main_buff_data is not None else 0
    impart_data = None
    impart_hp_per = impart_data.impart_hp_per if impart_data is not None else 0
    impart_mp_per = impart_data.impart_mp_per if impart_data is not None else 0
    impart_know_per = impart_data.impart_know_per if impart_data is not None else 0
    impart_burst_per = impart_data.impart_burst_per if impart_data is not None else 0
    boss_atk = impart_data.boss_atk if impart_data is not None else 0

    level_up_rate = jsondata.level_rate_data()[user_info.level]  # 对应境界突破的概率
    user_level_uprate = int(user_info.level_up_rate)  # 用户失败次数加成

    msg = f"""道号: {user_info.user_name}
气血: {number_to(user_info.hp)}/{number_to(int((user_info.exp / 2) * (1 + main_hp_buff + impart_hp_per)))}
真元: {int((user_info.mp / user_info.exp) * 100)}%
攻击: {number_to(user_info.atk)}
攻击修炼: {user_info.atkpractice}级(提升攻击力{user_info.atkpractice * 4}%)
修炼效率: {int(((level_rate * realm_rate) * (1 + main_buff_rate_buff)) * 100)}%
会心: {crit_buff + int(impart_know_per * 100)}%
减伤率: {def_buff}%
boss战增益: {int(boss_atk * 100)}%
会心伤害增益: {int((1.5 + impart_burst_per) * 100)}%
突破概率：{level_up_rate + user_level_uprate}%
"""
    await xiuxian_send_message(mind_state, message=msg)


@xiuxian_stone.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def xiuxian_stone_(bot: Bot, event: GroupMessageEvent):
    """
    我的灵石信息
    """
    _, user_info, _ = check_user(event)
    msg = f"道友当前身上灵石：{user_info.stone}"
    await xiuxian_send_message(xiuxian_stone, msg)
