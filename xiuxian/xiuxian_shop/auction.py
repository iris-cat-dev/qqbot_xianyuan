from datetime import datetime

from nonebot import logger

from ..common.bot_utils import xiuxian_send_message
from ..common.param_checker import Cooldown
from ..common.utils import date_diff

set_auction = on_command("群交流会", priority=4, permission=GROUP and (SUPERUSER | GROUP_ADMIN | GROUP_OWNER),     block=True)
creat_auction = on_fullmatch("举行交友会", priority=5, permission=GROUP and SUPERUSER, block=True)
offer_auction = on_command("交友", priority=5, permission=GROUP, block=True)


__back_help__ = f"""
背包帮助信息:
指令：
9、群交流会开启、关闭:开启交友行功能，管理员指令，注意：会在机器人所在的全部已开启此功能的群内通报交友消息
10、交友+金额：对本次交友会的物品进行交友
非指令：
1、定时生成交友会,每天{auction_time_config['hours']}点每整点生成一场交友会
""".strip()

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
            await xiuxian_send_message(creat_auction, msg)
            return
        now_price = int(auction['now_price'])
        user_info = sql_message.get_user_message(auction['user_id'])
        user_stone = user_info.stone
        if user_stone < now_price:
            msg = f"交友会结算！竞拍者灵石小于交友，判定为捣乱，捣乱次数+1!"
            await xiuxian_send_message(creat_auction, msg)
            return
        msg = "本次交友会结束！"
        msg += f"恭喜来自群{auction['group_id']}的{user_info.user_name}道友成功交友获得：{auction['type']}-{auction['name']}!"
        await xiuxian_send_message(creat_auction, msg)

        sql_message.send_back(user_info.user_id, auction['id'], auction['name'], auction['type'], 1)
        sql_message.update_ls(user_info.user_id, int(auction['now_price']), 2)
        auction = {}
        auction_offer_time_count = 0
        return


@creat_auction.handle(parameterless=[Cooldown(at_sender=True)])
async def creat_auction_(bot: Bot, event: GroupMessageEvent):
    group_id = str(event.group_id)
    bot = await assign_bot_group(group_id=group_id)
    if group_id not in groups:
        msg = '本群尚未开启交友会功能，请联系管理员开启！'
        await xiuxian_send_message(creat_auction, msg)

    global auction
    if auction != {}:
        msg = f'本群已存在一场交友会，请等待交友会结束！'
        await xiuxian_send_message(creat_auction, msg)

    auction_id = None
    try:
        auction_id_list = get_auction_id_list()
        auction_id = random.choice(auction_id_list)
    except LookupError:
        msg = "获取不到交友物品的信息，请检查配置文件！"
        await xiuxian_send_message(creat_auction, msg)

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
        await xiuxian_send_message(creat_auction, msg)

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
        await xiuxian_send_message(creat_auction, msg)

    isUser, user_info, msg = check_user(event)
    if not isUser:
        await xiuxian_send_message(creat_auction, msg)

    global auction
    if auction == {}:
        msg = f'本群不存在交友会，请等待交友会开启！'
        await xiuxian_send_message(creat_auction, msg)

    price = args.extract_plain_text().strip()
    try:
        price = int(price)
    except ValueError:
        msg = f"请发送正确的灵石数量"
        await xiuxian_send_message(creat_auction, msg)

    now_price = auction['now_price']
    min_price = int(now_price * 0.05)  # 最低加价5%
    if price <= 0 or price <= auction['now_price'] or price > user_info.stone:
        msg = f"走开走开，别捣乱！"
        await xiuxian_send_message(creat_auction, msg)

    if price - now_price < min_price:
        msg = f"交友不得少于当前竞拍价的5%，目前最少加价为：{min_price}灵石，目前竞拍价为：{now_price}!"
        await xiuxian_send_message(creat_auction, msg)

    global auction_offer_flag, auction_offer_time_count, auction_offer_all_count
    auction_offer_flag = True  # 有人交友
    auction_offer_time_count += 1
    auction_offer_all_count += 1
    auction['user_id'] = user_info.user_id
    auction['now_price'] = price
    auction['group_id'] = group_id
    now_time = datetime.now()
    dif_time = date_diff(now_time, auction['start_time'])
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
        await xiuxian_send_message(creat_auction, msg)


@set_auction.handle(parameterless=[Cooldown(at_sender=True)])
async def set_auction_(bot: Bot, event: GroupMessageEvent):
  
    mode = args.extract_plain_text().strip()
    group_id = str(event.group_id)
    is_in_group = is_in_groups(event)  # True在，False不在

    if mode == '开启':
        if is_in_group:
            msg = f'本群已开启群交流会，请勿重复开启!'
            await xiuxian_send_message(set_auction, msg)

        else:
            config['open'].append(group_id)
            savef(config)
            msg = "已开启群交流会"
            await xiuxian_send_message(set_auction, msg)

    elif mode == '关闭':
        if is_in_group:
            config['open'].remove(group_id)
            savef(config)
            msg = f'已关闭本群交流会!'
            await xiuxian_send_message(set_auction, msg)
        else:
            msg = f'本群未开启群交流会!'
            await xiuxian_send_message(set_auction, msg)

    else:
        msg = __back_help__
        await xiuxian_send_message(set_auction, msg)


