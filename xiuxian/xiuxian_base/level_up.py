import random
from datetime import datetime

from nonebot import on_fullmatch, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent


from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..common.rank import Rank
from ..data_source import jsondata
from ..item_json import Items
from ..lay_out import Cooldown
from ..utils import check_user
from ..xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import XiuConfig

level_up = on_fullmatch("突破", priority=6, permission=GROUP, block=True)
level_up_dr = on_fullmatch("渡厄突破", priority=7, permission=GROUP, block=True)
level_up_zj = on_fullmatch("直接突破", priority=7, permission=GROUP, block=True)
user_level_up_rate = on_fullmatch('我的突破概率', priority=5, permission=GROUP, block=True)

sql_message = XiuxianDateManage()
rank = Rank()


@level_up.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def level_up_(bot: Bot, event: GroupMessageEvent):
    """
    突破
    """
    _, user_info, msg = check_user(event)
    user_id = user_info.user_id
    if user_info.hp is None:
        # 判断用户气血是否为空
        sql_message.update_user_hp(user_id)

    user_msg = sql_message.get_user_message(user_id)  # 用户信息
    user_leveluprate = int(user_msg.level_up_rate)  # 用户失败次数加成
    level_cd = user_msg.level_up_cd

    if level_cd:
        # 校验是否存在CD
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果cd小于配置的cd，返回等待时间
            msg = "目前无法突破，还需要{}分钟".format(XiuConfig().level_up_cd - (cd // 60))
            await xiuxian_send_message(level_up, msg)
    else:
        pass

    level_name = user_msg.level  # 用户境界
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    user_backs = sql_message.get_back_msg(user_id)  # list(back)
    items = Items()
    pause_flag = False
    elixir_name = None
    elixir_desc = None
    if user_backs is not None:
        for back in user_backs:
            if int(back.goods_id) == 1999:  # 检测到有对应丹药
                pause_flag = True
                elixir_name = back.goods_name
                elixir_desc = items.get_data_by_item_id(1999)['desc']
                break

    if pause_flag:
        msg = (f"由于检测到背包有丹药：{elixir_name}，效果：{elixir_desc}，突破已经准备就绪"
               f"请发送 ，【渡厄突破】 或 【直接突破】来选择是否使用丹药突破！"
               f"本次突破概率为：{level_rate + user_leveluprate}% ")
    else:
        msg = (f"由于检测到背包没有【渡厄丹】，突破已经准备就绪，"
               f"请发送，【直接突破】来突破！请注意，本次突破失败将会损失部分修为，"
               f"本次突破概率为：{level_rate + user_leveluprate}% ")

    await xiuxian_send_message(level_up, msg)


@level_up_zj.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def level_up_zj_(bot: Bot, event: GroupMessageEvent):
    """
    直接 突破
    """
    _, user_info, _ = check_user(event)
    user_id = user_info.user_id

    # 判断用户气血是否为空
    if user_info.hp is None:
        sql_message.update_user_hp(user_id)

    level_cd = user_info.level_up_cd
    if level_cd:
        # 校验是否存在 cd
        time_now = datetime.now()
        cd = OtherSet().date_diff(time_now, level_cd)  # 获取 second
        if cd < XiuConfig().level_up_cd * 60:
            # 如果 cd 小于配置的 cd，返回等待时间
            msg = "目前无法突破，还需要{}分钟".format(XiuConfig().level_up_cd - (cd // 60))
            await xiuxian_send_message(level_up_zj, message=msg)

    if rank.is_max(user_info.level):
        msg = "道友已是最高境界，无法突破！"
        return await xiuxian_send_message(level_up_zj, message=msg)

    # 判断修为是否足够突破
    next_rank = rank.get_rank_info(user_info.level, 1)
    next_rank_name = next_rank["name"]
    need_exp = next_rank["exp"]
    if user_info.exp < need_exp:
        msg = f"道友的修为不足以突破！距离下次突破需要{need_exp - user_info.exp}修为！突破境界为：{next_rank_name}"
        return await xiuxian_send_message(level_up_zj, message=msg)

    level_rate = jsondata.level_rate_data()[user_info.level]  # 对应境界突破的概率
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
    pass


@user_level_up_rate.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def user_level_up_rate_(_: Bot, event: GroupMessageEvent):
    """
    突破概率
    """
    user_id = event.get_user_id()
    user_msg = sql_message.get_user_message(user_id)  # 用户信息
    level_up_rate = int(user_msg.level_up_rate)  # 用户失败次数加成
    level_name = user_msg.level  # 用户境界
    level_rate = jsondata.level_rate_data()[level_name]  # 对应境界突破的概率
    msg = f"道友下一次突破成功概率为{level_rate + level_up_rate}%"
    await xiuxian_send_message(user_level_up_rate, message=msg)
