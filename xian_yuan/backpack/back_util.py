from datetime import datetime

from ..common.item_json import Items
from ..common.read_buff import (
    UserBuffDate, get_weapon_info_msg,
    get_armor_info_msg, get_sec_msg, get_main_info_msg
)
from ..common.read_buff import get_player_info, save_player_info
from ..common.xiuxian2_handle import XiuxianDateManage

items = Items()
sql_message = XiuxianDateManage()


def check_equipment_can_use(user_id, goods_id):
    """
    装备数据库字段：
        good_type -> '装备'
        state -> 0-未使用， 1-已使用
        goods_num -> '目前数量'
        all_num -> '总数量'
        update_time ->使用的时候更新
        action_time ->使用的时候更新
    判断:
        state = 0, goods_num = 1, all_num =1  可使用
        state = 1, goods_num = 1, all_num =1  已使用
        state = 1, goods_num = 2, all_num =2  已装备，多余的，不可重复使用
    顶用：
    """
    flag = False
    back_equipment = sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    if back_equipment.state == 0:
        flag = True
    return flag


def get_use_equipment_sql(user_id, goods_id):
    """
    使用装备
    返回sql,和法器或防具
    """
    sql_str = []
    item_info = items.get_data_by_item_id(goods_id)
    user_buff_info = UserBuffDate(user_id).BuffInfo
    now_time = datetime.now()
    item_type = ''
    if item_info['item_type'] == "法器":
        item_type = "法器"
        in_use_id = user_buff_info.faqi_buff
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=1 WHERE user_id={user_id} and goods_id={goods_id}")  # 装备
        if in_use_id != 0:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")  # 取下原有的

    if item_info['item_type'] == "防具":
        item_type = "防具"
        in_use_id = user_buff_info.armor_buff
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=1 WHERE user_id={user_id} and goods_id={goods_id}")  # 装备
        if in_use_id != 0:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")  # 取下原有的

    return sql_str, item_type


def get_no_use_equipment_sql(user_id, goods_id):
    """
    卸载装备
    返回sql,和法器或防具
    """
    sql_str = []
    item_info = items.get_data_by_item_id(goods_id)
    user_buff_info = UserBuffDate(user_id).BuffInfo
    now_time = datetime.now()
    item_type = ''
    if item_info['item_type'] == "法器":
        item_type = "法器"
        in_use_id = user_buff_info.faqi_buff
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={goods_id}")  # 卸载装备
        if in_use_id != 0:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")  # 取下原有的

    if item_info['item_type'] == "防具":
        item_type = "防具"
        in_use_id = user_buff_info.armor_buff
        sql_str.append(
            f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={goods_id}")  # 卸载装备
        if in_use_id != 0:
            sql_str.append(
                f"UPDATE back set update_time='{now_time}',action_time='{now_time}',state=0 WHERE user_id={user_id} and goods_id={in_use_id}")  # 取下原有的

    return sql_str, item_type


def check_equipment_use_msg(user_id, goods_id):
    """
    检测装备是否已用
    """
    user_back = sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)
    now_num = user_back.goods_num
    all_num = user_back.all_num
    state = user_back.state
    is_use = False
    if state == 0:
        is_use = False
    if state == 1:
        is_use = True
    return is_use


def takeSecond(elem):
    """
    品阶排序key
    """
    num_dict = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
    try:
        xu_lie = num_dict[elem[0]]
    except:
        xu_lie = 10
    return xu_lie


def get_user_back_msg(user_id):
    """
    获取背包内的所有物品信息
    """
    l_equipment_msg = []
    l_skill_msg = []
    l_elixir_msg = []
    l_yaocai_msg = []
    l_xiulianitem_msg = []
    l_ldl_msg = []
    l_msg = []
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    if user_backs is None:
        return l_msg

    for user_back in user_backs:
        if user_back.goods_type == "装备":
            l_equipment_msg = get_equipment_msg(l_equipment_msg, user_id, user_back.goods_id, user_back.goods_num)

        elif user_back.goods_type == "技能":
            l_skill_msg = get_skill_msg(l_skill_msg, user_id, user_back.goods_id, user_back.goods_num)

        elif user_back.goods_type == "丹药":
            l_elixir_msg = get_elixir_msg(l_elixir_msg, user_back.goods_id, user_back.goods_num)

        elif user_back.goods_type == "聚灵旗":
            l_xiulianitem_msg = get_jlq_msg(l_xiulianitem_msg, user_id, user_back.goods_id, user_back.goods_num)

        elif user_back.goods_type == "炼丹炉":
            l_ldl_msg = get_ldl_msg(l_ldl_msg, user_id, user_back.goods_id, user_back.goods_num)

        elif user_back.goods_type == "药材":
            l_yaocai_msg = get_yaocai_msg(l_yaocai_msg, user_back.goods_id, user_back.goods_num)

    if l_equipment_msg:
        l_msg.append("☆------我的装备------☆")
        for msg in l_equipment_msg:
            l_msg.append(msg)

    if l_skill_msg:
        l_msg.append("☆------拥有技能书------☆")
        for msg in l_skill_msg:
            l_msg.append(msg)

    if l_xiulianitem_msg:
        l_msg.append("☆------修炼物品------☆")
        for msg in l_xiulianitem_msg:
            l_msg.append(msg)

    if l_ldl_msg:
        l_msg.append("☆------炼丹炉------☆")
        for msg in l_ldl_msg:
            l_msg.append(msg)

    if l_elixir_msg:
        l_msg.append("☆------我的丹药------☆")
        for msg in l_elixir_msg:
            l_msg.append(msg)

    if l_yaocai_msg:
        l_msg.append("☆------我的药材------☆")
        l_yaocai_msg.sort(key=takeSecond)
        msg = ""
        for x in l_yaocai_msg:
            msg += x
        l_msg.append(msg)
    return l_msg


def get_yaocai_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的药材信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"{item_info['level']} {item_info['name']} x {goods_num}\n"
    l_msg.append(msg)
    return l_msg


def get_jlq_msg(l_msg, user_id, goods_id, goods_num):
    """
    获取背包内的修炼物品信息，聚灵旗
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\n"
    msg += f"效果：{item_info['desc']}"
    msg += f"\n拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_ldl_msg(l_msg, user_id, goods_id, goods_num):
    """
    获取背包内的炼丹炉信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\n"
    msg += f"效果：{item_info['desc']}"
    msg += f"\n拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_equipment_msg(l_msg, user_id, goods_id, goods_num):
    """
    获取背包内的装备信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = ""
    if item_info['item_type'] == '防具':
        msg = get_armor_info_msg(goods_id, item_info)
    elif item_info['item_type'] == '法器':
        msg = get_weapon_info_msg(goods_id, item_info)
    msg += f"\n拥有数量:{goods_num}"
    is_use = check_equipment_use_msg(user_id, goods_id)
    if is_use:
        msg += f"\n已装备"
    else:
        msg += f"\n可装备"
    l_msg.append(msg)
    return l_msg


def get_skill_msg(l_msg, user_id, goods_id, goods_num):
    """
    获取背包内的技能信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = ""
    if item_info['item_type'] == '神通':
        msg = f"{item_info['level']}神通-{item_info['name']}:"
        msg += get_sec_msg(item_info)
    elif item_info['item_type'] == '功法':
        msg = f"{item_info['level']}功法-"
        msg += get_main_info_msg(goods_id)[1]
    msg += f"\n拥有数量:{goods_num}"
    l_msg.append(msg)
    return l_msg


def get_elixir_msg(l_msg, goods_id, goods_num):
    """
    获取背包内的丹药信息
    """
    item_info = items.get_data_by_item_id(goods_id)
    msg = f"名字：{item_info['name']}\n"
    msg += f"效果：{item_info['desc']}\n"
    msg += f"拥有数量：{goods_num}"
    l_msg.append(msg)
    return l_msg



def get_use_jlq_msg(user_id, goods_id):
    user_info = sql_message.get_user_message(user_id)
    if user_info.blessed_spot_flag == 0:
        msg = f"道友还未拥有洞天福地，无法使用该物品"
    else:
        item_info = items.get_data_by_item_id(goods_id)
        user_buff_data = UserBuffDate(user_id).BuffInfo
        if int(user_buff_data.blessed_spot) >= item_info['修炼速度']:
            msg = f"该聚灵旗的等级不能满足道友的福地了，使用了也没效果"
        else:
            mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
            mix_elixir_info['药材速度'] = item_info['药材速度']
            save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
            sql_message.update_back_j(user_id, goods_id)
            sql_message.updata_user_blessed_spot(user_id, item_info['修炼速度'])
            msg = f"道友洞天福地的聚灵旗已经替换为：{item_info['name']}"
    return msg


def backpack_check_item(user_id: int, goods_name: str):
    item_data = items.get_data_by_item_name(goods_name)
    return backpack_check_item_by_id(user_id, item_data["id"])


def backpack_check_item_by_id(user_id: int, goods_id: int) -> bool:
    user_backs = sql_message.get_back_msg(user_id)
    if user_backs is not None:
        for back in user_backs:
            if int(back.goods_id) == goods_id:  # 检测到有对应丹药
                return True
    return False
