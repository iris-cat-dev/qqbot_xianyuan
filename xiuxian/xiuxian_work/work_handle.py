import random

from .work_data_source import WorkPlayerData, RewardConfig, WorkConfig
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.item_json import Items
from ..common.rank import Rank
from ..common.rate_calculater import calculated

item = Items()
sql_manager = XiuxianSqlManager()


def format_work_list(work_list):
    n = 1
    work_msg_f = f"☆------道友的个人悬赏令------☆\n"

    if len(work_list) == 0:
        work_msg_f += "空"
        return work_msg_f

    for i in work_list:
        work_msg_f += f"{n}、{format_work_msg(i)}"
        n += 1
    return work_msg_f


def format_work_msg(work_):
    item_id = work_["item_id"]
    if item_id == 0:
        item_msg = "!"
    else:
        item_info = Items().get_data_by_item_id(item_id)
        item_msg = f"，可能额外获得：{item_info['level']}:{item_info['name']}!"
    msg = f'【{work_["name"]}】，完成机率{work_["rate"]}，基础报酬{work_["exp"]}修为，预计需{work_["time"]}分钟{item_msg}\n'
    return msg


def check_refresh(user_id):
    user_cd = sql_manager.get_user_cd(user_id)
    if not WorkPlayerData(user_id).has_work() and user_cd.type == 2:
        sql_manager.set_user_state(user_id, 0)
        msg = f"悬赏令已更新，已重置道友的状态！"
        return True, msg
    return False, ""


def work_make_list(user_id):
    """
    悬赏令获取
    """
    user_info = sql_manager.get_user_info(user_id)

    work1 = work_make_item(WorkConfig().work1, user_info.level, user_info.exp, user_info.level)
    work2 = work_make_item(WorkConfig().work2, user_info.level, user_info.exp, user_info.level)
    work3 = work_make_item(WorkConfig().work3, user_info.level, user_info.exp, user_info.level)

    work_list = [work1, work2, work3]
    return work_list


def work_check_success(work_data):
    if random.randint(1, 100) <= work_data["rate"]:
        big_success = False
        if work_data["rate"] >= 100:
            big_success = True
        return True, big_success, work_data
    else:
        return False, False, work_data


def work_make_item(work_list, work_level, exp, user_level):
    level_price_data = RewardConfig().level_price_data
    work_level = Rank().to_big_rank(work_level)

    work_list = work_list[work_level]
    work_name_list = []
    for name in work_list:
        work_name_list.append(name)

    work_name = random.choice(work_name_list)
    work_info = work_list[work_name]
    level_price_data = level_price_data[work_level][work_info['level']]
    rate, is_out = work_count_rate(exp, level_price_data["needexp"])
    success_msg = work_info['succeed']
    fail_msg = work_info['fail']
    item_type = get_random_item_type()
    item_id = item.get_random_id_list_by_rank_and_item_type(Rank().to_level(user_level), item_type)

    if not item_id:
        item_id = 0
    else:
        item_id = random.choice(item_id)

    return {
        "name": work_name,
        "rate": rate,
        "exp": level_price_data["award"],
        "item_id": item_id,
        "success_msg": success_msg,
        "failed_msg": fail_msg,
        "time": int(level_price_data["time"] * is_out)
    }


def get_random_item_type():
    type_rate = {
        "功法": {
            "type_rate": 400,
        },
        "神通": {
            "type_rate": 400,
        },
        "丹药": {
            "type_rate": 400,
        }
    }
    temp_dict = {}
    for i, v in type_rate.items():
        try:
            temp_dict[i] = v["type_rate"]
        except:
            continue
    key = [calculated(temp_dict)]
    return key


def work_count_rate(exp, need_exp):
    rate = int(exp / need_exp * 100)
    is_out = 1
    if rate >= 100:
        tp = 1
        flag = True
        while flag:
            r = exp / need_exp * 100
            if r > 100:
                tp += 1
                exp /= 1.5
            else:
                flag = False

        rate = 100
        is_out = float(1 - tp * 0.05)
        if is_out < 0.5:
            is_out = 0.5
    return rate, round(is_out, 2)
