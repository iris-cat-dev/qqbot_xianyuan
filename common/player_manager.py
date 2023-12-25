from .game_sql_manager import XiuxianSqlManager
from .rank import Rank
from .read_buff import UserBuffDate
from .root import Root
from ..xiuxian_config import XiuConfig

sql_manager = XiuxianSqlManager()

root = Root()
rank = Rank()


def get_player_list():
    pass


def get_cultivation_rate(user_id: int):
    user_info = sql_manager.get_user_info(user_id)
    root_rate = root.get_root_speed(user_info.root_type)  # 灵根倍率
    level_rate = rank.get_rank_speed(user_info.level)  # 境界倍率

    user_buff_data = UserBuffDate(user_id)
    main_buff_data = user_buff_data.get_user_main_buff_data()
    main_buff_rate = main_buff_data['ratebuff'] if main_buff_data is not None else 0  # 功法
    blessed_spot_rate = user_buff_data.BuffInfo.blessed_spot

    return {
        "total": root_rate * level_rate * (1 + main_buff_rate + blessed_spot_rate),
        "root_rate": root_rate,
        "level_rate": level_rate,
        "main_buff_rate": main_buff_rate,
        "blessed_spot_rate": blessed_spot_rate
    }


def get_total_hp(user_id: int) -> int:
    user_info = sql_manager.get_user_info(user_id)
    user_buff_data = UserBuffDate(user_id)
    main_buff_data = user_buff_data.get_user_main_buff_data()
    main_buff_rate = main_buff_data['hpbuff'] if main_buff_data is not None else 0
    return int(user_info.exp * (1 + main_buff_rate))


def get_total_mp(user_id: int) -> int:
    user_info = sql_manager.get_user_info(user_id)
    user_buff_data = UserBuffDate(user_id)
    main_buff_data = user_buff_data.get_user_main_buff_data()
    main_buff_rate = main_buff_data['mpbuff'] if main_buff_data is not None else 0
    return int(user_info.exp // 2 * (1 + main_buff_rate))


def get_attack_info(user_id: int) -> dict:
    user_info = sql_manager.get_user_info(user_id)
    user_buff = UserBuffDate(user_info.user_id)
    user_weapon_data = user_buff.get_user_weapon_data()
    if user_weapon_data is not None:
        weapon_attack = user_weapon_data["atk_buff"]
    else:
        weapon_attack = 0

    main_buff_data = user_buff.get_user_main_buff_data()
    main_buff_attack = main_buff_data['atkbuff'] if main_buff_data is not None else 0

    buff_info = user_buff.BuffInfo  # 丹药 buff
    atk_practice = user_info.atkpractice * 4 / 100  # 攻击修炼
    return {
        "total": int((user_info.atk + buff_info.atk_buff) * (1 + main_buff_attack + atk_practice + weapon_attack)),
        "base_atk": user_info.atk,
        "atk_buff": buff_info.atk_buff,
        "atk_practice": atk_practice,
        "main_buff_attack": main_buff_attack,
        "weapon_attack": weapon_attack,
    }


def get_total_attack(user_id: int) -> int:
    attack_info = get_attack_info(user_id)
    return attack_info["total"]


def get_total_defense(user_id: int):
    user_info = sql_manager.get_user_info(user_id)
    user_armor_data = UserBuffDate(user_info.user_id).get_user_armor_buff_data()
    if user_armor_data is not None:
        armor_defense = int(user_armor_data["def_buff"] * 100)
    else:
        armor_defense = 0
    return armor_defense


def get_total_critical(user_id: int):
    user_buff = UserBuffDate(user_id)
    user_weapon_data = user_buff.get_user_weapon_data()
    if user_weapon_data is not None:
        crit_buff = int(user_weapon_data['crit_buff'] * 100)
    else:
        crit_buff = 1
    return crit_buff


def check_user_state(user_id, need_type):
    """
    :说明: `check_user_type`
    > 匹配用户状态，返回是否状态一致
    :返回参数:
      * `isType: 是否一致
      * `msg: 消息体
    """
    is_type = False
    msg = ''
    cd_info = sql_manager.get_user_cd(user_id)
    if cd_info is None:
        user_type = 0
    else:
        user_type = cd_info.type

    if user_type == need_type:  # 状态一致
        is_type = True
    else:
        if user_type == 1:
            msg = "道友现在在闭关呢，小心走火入魔！"

        elif user_type == 2:
            msg = "道友现在在做悬赏令呢，分身乏术！"

        elif user_type == 3:
            msg = "道友现在正在秘境中，分身乏术！"

        elif user_type == 0:
            msg = "道友正在发呆！呆呆呆呆呆呆～"


    return is_type, msg


def leave_harm_time(user_id):
    hp_speed = 25
    user_info = sql_manager.get_user_info(user_id)  # 获取用户信息
    level = user_info.level
    level_rate = root.get_root_speed(user_info.root_type)  # 灵根倍率
    realm_rate = Rank().get_rank_speed(level)  # 境界倍率
    user_buff_data = UserBuffDate(user_id)
    mainbuffdata = UserBuffDate(user_id).get_user_main_buff_data()
    mainbuffratebuff = mainbuffdata['ratebuff'] if mainbuffdata != None else 0  # 功法修炼倍率
    try:
        time = int(((user_info.exp / 10) - user_info.hp) / ((XiuConfig().closing_exp * level_rate * realm_rate * (
                1 + mainbuffratebuff)) * hp_speed))
    except:
        time = "无穷大"
    return time
