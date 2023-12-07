import re
from datetime import datetime

from nonebot import on_fullmatch, on_startswith, on_endswith
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.param_checker import check_player, Cooldown
from ..common.player_manager import get_cultivation_rate, check_user_state
from ..common.root import Root
from ..common.xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import XiuConfig

cache_help = {}
sql_message = XiuxianDateManage()
sql_manager = XiuxianSqlManager()

root = Root()


cul_help = on_fullmatch("修炼帮助", priority=5, permission=GROUP, block=True)
out_closing = on_endswith("出关", priority=5, permission=GROUP, block=True)
in_closing = on_fullmatch("闭关", priority=5, permission=GROUP, block=True)
stone_exp = on_startswith("灵石修炼", priority=5, permission=GROUP, block=True)


__cul_help__ = f"""
修炼帮助信息:
指令：
1、闭关:开始闭关修炼提升修为
2、出关:结束闭关
3、灵石出关:使用灵石进行闭关，自动计算消耗灵石
4、灵石修炼:通过灵石增加修为
""".strip()


@cul_help.handle(parameterless=[Cooldown(at_sender=True)])
async def work_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(cul_help, message=__cul_help__)


@stone_exp.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def stone_exp_(_: Bot, event: GroupMessageEvent):
    """
    灵石修炼
    """
    user_info = sql_manager.get_user_info(event.user_id)
    user_id = user_info.user_id
    level = user_info.level
    use_exp = user_info.exp
    use_stone = user_info.stone
    max_exp = (int(OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit)  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    msg = str(event.message)  # args.extract_plain_text().strip()
    stone_num = re.findall("\d+", msg)  # 灵石数

    if stone_num:
        pass
    else:
        msg = "请输入正确的灵石数量！"
        await xiuxian_send_message(stone_exp, message=msg)

    stone_num = int(stone_num[0])
    if use_stone <= stone_num:
        msg = "你的灵石还不够呢，快去赚点灵石吧！"
        await xiuxian_send_message(stone_exp, message=msg)

    exp = int(stone_num / 10)
    if exp >= user_get_exp_max:
        # 用户获取的修为到达上限
        sql_message.update_exp(user_id, user_get_exp_max)
        sql_message.update_power2(user_id)  # 更新战力
        msg = f"修炼结束，本次修炼到达上限，共增加修为：{user_get_exp_max},消耗灵石：{user_get_exp_max * 10}"
        sql_message.update_ls(user_id, int(user_get_exp_max * 10), 2)
        await xiuxian_send_message(stone_exp, message=msg)
    else:
        sql_message.update_exp(user_id, exp)
        sql_message.update_power2(user_id)  # 更新战力
        msg = f"修炼结束，本次修炼共增加修为：{exp},消耗灵石：{stone_num}"
        sql_message.update_ls(user_id, int(stone_num), 2)
        await xiuxian_send_message(stone_exp, message=msg)


@in_closing.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def in_closing_(bot: Bot, event: GroupMessageEvent):
    """
    闭关
    """
    user_type = 1  # 状态0为无事件
    user_info = sql_manager.get_user_info(event.user_id)

    user_id = user_info.user_id
    is_type, msg = check_user_state(user_id, 0)
    if is_type:  # 符合
        sql_message.in_closing(user_id, user_type)
        msg = "进入闭关状态，如需出关，发送【出关】！"
        await xiuxian_send_message(in_closing, message=msg)
    else:
        await xiuxian_send_message(in_closing, message=msg)


@out_closing.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def out_closing_(bot: Bot, event: GroupMessageEvent):
    """
    出关
    """
    user_info = sql_manager.get_user_info(event.user_id)

    user_type = 0  # 状态0为无事件
    user_id = user_info.user_id
    level = user_info.level
    use_exp = user_info.exp
    hp_speed = 50
    mp_speed = 25

    max_exp = int(OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    now_time = datetime.now()
    user_cd_message = sql_message.get_user_cd(user_id)
    is_type, msg = check_user_state(user_id, 1)
    if not is_type:
        await xiuxian_send_message(out_closing, message=msg)
    else:
        # 用户状态为 1
        in_closing_time = datetime.strptime(user_cd_message.create_time, "%Y-%m-%d %H:%M:%S.%f")  # 进入闭关的时间
        exp_time = (OtherSet().date_diff(now_time, in_closing_time) // 60)  # 闭关时长计算(分钟) = second // 60
        cultivation_rate_info = get_cultivation_rate(event.user_id)
        exp = int((exp_time * XiuConfig().closing_exp) * (cultivation_rate_info["total"]))

        impart_exp_up = 0
        exp = int(exp * (1 + impart_exp_up))
        if exp >= user_get_exp_max:
            # 用户获取的修为到达上限
            sql_message.in_closing(user_id, user_type)
            sql_message.update_exp(user_id, user_get_exp_max)
            sql_message.update_power2(user_id)  # 更新战力

            result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed), int(exp * mp_speed))
            sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1], int(result_hp_mp[2] / 10))
            msg = "闭关结束，本次闭关到达上限，共增加修为：{}{}{}".format(user_get_exp_max, result_msg[0], result_msg[1])
            await xiuxian_send_message(out_closing, message=msg)

        else:
            # 用户获取的修为没有到达上限
            if str(event.message) == "灵石出关":
                user_stone = user_info.stone  # 用户灵石数
                if user_stone <= 0:
                    user_stone = 0
                if exp <= user_stone:
                    exp = exp * 2
                    sql_message.in_closing(user_id, user_type)
                    sql_message.update_exp(user_id, exp)
                    sql_message.update_ls(user_id, int(exp / 2), 2)
                    sql_message.update_power2(user_id)  # 更新战力

                    result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed), int(exp * mp_speed))
                    sql_message.update_user_attribute(user_id,
                                                      result_hp_mp[0],
                                                      result_hp_mp[1],
                                                      int(result_hp_mp[2] / 10))
                    msg = "闭关结束，共闭关{}分钟，本次闭关增加修为：{}，消耗灵石{}枚{}{}".format(exp_time,
                                                                                              exp,
                                                                                              int(exp / 2),
                                                                                              result_msg[0],
                                                                                              result_msg[1])
                    await xiuxian_send_message(out_closing, message=msg)

                else:
                    exp = exp + user_stone
                    sql_message.in_closing(user_id, user_type)
                    sql_message.update_exp(user_id, exp)
                    sql_message.update_ls(user_id, user_stone, 2)
                    sql_message.update_power2(user_id)  # 更新战力
                    result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed), int(exp * mp_speed))
                    sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1],
                                                      int(result_hp_mp[2] / 10))
                    msg = "闭关结束，共闭关{}分钟，本次闭关增加修为：{}，消耗灵石{}枚{}{}".format(exp_time, exp, user_stone,
                                                                                              result_msg[0],
                                                                                              result_msg[1])

                    await xiuxian_send_message(out_closing, message=msg)
            else:
                sql_message.in_closing(user_id, user_type)
                sql_message.update_exp(user_id, exp)
                sql_message.update_power2(user_id)  # 更新战力
                result_msg, result_hp_mp = OtherSet().send_hp_mp(user_id, int(exp * hp_speed), int(exp * mp_speed))
                sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1], int(result_hp_mp[2] / 10))
                msg = "闭关结束，共闭关{}分钟，本次闭关增加修为：{}{}{}".format(exp_time, exp, result_msg[0],
                                                                             result_msg[1])
                await xiuxian_send_message(out_closing, message=msg)



