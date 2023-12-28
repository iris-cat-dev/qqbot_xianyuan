from ..common.game_sql_manager import XiuxianSqlManager

sql_manager = XiuxianSqlManager()


def check_has_blessed_spot(user_id):
    user_info = sql_manager.get_user_info(user_id)
    msg = ""
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送【洞天福地购买】~"
        return False, msg
    return True, msg
