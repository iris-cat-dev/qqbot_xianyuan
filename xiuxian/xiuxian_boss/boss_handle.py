import random

from .boss_data_source import BossConfig, BossGameData, BossPlayerData
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.player_fight import user_info_to_player_info, boss_info_to_player_info, boss_fight, \
    player_info_to_boss_info
from ..common.rank import Rank
from ..common.utils import number_to
from ..common.xiuxian2_handle import items

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
        # 保底机制获取一个最低境界活跃的用户，生成一个同境boss
        last_user = sql_manager.get_last_user(only_active=True)
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
            boss_rank_info = rank.get_big_rank_info(user_info.level)
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


def get_random_goods(user_id):
    goods_id_list = [1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109]
    item_id = random.choice(goods_id_list)
    item_info = items.get_data_by_item_id(item_id)
    item_msg = f"【{item_info['level']}:{item_info['name']}】"
    sql_manager.insert_backpack(user_id, item_id, item_info['name'], item_info['type'], 1)
    return item_msg


async def handle_boss_fight(user_id, boss_num):
    user_info = sql_manager.get_user_info(user_id)
    boss_info = boss_data.boss_list[boss_num - 1]

    boss_info_old = boss_info
    boss_all_hp = boss_info_old['max_hp']
    boss_old_hp = boss_info_old["hp"]

    boss_magnification = boss_config.boss_magnification
    low_level_battle_mode = False
    msg = ""
    if rank.compare_big_rank(boss_info_old['rank'], user_info.level) == -1:
        # convent to same rank battle
        low_level_battle_mode = True
        boss_rank_info = rank.get_rank_info(user_info.level)
        boss_info["hp"] = int(boss_info["hp"] / boss_info["max_hp"] * boss_rank_info["exp"] * boss_magnification["hp"])
        boss_info["max_hp"] = int(boss_rank_info["exp"] * boss_magnification["hp"])
        boss_info["atk"] = int(boss_rank_info["exp"] * boss_magnification["atk"])
        msg = (f"警告！道友的境界超过邪魔！邪魔境界提升至{user_info.level}! "
               f'血量:{number_to(boss_info["hp"])} '
               f'攻击:{number_to(boss_info["atk"])}\n')

    player_info1 = user_info_to_player_info(user_info)
    player_info2 = boss_info_to_player_info(boss_info)
    battle_list, victor, boss_info_new, get_stone = await boss_fight(player_info1, player_info2, bot_id=0)
    boss_info_new = player_info_to_boss_info(boss_info_new)

    if low_level_battle_mode:
        # convent to same rank battle
        boss_rank_info = rank.get_rank_info(boss_info_old['rank'])
        boss_info_new["hp"] = int(
            boss_info_new["hp"] / boss_info_new["max_hp"] * boss_rank_info["exp"] * boss_magnification["hp"])
        boss_info_new["max_hp"] = int(boss_rank_info["exp"] * boss_magnification["hp"])
        boss_info_new["atk"] = int(boss_rank_info["exp"] * boss_magnification["atk"])

    boss_now_hp = boss_info_new['hp']
    boss_level_index = rank.to_level_index(boss_info_old['rank'])
    boss_total_point = 30 + boss_level_index * 2

    boss_point = int((boss_old_hp - boss_now_hp) / boss_all_hp * boss_total_point)
    if boss_point < 2:
        boss_point = 2

    boss_player_data = BossPlayerData(user_id)
    boss_player_data.point += boss_point
    boss_player_data.save()

    get_stone = boss_info_old["stone"] - boss_info_new['stone']
    get_exp = get_stone // 3
    sql_manager.add_money(user_id, get_stone)
    sql_manager.add_exp(user_id, get_exp)

    goods_msg = "无"
    if victor == "Boss赢了":
        boss_data.boss_list[boss_num - 1] = boss_info_new
        msg += f"道友不敌邪魔【{boss_info['name']}】，重伤逃遁，剩余血量({boss_now_hp}/{boss_all_hp})\n"
    else:
        boss_data.boss_list.remove(boss_data.boss_list[boss_num - 1])
        msg += f"恭喜道友击败邪魔【{boss_info['name']}】\n"
        goods_msg = get_random_goods(user_id)

    msg += (f"收获奖励：\n"
            f"灵石:{get_stone}枚\n"
            f"修为:{get_exp}点\n"
            f"世界积分:{boss_point}点\n"
            f"获得物品:{goods_msg}")

    boss_data.save()
    return msg, battle_list
