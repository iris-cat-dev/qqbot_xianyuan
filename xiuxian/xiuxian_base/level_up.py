import random
from datetime import datetime

from nonebot import on_fullmatch, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player,Cooldown
from ..common.rank import Rank
from ..common.utils import check_user
from ..common.xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_backpack.back_util import backpack_check_item
from ..xiuxian_config import XiuConfig

level_up = on_fullmatch("突破", priority=6, permission=GROUP, block=True)
level_up_dr = on_fullmatch("渡厄突破", priority=7, permission=GROUP, block=True)
level_up_zj = on_fullmatch("直接突破", priority=7, permission=GROUP, block=True)
user_level_up_rate = on_fullmatch('我的突破概率', priority=5, permission=GROUP, block=True)

sql_message = XiuxianDateManage()
rank = Rank()


def check_cd(user_info):
    level_cd = user_info.level_up_cd
    if level_cd:
        # 校验是否存在 cd
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取 second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果 cd 小于配置的 cd，返回等待时间
            msg = "目前无法突破，还需要{}分钟".format(XiuConfig().level_up_cd - (cd // 60))
            return True, msg
    return False, ""


def check_exp_enough(user_info):
    if rank.is_max(user_info.level):
        msg = "道友已是最高境界，无法突破！"
        return False, msg

    # 判断修为是否足够突破
    next_rank = rank.get_rank_info(user_info.level, 1)
    next_rank_name = next_rank["name"]
    need_exp = next_rank["exp"]
    if user_info.exp < need_exp:
        msg = f"道友的修为不足以突破！距离下次突破需要{need_exp - user_info.exp}修为！突破境界为：{next_rank_name}"
        return False, msg

    return True, ""


@level_up.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def level_up_(_: Bot, event: GroupMessageEvent):
    """
    突破
    """
    _, user_info, msg = check_user(event)
    result, msg = check_cd(user_info)
    if result:
        return await xiuxian_send_message(level_up_zj, message=msg)

    result, msg = check_exp_enough(user_info)
    if not result:
        return await xiuxian_send_message(level_up_zj, message=msg)

    level_name = user_info.level  # 用户境界
    level_rate = rank.get_rank_rate(level_name)  # 对应境界突破的概率

    elixir_name = "渡厄丹"
    user_level_uprate = int(user_info.level_up_rate)
    has = backpack_check_item(user_info.user_id, elixir_name)
    if has:
        msg = (f"由于检测到背包有丹药：{elixir_name}】，本次突破失败将不会损失修为，突破已经准备就绪,"
               f"请发送，【渡厄突破】或【直接突破】来选择是否使用丹药突破！"
               f"本次突破概率为：{level_rate + user_level_uprate}% ")
    else:
        msg = (f"由于检测到背包没有【{elixir_name}】，突破已经准备就绪，"
               f"请发送，【直接突破】来突破！请注意，本次突破失败将会损失部分修为，"
               f"本次突破概率为：{level_rate + user_level_uprate}% ")

    await xiuxian_send_message(level_up, msg)


@level_up_zj.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def level_up_zj_(_: Bot, event: GroupMessageEvent):
    """
    直接 突破
    """
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id
    result, msg = check_cd(user_info)
    if result:
        return await xiuxian_send_message(level_up_zj, message=msg)

    result, msg = check_exp_enough(user_info)
    if not result:
        return await xiuxian_send_message(level_up_zj, message=msg)

    next_rank = rank.get_rank_info(user_info.level, 1)
    next_rank_name = next_rank["name"]
    level_rate = rank.get_rank_rate(user_info.level)  # 对应境界突破的概率
    user_level_uprate = int(user_info.level_up_rate)  # 用户失败次数加成
    total_rate = level_rate + user_level_uprate
    success = True if random.randint(0, 100) < total_rate else False

    if success:
        # 突破成功
        sql_message.updata_level(user_id, next_rank_name)  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        msg = f"恭喜道友突破{next_rank_name}成功"
        await xiuxian_send_message(level_up_zj, message=msg)

    else:
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        # 失败惩罚，随机扣减修为
        percentage = random.randint(XiuConfig().level_punishment_floor, XiuConfig().level_punishment_limit)
        now_exp = int(user_info.exp * (percentage / 100))

        sql_message.update_j_exp(user_id, now_exp)  # 更新用户修为
        now_hp = user_info.hp - (now_exp / 2) if (user_info.hp - (now_exp / 2)) > 0 else 1
        now_mp = user_info.mp - now_exp if (user_info.mp - now_exp) > 0 else 1
        sql_message.update_user_hp_mp(user_id, now_hp, now_mp)  # 修为掉了，血量、真元也要掉

        update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
            level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
        sql_message.update_levelrate(user_id, user_level_uprate + update_rate)
        msg = f"道友突破失败,境界受损,修为减少{now_exp}，下次突破成功率增加{update_rate}%，道友不要放弃！"
        await xiuxian_send_message(level_up_zj, message=msg)


@level_up_dr.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def level_up_dr_(bot: Bot, event: GroupMessageEvent):
    """
    渡厄 突破
    """
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id
    result, msg = check_cd(user_info)
    if result:
        return await xiuxian_send_message(level_up_zj, message=msg)

    result, msg = check_exp_enough(user_info)
    if not result:
        return await xiuxian_send_message(level_up_zj, message=msg)

    elixir_name = "渡厄丹"
    has = backpack_check_item(user_info.user_id, elixir_name)
    if not has:
        msg = f"没有检测到【{elixir_name}】，突破停止！"
        return await xiuxian_send_message(level_up_zj, message=msg)

    # 使用丹药
    sql_message.update_back_j(user_id, 1999, use_key=1)

    # 获取概率，判断是否成功
    next_rank = rank.get_rank_info(user_info.level, 1)
    next_rank_name = next_rank["name"]
    level_rate = rank.get_rank_rate(user_info.level)  # 对应境界突破的概率
    user_level_uprate = int(user_info.level_up_rate)  # 用户失败次数加成
    total_rate = level_rate + user_level_uprate
    success = True if random.randint(0, 100) < total_rate else False

    if success:
        # 突破成功
        sql_message.updata_level(user_id, next_rank_name)  # 更新境界
        sql_message.update_power2(user_id)  # 更新战力
        sql_message.updata_level_cd(user_id)  # 更新CD
        sql_message.update_levelrate(user_id, 0)
        sql_message.update_user_hp(user_id)  # 重置用户HP，mp，atk状态
        msg = f"道友使用了丹药【{elixir_name}】，恭喜道友突破【{next_rank_name}】成功！"
        await xiuxian_send_message(level_up_zj, message=msg)

    else:
        # 突破失败
        sql_message.updata_level_cd(user_id)  # 更新突破CD
        update_rate = 1 if int(level_rate * XiuConfig().level_up_probability) <= 1 else int(
            level_rate * XiuConfig().level_up_probability)  # 失败增加突破几率
        sql_message.update_levelrate(user_id, user_level_uprate + update_rate)
        msg = f"道友突破失败，但是使用了丹药【{elixir_name}】，本次突破失败不扣除修为下次突破成功率增加{update_rate}%，道友不要放弃！"
        await xiuxian_send_message(level_up_zj, message=msg)


@user_level_up_rate.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def user_level_up_rate_(_: Bot, event: GroupMessageEvent):
    """
    我的突破概率
    """
    user_id = event.get_user_id()
    user_info = sql_message.get_user_message(user_id)  # 用户信息
    level_up_rate = int(user_info.level_up_rate)  # 用户失败次数加成
    level_rate = rank.get_rank_info(user_info.level)["rate"]  # 对应境界突破的概率
    msg = f"道友下一次突破成功概率为{level_rate + level_up_rate}%"
    await xiuxian_send_message(user_level_up_rate, message=msg)
