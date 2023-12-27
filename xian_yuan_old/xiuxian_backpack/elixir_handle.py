from ..common.game_sql_manager import XiuxianSqlManager
from ..common.item_json import Items
from ..common.player_manager import get_total_hp, get_total_mp
from ..common.rank import Rank
from ..common.xiuxian2_handle import XiuxianDateManage

items = Items()
rank = Rank()
sql_manager = XiuxianSqlManager()
sql_message = XiuxianDateManage()

def check_use_elixir(user_id, goods_id, num):
    user_info = sql_message.get_user_message(user_id)
    user_rank = rank.to_level(user_info.level)

    goods_info = items.get_data_by_item_id(goods_id)
    goods_rank = goods_info['rank']
    goods_name = goods_info['name']
    back = sql_message.get_item_by_good_id_and_user_id(user_id, goods_id)

    # goods_day_num = back.day_num
    goods_all_num = back.all_num
    if goods_info['buff_type'] == "level_up_rate":  # 增加突破概率的丹药
        if goods_rank < user_rank:  # 最低使用限制
            msg = f"丹药：{goods_name}的最低使用境界为{goods_info['境界']}，道友不满足使用条件"
        elif goods_rank - user_rank > 18:  # 最高使用限制
            msg = f"道友当前境界为：{user_info.level}，丹药：{goods_name}已不能满足道友，请寻找适合道友的丹药吧！"
        else:  # 检查完毕
            sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
            sql_message.update_levelrate(user_id, user_info.level_up_rate + goods_info['buff'] * num)
            msg = f"道友成功使用丹药：{goods_name}{num}颗，下一次突破的成功概率提高{goods_info['buff'] * num}%!"

    elif goods_info['buff_type'] == "level_up_big":  # 增加大境界突破概率的丹药
        if goods_rank != user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}，道友不满足使用条件！"
        else:
            if goods_all_num >= goods_info['all_num']:
                msg = f"道友使用的丹药：{goods_name}已经达到丹药的耐药性上限！已经无法使用该丹药了！"
            else:  # 检查完毕
                sql_message.update_back_j(user_id, goods_id, use_key=1)
                sql_message.update_levelrate(user_id, user_info.level_up_rate + goods_info['buff'])
                msg = f"道友成功使用丹药：{goods_name}1颗,下一次突破的成功概率提高{goods_info['buff']}%!"

    elif goods_info['buff_type'] == "hp":  # 回复状态的丹药
        if goods_rank < user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            user_max_hp = get_total_hp(user_info.user_id)
            user_max_mp = get_total_mp(user_info.user_id)
            if user_info.hp == user_max_hp and user_info.mp == user_max_mp:
                msg = f"道友的状态是满的，用不了哦！"
            else:
                buff = goods_info['buff']
                buff = round((0.016 * user_rank + 0.104) * buff, 2)

                recover_hp = int(buff * user_max_hp * num)
                if user_info.hp + recover_hp > user_max_hp:
                    new_hp = user_max_hp  # 超过最大
                else:
                    new_hp = user_info.hp + recover_hp

                msg = f"道友成功使用丹药：{goods_name}{num}颗，经过境界转化状态恢复了{int(buff * 100 * num)}%!"
                sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
                sql_message.update_user_hp_mp(user_id, new_hp, user_info.mp)

    elif goods_info['buff_type'] == "all":  # 回满状态的丹药
        if goods_rank < user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            user_max_hp = int(user_info.exp / 2)
            user_max_mp = int(user_info.exp)
            if user_info.hp == user_max_hp and user_info.mp == user_max_mp:
                msg = f"道友的状态是满的，用不了哦！"
            else:
                sql_message.update_back_j(user_id, goods_id, use_key=1)
                sql_message.update_user_hp(user_id)
                msg = f"道友成功使用丹药：{goods_name}1颗,状态已全部恢复!"

    elif goods_info['buff_type'] == "atk_buff":  # 永久加攻击buff的丹药
        if goods_rank < user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            buff = goods_info['buff'] * num
            sql_message.updata_user_atk_buff(user_id, buff)
            sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
            msg = f"道友成功使用丹药：{goods_name}{num}颗，攻击力永久增加{buff}点！"

    elif goods_info['buff_type'] == "exp_up":  # 加固定经验值的丹药
        if goods_rank < user_rank:  # 使用限制
            msg = f"丹药：{goods_name}的使用境界为{goods_info['境界']}以上，道友不满足使用条件！"
        else:
            exp = goods_info['buff'] * num
            user_hp = int(user_info.hp + (exp / 2))
            user_mp = int(user_info.mp + exp)
            user_atk = int(user_info.atk + (exp / 10))
            sql_message.update_exp(user_id, exp)
            sql_message.update_power2(user_id)  # 更新战力
            sql_message.update_user_attribute(user_id, user_hp, user_mp, user_atk)  # 这种事情要放在update_exp方法里
            sql_message.update_back_j(user_id, goods_id, num=num, use_key=1)
            msg = f"道友成功使用丹药：{goods_name}{num}颗,修为增加{exp}点！"
    else:
        msg = f"该类型的丹药目前暂时不支持使用！"
    return msg
