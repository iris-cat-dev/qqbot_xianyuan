import random
import re
from datetime import datetime

from nonebot import on_fullmatch, require, on_startswith, on_endswith
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent
from nonebot.log import logger

from .two_exp_cd import two_exp_cd
from .. import Rank
from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import check_player
from ..data_source import jsondata
from ..lay_out import Cooldown
from ..read_buff import UserBuffDate
from ..utils import check_user
from ..utils import check_user_type
from ..xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import XiuConfig

cache_help = {}
sql_message = XiuxianDateManage()

two_exp_cd_up = require("nonebot_plugin_apscheduler").scheduler

cul_help = on_fullmatch("修炼帮助", priority=5, permission=GROUP, block=True)
out_closing = on_endswith("出关", priority=5, permission=GROUP, block=True)
in_closing = on_fullmatch("闭关", priority=5, permission=GROUP, block=True)
stone_exp = on_startswith("灵石修炼", priority=5, permission=GROUP, block=True)
two_exp = on_startswith("双修", priority=5, permission=GROUP, block=True)
my_exp_num = on_fullmatch("我的双修次数", priority=9, permission=GROUP, block=True)
del_exp_decimal = on_fullmatch("抑制黑暗动乱", priority=9, permission=GROUP, block=True)

__cul_help__ = f"""
修炼帮助信息:
指令：
1、闭关:开始闭关修炼提升修为
2、出关:结束闭关
3、灵石出关:使用灵石进行闭关，自动计算消耗灵石
4、灵石修炼:通过灵石增加修为
5、双修: 与道侣一起修炼
6、我的双修次数:每日的双修剩余次数
7、抑制黑暗动乱:清除修为浮点数
""".strip()


# 每日0点重置用户宗门任务次数、宗门丹药领取次数
@two_exp_cd_up.scheduled_job("cron", hour=0, minute=0)
async def two_exp_cd_up_():
    two_exp_cd.re_data()
    logger.info('双修次数已更新！')


two_exp_limit = 3


@cul_help.handle(parameterless=[Cooldown(at_sender=True)])
async def work_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(cul_help, message=__cul_help__)


@two_exp.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def two_exp_(bot: Bot, event: GroupMessageEvent):
    """
    双修
    """
    global two_exp_limit
    _, user_1, msg = check_user(event)

    two_qq = None  # 艾特的时候存到这里
    try:
        two_qq = event.original_message[1].data.get("qq", "")
    except:
        msg = "指令输入错误：【双修+@对方】"
        await xiuxian_send_message(two_exp, message=msg)

    if two_qq is None:
        msg = "请at你的道侣,与其一起双修！"
        await xiuxian_send_message(two_exp, message=msg)

    user_2 = sql_message.get_user_message(two_qq)
    if int(user_1.user_id) == int(two_qq):
        msg = "道友无法与自己双修！"
        await xiuxian_send_message(two_exp, message=msg)

    if user_2:
        exp_1 = user_1.exp
        exp_2 = user_2.exp
        if exp_2 > exp_1:
            msg = "修仙大能看了看你，不屑一顾，扬长而去！"
            await xiuxian_send_message(two_exp, message=msg)

        else:
            limt_1 = two_exp_cd.find_user(user_1.user_id)
            limt_2 = two_exp_cd.find_user(user_2.user_id)
            # 加入传承

            impart_two_exp_1 = 0
            impart_two_exp_2 = 0
            if limt_1 >= two_exp_limit + impart_two_exp_1:
                msg = "道友今天双修次数已经到达上限！"
                await xiuxian_send_message(two_exp, message=msg)

            if limt_2 >= two_exp_limit + impart_two_exp_2:
                msg = "对方今天双修次数已经到达上限！"
                await xiuxian_send_message(two_exp, message=msg)

            max_exp_1 = (
                    int(OtherSet().set_closing_type(user_1.level)) * XiuConfig().closing_exp_upper_limit
            )  # 获取下个境界需要的修为 * 1.5为闭关上限
            max_exp_2 = (
                    int(OtherSet().set_closing_type(user_2.level)) * XiuConfig().closing_exp_upper_limit
            )
            user_get_exp_max_1 = int(max_exp_1) - user_1.exp
            user_get_exp_max_2 = int(max_exp_2) - user_2.exp

            if user_get_exp_max_1 < 0:
                user_get_exp_max_1 = 0
            if user_get_exp_max_2 < 0:
                user_get_exp_max_2 = 0

            msg = ""
            msg += f"{user_1.user_name}与{user_2.user_name}情投意合，于某地一起修炼了一晚。"
            if random.randint(1, 100) in [13, 14, 52, 10, 66]:
                exp = int((exp_1 + exp_2) * 0.0055)

                if user_1.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_1.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_1 = max_exp
                else:
                    exp_limit_1 = exp

                if exp_limit_1 >= user_get_exp_max_1:
                    sql_message.update_exp(user_1.user_id, user_get_exp_max_1)
                    msg += f"{user_1.user_name}修为到达上限，增加修为{user_get_exp_max_1}。"
                else:
                    sql_message.update_exp(user_1.user_id, exp_limit_1)
                    msg += f"{user_1.user_name}增加修为{exp_limit_1}。"
                sql_message.update_power2(user_1.user_id)

                if user_2.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_2.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_2 = max_exp
                else:
                    exp_limit_2 = exp

                if exp_limit_2 >= user_get_exp_max_2:
                    sql_message.update_exp(user_2.user_id, user_get_exp_max_2)
                    msg += f"{user_2.user_name}修为到达上限，增加修为{user_get_exp_max_2}。"
                else:
                    sql_message.update_exp(user_2.user_id, exp_limit_2)
                    msg += f"{user_2.user_name}增加修为{exp_limit_2}。"
                sql_message.update_power2(user_2.user_id)
                sql_message.update_levelrate(user_1.user_id, user_1.level_up_rate + 2)
                sql_message.update_levelrate(user_2.user_id, user_2.level_up_rate + 2)
                two_exp_cd.add_user(user_1.user_id)
                two_exp_cd.add_user(user_2.user_id)
                msg += f"离开时双方互相留法宝为对方护道,双方各增加突破概率2%。"
                await xiuxian_send_message(two_exp, message=msg)

            else:
                exp = int((exp_1 + exp_2) * 0.0055)

                if user_1.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_1.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_1 = max_exp
                else:
                    exp_limit_1 = exp
                if exp_limit_1 >= user_get_exp_max_1:
                    sql_message.update_exp(user_1.user_id, user_get_exp_max_1)
                    msg += f"{user_1.user_name}修为到达上限，增加修为{user_get_exp_max_1}。"
                else:
                    sql_message.update_exp(user_1.user_id, exp_limit_1)
                    msg += f"{user_1.user_name}增加修为{exp_limit_1}。"
                sql_message.update_power2(user_1.user_id)

                if user_2.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_2.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_2 = max_exp
                else:
                    exp_limit_2 = exp
                if exp_limit_2 >= user_get_exp_max_2:
                    sql_message.update_exp(user_2.user_id, user_get_exp_max_2)
                    msg += f"{user_2.user_name}修为到达上限，增加修为{user_get_exp_max_2}。"
                else:
                    sql_message.update_exp(user_2.user_id, exp_limit_2)
                    msg += f"{user_2.user_name}增加修为{exp_limit_2}。"
                sql_message.update_power2(user_2.user_id)
                two_exp_cd.add_user(user_1.user_id)
                two_exp_cd.add_user(user_2.user_id)
                await xiuxian_send_message(two_exp, message=msg)

    else:
        msg = "修仙者应一心向道，务要留恋凡人！"
        await xiuxian_send_message(two_exp, message=msg)


@stone_exp.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def stone_exp_(_: Bot, event: GroupMessageEvent):
    """
    灵石修炼
    """
    _, user_info, _ = check_user(event)
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
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    is_type, msg = check_user_type(user_id, 0)
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
    _, user_info, msg = check_user(event)

    user_type = 0  # 状态0为无事件
    user_id = user_info.user_id
    level = user_info.level
    use_exp = user_info.exp
    hp_speed = 25
    mp_speed = 50

    max_exp = int(OtherSet().set_closing_type(level)) * XiuConfig().closing_exp_upper_limit  # 获取下个境界需要的修为 * 1.5为闭关上限
    user_get_exp_max = int(max_exp) - use_exp

    if user_get_exp_max < 0:
        # 校验当当前修为超出上限的问题，不可为负数
        user_get_exp_max = 0

    now_time = datetime.now()
    user_cd_message = sql_message.get_user_cd(user_id)
    is_type, msg = check_user_type(user_id, 1)
    if not is_type:
        await xiuxian_send_message(out_closing, message=msg)
    else:
        # 用户状态为 1
        in_closing_time = datetime.strptime(  user_cd_message.create_time, "%Y-%m-%d %H:%M:%S.%f" )  # 进入闭关的时间
        exp_time = ( OtherSet().date_diff(now_time, in_closing_time) // 60 )  # 闭关时长计算(分钟) = second // 60
        level_rate = sql_message.get_root_rate(user_info.root_type)  # 灵根倍率
        realm_rate = Rank().get_rank_speed(level) # 境界倍率

        user_buff_data = UserBuffDate(user_id)
        mainbuffdata = user_buff_data.get_user_main_buff_data()
        mainbuffratebuff = mainbuffdata['ratebuff'] if mainbuffdata != None else 0  # 功法修炼倍率
        exp = int(
            (exp_time * XiuConfig().closing_exp) * ((level_rate * realm_rate * (1 + mainbuffratebuff)))
            # 洞天福地为加法
        )  # 本次闭关获取的修为
        # 计算传承增益

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
                    sql_message.update_user_attribute(user_id, result_hp_mp[0], result_hp_mp[1],
                                                      int(result_hp_mp[2] / 10))
                    msg = "闭关结束，共闭关{}分钟，本次闭关增加修为：{}，消耗灵石{}枚{}{}".format(exp_time, exp,
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


@del_exp_decimal.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def del_exp_decimal_(bot: Bot, event: GroupMessageEvent):
    """
    清除修为浮点数
    """
    _, user_info, msg = check_user(event)
    user_id = user_info.user_id
    exp = user_info.exp
    sql_message.del_exp_decimal(user_id, exp)
    msg = "黑暗动乱暂时抑制成功！"
    await xiuxian_send_message(del_exp_decimal, message=msg)


@my_exp_num.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def my_exp_num_(bot: Bot, event: GroupMessageEvent):
    """
    我的双修次数
    """
    global two_exp_limit
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    limit = two_exp_cd.find_user(user_id)
    impart_data = None
    impart_two_exp = impart_data.impart_two_exp if impart_data is not None else 0
    num = (two_exp_limit + impart_two_exp) - limit
    if num <= 0:
        num = 0
    msg = f"道友剩余双修次数{num}次！"
    await xiuxian_send_message(out_closing, message=msg)
