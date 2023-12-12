import random

from .boss_data_source import BossConfig, BossGameData
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.rank import Rank

sql_manager = XiuxianSqlManager()
rank = Rank()
boss_config = BossConfig()
boss_data = BossGameData()


def check_group_open_boss(group_id):
    if group_id in boss_data.group_list:
        return True, ""
    else:
        return False, "本群尚未开启世界Boss，请联系管理员开启，输入【世界boss开启】!"


def check_input_boss(boss_id) -> (True, str):
    if len(boss_data.boss_list) == 0:
        return False, f'本群尚未生成世界Boss，请等待世界boss刷新!'

    index = len(boss_data.boss_list)
    if not (0 < boss_id <= index):
        return False, '请输入正确的世界Boss编号!'

    return True, ""


def create_boss(boss_rank: str = None):
    if boss_rank is None:
        # 保底机制获取一个最低境界的用户，生成一个同境boss
        last_user = sql_manager.get_last_user()
        last_user_rank_info = rank.get_rank_info(last_user.level)
        # 判断是否存在最低境界 boss
        has_last_level_boss = False
        for boss in boss_data.boss_list:
            if boss["rank"] == last_user_rank_info["name"]:
                has_last_level_boss = True
                break
        if has_last_level_boss:
            # 如果存在随机抽取一个玩家相同境界
            user_list = sql_manager.get_user_list()
            user_id = random.choice(user_list)
            user_info = sql_manager.get_user_info(user_id)
            boss_rank_info = rank.get_rank_info(user_info.level)
        else:
            boss_rank_info = last_user_rank_info
    else:
        boss_rank_info = rank.get_big_rank_info(boss_rank)

    exp = boss_rank_info["exp"]
    # 生成 boss 倍率对应参数
    boss_magnification = boss_config.boss_magnification
    boss_info = {
        'hp': int(exp * boss_magnification["hp"]),
        'max_hp': int(exp * boss_magnification["hp"]),
        'mp': int(exp * boss_magnification["mp"]),
        'atk': int(exp * boss_magnification["atk"]),
        'name': random.choice(boss_config.boss_name_list),
        'rank': boss_rank_info["name"],
        "stone": int(exp * boss_magnification["stone"]),
    }
    return boss_info
