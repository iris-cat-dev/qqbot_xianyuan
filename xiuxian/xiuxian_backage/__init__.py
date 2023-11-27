import asyncio
import random
import re
from datetime import datetime

from nonebot import on_command, require, on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import (
    Bot,
    GROUP,
    Message,
    GroupMessageEvent,
    MessageSegment,
    GROUP_ADMIN,
    GROUP_OWNER,
    ActionFailed
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from .back_util import (
    get_user_back_msg, check_equipment_can_use,
    get_use_equipment_sql, check_use_elixir,
    get_use_jlq_msg, get_no_use_equipment_sql
)
from .backconfig import get_config, savef
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_img_message
from ..common.param_checker import check_player
from ..item_json import Items
from ..lay_out import assign_bot, assign_bot_group, Cooldown, CooldownIsolateLevel
from ..read_buff import (
    get_weapon_info_msg, get_armor_info_msg,
    get_sec_msg, get_main_info_msg
)
from ..utils import (
    check_user, get_msg_pic
)
from ..xiuxian2_handle import XiuxianDateManage, OtherSet
from ..xiuxian_config import XiuConfig

items = Items()
config = get_config()
groups = config['open']  # list，群交流会使用
auction = {}
AUCTIONSLEEPTIME = 120  # 交友初始等待时间（秒）
cache_help = {}
auction_offer_flag = False  # 交友标志
AUCTIONOFFERSLEEPTIME = 10  # 每次交友增加交友剩余的时间（秒）
auction_offer_time_count = 0  # 计算剩余时间
auction_offer_all_count = 0  # 控制线程等待时间
auction_time_config = config['交友会定时参数']  #
sql_message = XiuxianDateManage()

# 定时任务
set_auction_by_scheduler = require("nonebot_plugin_apscheduler").scheduler
reset_day_num_scheduler = require("nonebot_plugin_apscheduler").scheduler

my_back = on_fullmatch('我的背包', priority=10, permission=GROUP, block=True)
use = on_startswith("使用", priority=15, permission=GROUP, block=True)
no_use_zb = on_command("换装", priority=5, permission=GROUP, block=True)

set_auction = on_command("群交流会", priority=4, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),
                         block=True)
creat_auction = on_fullmatch("举行交友会", priority=5, permission=GROUP and SUPERUSER, block=True)
offer_auction = on_command("交友", priority=5, permission=GROUP, block=True)
back_help = on_fullmatch("背包帮助", priority=8, permission=GROUP, block=True)

__back_help__ = f"""
背包帮助信息:
指令：
1、我的背包:查看自身背包前98个物品的信息
2、使用+物品名字：使用物品,丹药可批量使用
3、换装+装备名字：卸载目标装备
4、坊市购买+物品编号:购买坊市内的物品
5、坊市查看、查看坊市:查询坊市在售物品
6、坊市上架:坊市上架 物品 金额 数量，上架背包内的物品,最低金额50w
7、系统坊市上架:系统坊市上架 物品 金额 数量，上架任意存在的物品，超管权限
8、坊市下架+物品编号：下架坊市内的物品，管理员和群主可以下架任意编号的物品！
9、群交流会开启、关闭:开启交友行功能，管理员指令，注意：会在机器人所在的全部已开启此功能的群内通报交友消息
10、交友+金额：对本次交友会的物品进行交友
11、炼金+物品名字：将物品炼化为灵石,支持批量炼金和绑定丹药炼金
12、背包帮助:获取背包帮助指令
13、查看修仙界物品:支持类型【功法|神通|丹药|合成丹药|法器|防具】
14、清空坊市:清空本群坊市,管理员权限
非指令：
1、定时生成交友会,每天{auction_time_config['hours']}点每整点生成一场交友会
""".strip()


# 重置丹药每日使用次数
@reset_day_num_scheduler.scheduled_job("cron", hour=0, minute=0, )
async def reset_day_num_scheduler_():
    sql_message.day_num_reset()
    logger.info("每日丹药使用次数重置成功！")


# 定时任务生成交友会
@set_auction_by_scheduler.scheduled_job("cron", hour=auction_time_config['hours'])
async def set_auction_by_scheduler_():
    if groups:
        global auction
        if auction != {}:  # 存在交友会
            logger.info("本群已存在一场交友会，已清除！")
            auction = {}
        try:
            auction_id_list = get_auction_id_list()
            auction_id = random.choice(auction_id_list)
        except LookupError:
            msg = "获取不到交友物品的信息，请检查配置文件！"
            logger.info(msg)
            return
        auction_info = items.get_data_by_item_id(auction_id)
        start_price = get_auction_price_by_id(auction_id)['start_price']
        msg = '本次交友的物品为：\n'
        msg += get_auction_msg(auction_id)
        msg += f"\n底价为{start_price}灵石"
        msg += "\n请诸位道友发送 交友+金额 来进行交友吧！"
        msg += f"\n本次竞拍时间为:{AUCTIONSLEEPTIME}秒！"
        auction['id'] = auction_id
        auction['user_id'] = 0
        auction['now_price'] = start_price
        auction['name'] = auction_info['name']
        auction['type'] = auction_info['type']
        auction['start_time'] = datetime.now()
        auction['group_id'] = 0
        for group_id in groups:
            bot = await assign_bot_group(group_id=group_id)
            try:
                if XiuConfig().img:
                    pic = await get_msg_pic(msg)
                    await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
                else:
                    await bot.send_group_msg(group_id=int(group_id), message=msg)
            except ActionFailed:  # 发送群消息失败
                continue
        await asyncio.sleep(AUCTIONSLEEPTIME)  # 先睡60秒

        global auction_offer_flag, auction_offer_all_count, auction_offer_time_count
        while auction_offer_flag:  # 有人交友
            if auction_offer_all_count == 0:
                auction_offer_flag = False
                break
            logger.info(f"有人交友，本次等待时间：{auction_offer_all_count * AUCTIONOFFERSLEEPTIME}秒")
            first_time = auction_offer_all_count * AUCTIONOFFERSLEEPTIME
            auction_offer_all_count = 0
            auction_offer_flag = False
            await asyncio.sleep(first_time)
            logger.info(
                f"总计等待时间{auction_offer_time_count * AUCTIONOFFERSLEEPTIME}秒，当前交友标志：{auction_offer_flag}，本轮等待时间：{first_time}")

        logger.info(f"等待时间结束，总计等待时间{auction_offer_time_count * AUCTIONOFFERSLEEPTIME}秒")
        if auction['user_id'] == 0:
            msg = "很可惜，本次交友会流拍了！"
            auction = {}
            for group_id in groups:
                bot = await assign_bot_group(group_id=group_id)
                try:
                    if XiuConfig().img:
                        pic = await get_msg_pic(msg)
                        await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(group_id), message=msg)
                except ActionFailed:  # 发送群消息失败
                    continue
            return
        now_price = int(auction['now_price'])
        user_info = sql_message.get_user_message(auction['user_id'])
        user_stone = user_info.stone
        if user_stone < now_price:
            msg = f"交友会结算！竞拍者灵石小于交友，判定为捣乱，捣乱次数+1!"
            for group_id in groups:
                bot = await assign_bot_group(group_id=group_id)
                try:
                    if XiuConfig().img:
                        pic = await get_msg_pic(msg)
                        await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
                    else:
                        await bot.send_group_msg(group_id=int(group_id), message=msg)
                except ActionFailed:  # 发送群消息失败
                    continue
            return
        msg = "本次交友会结束！"
        msg += f"恭喜来自群{auction['group_id']}的{user_info.user_name}道友成功交友获得：{auction['type']}-{auction['name']}!"
        for group_id in groups:
            bot = await assign_bot_group(group_id=group_id)
            try:
                if XiuConfig().img:
                    pic = await get_msg_pic(msg)
                    await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
                else:
                    await bot.send_group_msg(group_id=int(group_id), message=msg)
            except ActionFailed:  # 发送群消息失败
                continue

        sql_message.send_back(user_info.user_id, auction['id'], auction['name'], auction['type'], 1)
        sql_message.update_ls(user_info.user_id, int(auction['now_price']), 2)
        auction = {}
        auction_offer_time_count = 0
        return


@back_help.handle(parameterless=[Cooldown(at_sender=True)])
async def back_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(back_help, message=__back_help__)


@my_back.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def mind_back_(bot: Bot, event: GroupMessageEvent):
    """
    我的背包
    """
    user_id = event.user_id
    msg_list = get_user_back_msg(user_id)
    if len(msg_list) > 0:
        # try:
        #     for item in msg_list:
        #         msg += f"{item}\n"
        # except ActionFailed:
        #     msg = "查看背包失败"
        #     await xiuxian_send_message(my_back, msg)
        await xiuxian_send_group_img_message(event.group_id, msg_list)
    else:
        msg = '道友的背包空空如也！'
        await xiuxian_send_message(my_back, msg)


@no_use_zb.handle(parameterless=[Cooldown(at_sender=True)])
async def no_use_zb_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    """
    卸载物品（只支持装备）
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    isUser, user_info, msg = check_user(event)
    if not isUser:
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await no_use_zb.finish()
    user_id = user_info.user_id
    arg = args.extract_plain_text().strip()

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await no_use_zb.finish()
    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    for back in back_msg:
        if arg == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            goods_type = back.goods_type
            break
    if not in_flag:
        msg = f"请检查该道具 {arg} 是否在背包内！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await no_use_zb.finish()

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            sql_str, item_type = get_no_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, 0)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, 0)
            msg = f"成功卸载装备{arg}！"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await no_use_zb.finish()
        else:
            msg = f"装备没有被使用，无法卸载！"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await no_use_zb.finish()
    else:
        msg = f"目前只支持卸载装备！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await no_use_zb.finish()


@use.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def use_(bot: Bot, event: GroupMessageEvent):
    """使用物品
    ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
    "remake", "day_num", "all_num", "action_time", "state"]
    """
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    message = str(event.message)
    arg = message[2:]  #

    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await xiuxian_send_message(use, message=msg)

    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_num = None
    for back in back_msg:
        if arg == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            goods_type = back.goods_type
            goods_num = back.goods_num
            break

    if not in_flag:
        msg = f"请检查该道具 {arg} 是否在背包内！"
        await xiuxian_send_message(use, message=msg)

    if goods_type == "装备":
        if not check_equipment_can_use(user_id, goods_id):
            msg = f"该装备已被装备，请勿重复装备！"
            await xiuxian_send_message(use, message=msg)

        else:  # 可以装备
            sql_str, item_type = get_use_equipment_sql(user_id, goods_id)
            for sql in sql_str:
                sql_message.update_back_equipment(sql)
            if item_type == "法器":
                sql_message.updata_user_faqi_buff(user_id, goods_id)
            if item_type == "防具":
                sql_message.updata_user_armor_buff(user_id, goods_id)

            msg = f"成功装备{arg}！"
            await xiuxian_send_message(use, message=msg)

    elif goods_type == "技能":
        pass

    elif goods_type == "丹药":
        try:
            num_str = re.findall("\d+", message)[0]  # boss编号
            num = int(num_str)
            if num > int(goods_num):
                msg = f"丹药数量不足，一共{goods_num}枚！"
                await xiuxian_send_message(use, message=msg)
        except:
            num = 1

        msg = check_use_elixir(user_id, goods_id, num)
        await xiuxian_send_message(use, message=msg)

    elif goods_type == "聚灵旗":
        msg = get_use_jlq_msg(user_id, goods_id)
        await xiuxian_send_message(use, message=msg)

    else:
        msg = '该类型物品调试中，未开启！'
        await xiuxian_send_message(use, message=msg)


@creat_auction.handle(parameterless=[Cooldown(at_sender=True)])
async def creat_auction_(bot: Bot, event: GroupMessageEvent):
    group_id = str(event.group_id)
    bot = await assign_bot_group(group_id=group_id)
    if group_id not in groups:
        msg = '本群尚未开启交友会功能，请联系管理员开启！'
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    global auction
    if auction != {}:
        msg = f'本群已存在一场交友会，请等待交友会结束！'
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()
    auction_id = None
    try:
        auction_id_list = get_auction_id_list()
        auction_id = random.choice(auction_id_list)
    except LookupError:
        msg = "获取不到交友物品的信息，请检查配置文件！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    auction_info = items.get_data_by_item_id(auction_id)
    start_price = get_auction_price_by_id(auction_id)['start_price']
    msg = '本次交友的物品为：\n'
    msg += get_auction_msg(auction_id)
    msg += f"\n底价为{start_price}灵石"
    msg += "\n请诸位道友发送 交友+金额 来进行交友吧！"
    msg += f"\n本次竞拍时间为:{AUCTIONSLEEPTIME}秒！"

    auction['id'] = auction_id
    auction['user_id'] = 0
    auction['now_price'] = start_price
    auction['name'] = auction_info['name']
    auction['type'] = auction_info['type']
    auction['start_time'] = datetime.now()
    auction['group_id'] = group_id

    for group_id in groups:
        bot = await assign_bot_group(group_id=group_id)
        try:
            if XiuConfig().img:
                pic = await get_msg_pic(msg)
                await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(group_id), message=msg)
        except ActionFailed:  # 发送群消息失败
            continue
    await asyncio.sleep(AUCTIONSLEEPTIME)  # 先睡60秒

    global auction_offer_flag, auction_offer_time_count, auction_offer_all_count
    while auction_offer_flag:  # 有人交友
        if auction_offer_all_count == 0:
            auction_offer_flag = False
            break
        logger.info(f"有人交友，本次等待时间：{auction_offer_all_count * AUCTIONOFFERSLEEPTIME}秒")
        first_time = auction_offer_all_count * AUCTIONOFFERSLEEPTIME
        auction_offer_all_count = 0
        auction_offer_flag = False
        await asyncio.sleep(first_time)

    logger.info(f"等待时间结束，总计等待时间{auction_offer_time_count * AUCTIONOFFERSLEEPTIME}秒")
    if auction['user_id'] == 0:
        msg = "很可惜，本次交友会流拍了！"
        auction = {}
        for group_id in groups:
            bot = await assign_bot_group(group_id=group_id)
            try:
                if XiuConfig().img:
                    pic = await get_msg_pic(msg)
                    await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
                else:
                    await bot.send_group_msg(group_id=int(group_id), message=msg)
            except ActionFailed:  # 发送群消息失败
                continue
        await creat_auction.finish()

    user_info = sql_message.get_user_message(auction['user_id'])
    now_price = int(auction['now_price'])
    user_stone = user_info.stone
    if user_stone < now_price:
        msg = f"交友会结算！竞拍者灵石小于交友，判定为捣乱，捣乱次数+1!"
        if XiuConfig().img:
            pic = await get_msg_pic(msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    msg = "本次交友会结束！"
    msg += f"恭喜来自群{auction['group_id']}的{user_info.user_name}道友成功交友获得：{auction['type']}-{auction['name']}!"
    for group_id in groups:
        bot = await assign_bot_group(group_id=group_id)
        try:
            if XiuConfig().img:
                pic = await get_msg_pic(msg)
                await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(group_id), message=msg)
        except ActionFailed:  # 发送群消息失败
            continue

    sql_message.send_back(user_info.user_id, auction['id'], auction['name'], auction['type'], 1)
    sql_message.update_ls(user_info.user_id, int(auction['now_price']), 2)
    auction = {}
    auction_offer_time_count = 0
    await creat_auction.finish()


@offer_auction.handle(parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GLOBAL)])
async def offer_auction_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    group_id = str(event.group_id)
    bot = await assign_bot_group(group_id=group_id)
    if group_id not in groups:
        msg = '本群尚未开启交友会功能，请联系管理员开启！'
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    isUser, user_info, msg = check_user(event)
    if not isUser:
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    global auction
    if auction == {}:
        msg = f'本群不存在交友会，请等待交友会开启！'
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    price = args.extract_plain_text().strip()
    try:
        price = int(price)
    except ValueError:
        msg = f"请发送正确的灵石数量"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    now_price = auction['now_price']
    min_price = int(now_price * 0.05)  # 最低加价5%
    if price <= 0 or price <= auction['now_price'] or price > user_info.stone:
        msg = f"走开走开，别捣乱！小心清空你灵石捏！"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()
    if price - now_price < min_price:
        msg = f"交友不得少于当前竞拍价的5%，目前最少加价为：{min_price}灵石，目前竞拍价为：{now_price}!"
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()

    global auction_offer_flag, auction_offer_time_count, auction_offer_all_count
    auction_offer_flag = True  # 有人交友
    auction_offer_time_count += 1
    auction_offer_all_count += 1
    auction['user_id'] = user_info.user_id
    auction['now_price'] = price
    auction['group_id'] = group_id
    now_time = datetime.now()
    dif_time = OtherSet().date_diff(now_time, auction['start_time'])
    msg = (
        f"来自群{group_id}的{user_info.user_name}道友交友：{price}枚灵石！"
        f"竞拍时间增加：{AUCTIONOFFERSLEEPTIME}秒，竞拍剩余时间：{int(AUCTIONSLEEPTIME - dif_time + AUCTIONOFFERSLEEPTIME * auction_offer_time_count)}秒"
    )
    error_msg = None
    for group_id in groups:
        bot = await assign_bot_group(group_id=group_id)
        try:
            if XiuConfig().img:
                pic = await get_msg_pic(msg)
                await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(group_id), message=msg)
        except ActionFailed:
            error_msg = f"消息发送失败，可能被风控，当前交友物品金额为：{auction['now_price']}！"
            continue
    logger.info(
        f"有人交友，交友标志：{auction_offer_flag}，当前等待时间：{auction_offer_all_count * AUCTIONOFFERSLEEPTIME}，总计交友次数：{auction_offer_time_count}")
    if error_msg is None:
        await offer_auction.finish()
    else:
        msg = error_msg
        if XiuConfig().img:
            pic = await get_msg_pic(msg)
            await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(group_id), message=msg)
        await creat_auction.finish()


@set_auction.handle(parameterless=[Cooldown(at_sender=True)])
async def set_auction_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    bot, send_group_id = await assign_bot(bot=bot, event=event)
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)
    is_in_group = is_in_groups(event)  # True在，False不在

    if mode == '开启':
        if is_in_group:
            msg = f'本群已开启群交流会，请勿重复开启!'
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()
        else:
            config['open'].append(group_id)
            savef(config)
            msg = "已开启群交流会"
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()

    elif mode == '关闭':
        if is_in_group:
            config['open'].remove(group_id)
            savef(config)
            msg = f'已关闭本群交流会!'
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()
        else:
            msg = f'本群未开启群交流会!'
            if XiuConfig().img:
                pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
                await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
            else:
                await bot.send_group_msg(group_id=int(send_group_id), message=msg)
            await set_auction.finish()

    else:
        msg = __back_help__
        if XiuConfig().img:
            pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
            await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
        else:
            await bot.send_group_msg(group_id=int(send_group_id), message=msg)
        await set_auction.finish()




def get_auction_id_list():
    auctions = config['auctions']
    auction_id_list = []
    for k, v in auctions.items():
        auction_id_list.append(v['id'])
    return auction_id_list


def get_auction_price_by_id(id):
    auctions = config['auctions']
    auction_info = None
    for k, v in auctions.items():
        if int(v['id']) == int(id):
            auction_info = auctions[k]
            break
    return auction_info


def is_in_groups(event: GroupMessageEvent):
    return str(event.group_id) in groups


def get_auction_msg(auction_id):
    item_info = items.get_data_by_item_id(auction_id)
    _type = item_info['type']
    msg = None
    if _type == "装备":
        if item_info['item_type'] == "防具":
            msg = get_armor_info_msg(auction_id, item_info)
        if item_info['item_type'] == '法器':
            msg = get_weapon_info_msg(auction_id, item_info)

    if _type == "技能":
        if item_info['item_type'] == '神通':
            msg = f"{item_info['level']}神通-{item_info['name']}:"
            msg += get_sec_msg(item_info)
        if item_info['item_type'] == '功法':
            msg = f"{item_info['level']}功法-"
            msg += get_main_info_msg(auction_id)[1]

    if _type == "丹药":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果:{item_info['desc']}"

    return msg
