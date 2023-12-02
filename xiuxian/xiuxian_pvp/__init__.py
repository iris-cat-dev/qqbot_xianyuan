import random

from nonebot import on_startswith, Bot
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_img_message, get_input_at_qq, get_input_number
from ..common.param_checker import check_player,Cooldown
from ..common.read_buff import UserBuffDate
from ..common.utils import check_user
from ..common.xiuxian2_handle import XiuxianDateManage, OtherSet, leave_harm_time
from ..xiuxian_config import XiuConfig

give_stone = on_startswith("送灵石", priority=5, permission=GROUP, block=True)
steal_stone = on_startswith("偷灵石", priority=4, permission=GROUP, block=True)
# gm_command = on_command("神秘力量", permission=SUPERUSER, priority=10, block=True)
rob_stone = on_startswith("打劫", priority=5, permission=GROUP, block=True)

sql_message = XiuxianDateManage()


# qc = on_fullmatch("切磋", priority=6, permission=GROUP, block=True)
#
# @qc.handle(parameterless=[Cooldown(cd_time=300, at_sender=True)])
# async def qc_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
#     """
#     切磋，不会掉血
#     """
#     bot, send_group_id = await assign_bot(bot=bot, event=event)
#     isUser, user_info, msg = check_user(event)
#     if not isUser:
#         if XiuConfig().img:
#             pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#             await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#         else:
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await qc.finish()
#     user_id = user_info.user_id
#
#     give_qq = None  # 艾特的时候存到这里
#     for arg in args:
#         if arg.type == "at":
#             give_qq = arg.data.get("qq", "")
#     if give_qq:
#         if give_qq == str(user_id):
#             msg = "道友不会左右互搏之术！"
#             if XiuConfig().img:
#                 pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#                 await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#             else:
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await qc.finish()
#
#         player1 = {"user_id": None, "道号": None, "气血": None,
#                    "攻击": None, "真元": None, '会心': None, '防御': 0, 'exp': 0}
#         player2 = {"user_id": None, "道号": None, "气血": None,
#                    "攻击": None, "真元": None, '会心': None, '防御': 0, 'exp': 0}
#         user1 = sql_message.get_user_real_info(user_id)
#
#         user1_weapon_data = UserBuffDate(user_id).get_user_weapon_data()
#         if user1_weapon_data is not None:
#             player1['会心'] = int(user1_weapon_data['crit_buff'] * 100)
#         else:
#             player1['会心'] = 1
#
#         user2 = sql_message.get_user_real_info(give_qq)
#         user2_weapon_data = UserBuffDate(user2.user_id).get_user_weapon_data()
#         if user2_weapon_data is not None:
#             player2['会心'] = int(user2_weapon_data['crit_buff'] * 100)
#         else:
#             player2['会心'] = 1
#         player1['user_id'] = user1.user_id
#         player1['道号'] = user1.user_name
#         player1['气血'] = user1.hp
#         player1['攻击'] = user1.atk
#         player1['真元'] = user1.mp
#         player1['exp'] = user1.exp
#
#         player2['user_id'] = user2.user_id
#         player2['道号'] = user2.user_name
#         player2['气血'] = user2.hp
#         player2['攻击'] = user2.atk
#         player2['真元'] = user2.mp
#         player2['exp'] = user2.exp
#
#         result, victor = Player_fight(player1, player2, 1, bot.self_id)
#         await send_forward_msg_list(bot, event, result)
#         msg = f"获胜的是{victor}"
#         if XiuConfig().img:
#             pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#             await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#         else:
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await qc.finish()
#     else:
#         msg = "没有对方的信息！"
#         if XiuConfig().img:
#             pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#             await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#         else:
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await qc.finish()


@give_stone.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def give_stone_(bot: Bot, event: GroupMessageEvent):
    """
    送灵石
    """
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    user_stone_num = user_info.stone

    give_qq, msg = get_input_at_qq(event)
    if not give_qq:
        msg += "输入：【送灵石+@对方+数量】 "
        return await xiuxian_send_message(rob_stone, message=msg)

    give_stone_num, msg = get_input_number(event)
    if not give_stone_num:
        msg += "请输入正确的灵石数量！"
        return await xiuxian_send_message(give_stone, message=msg)

    if int(give_stone_num) > int(user_stone_num):
        msg = "道友的灵石不够，请重新输入！"
        return await xiuxian_send_message(give_stone, message=msg)

    if str(give_qq) == str(user_id):
        msg = "请不要送灵石给自己！"
        await xiuxian_send_message(give_stone, message=msg)
    else:
        give_user = sql_message.get_user_message(give_qq)
        if give_user:
            sql_message.update_ls(user_id, give_stone_num, 2)  # 减少用户灵石
            give_stone_num2 = int(give_stone_num) * 0.05
            num = int(give_stone_num) - int(give_stone_num2)
            sql_message.update_ls(give_qq, num, 1)  # 增加用户灵石
            msg = "道友通过驿站，寄送{}枚灵石给{}道友！收取手续费{}枚".format(
                give_stone_num, give_user.user_name, int(give_stone_num2)
            )
            await xiuxian_send_message(give_stone, message=msg)
        else:
            msg = "对方未踏入修仙界，不可赠送！"
            await xiuxian_send_message(give_stone, message=msg)


@steal_stone.handle(parameterless=[Cooldown(XiuConfig().tou_cd, at_sender=True)])
async def steal_stone_(bot: Bot, event: GroupMessageEvent):
    """
    偷灵石
    """
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    steal_user = None
    steal_user_stone = None
    user_stone_num = user_info.stone

    cost_stone_num = XiuConfig().tou
    if int(cost_stone_num) > int(user_stone_num):
        msg = f'“没钱还想请我们动手！”,道友因为灵石不足{cost_stone_num}请不动盗门长老被打飞！'
        await xiuxian_send_message(give_stone, message=msg)

    steal_qq, msg = get_input_at_qq(event)
    if not steal_qq:
        msg += '偷灵石+@对方qq'
        await xiuxian_send_message(give_stone, message=msg)

    if steal_qq == user_id:
        msg = '“偷自己有意思么？刷成就?”, 道友被盗门长老打飞！'
        await xiuxian_send_message(give_stone, message=msg)

    else:
        steal_user = sql_message.get_user_message(steal_qq)
        steal_user_stone = steal_user.stone

    if steal_user:
        steal_success = random.randint(0, 100)
        result = OtherSet().get_power_rate(user_info.power, steal_user.power)
        if isinstance(result, int):
            if int(steal_success) > result:
                sql_message.update_ls(user_id, cost_stone_num, 2)  # 减少手续费
                sql_message.update_ls(steal_qq, cost_stone_num, 1)  # 增加被偷的人的灵石
                msg = f'盗门长老偷窃失手了，被对方发现！赔款{cost_stone_num}灵石'
                await xiuxian_send_message(give_stone, message=msg)

            get_stone = random.randint(int(XiuConfig().tou_lower_limit * steal_user_stone),
                                       int(XiuConfig().tou_upper_limit * steal_user_stone))
            if int(get_stone) > int(steal_user_stone):
                sql_message.update_ls(user_id, steal_user_stone, 1)  # 增加偷到的灵石
                sql_message.update_ls(steal_qq, steal_user_stone, 2)  # 减少被偷的人的灵石
                msg = f"{steal_user.user_name}道友已经被榨干了~"
                await xiuxian_send_message(give_stone, message=msg)

            else:
                sql_message.update_ls(user_id, get_stone, 1)  # 增加偷到的灵石
                sql_message.update_ls(steal_qq, get_stone, 2)  # 减少被偷的人的灵石
                msg = "盗门长老得手了，共偷取{}道友{}枚灵石！".format(steal_user.user_name, get_stone)
                await xiuxian_send_message(give_stone, message=msg)

        else:
            msg = result
            await xiuxian_send_message(give_stone, message=msg)

    if not steal_qq:
        msg = "对方未踏入修仙界，不要对杂修出手！"
        await xiuxian_send_message(give_stone, message=msg)


# @gm_command.handle(parameterless=[Cooldown(at_sender=True)])
# async def gm_command_(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
#     """
#     GM加灵石
#     """
#     bot, send_group_id = await assign_bot(bot=bot, event=event)
#     give_qq = None  # 艾特的时候存到这里
#     msg = args.extract_plain_text().strip()
#     stone_num = re.findall("\d+", msg)  ## 灵石数
#     nick_name = re.findall("\D+", msg)  ## 道号
#     give_stone_num = stone_num[0]
#     if 1 <= int(give_stone_num) <= 100000000:
#         pass
#     else:
#         msg = "请输入正确的灵石数量！"
#         if XiuConfig().img:
#             pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#             await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#         else:
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await gm_command.finish()
#     for arg in args:
#         if arg.type == "at":
#             give_qq = arg.data.get("qq", "")
#     if give_qq:
#         give_user = sql_message.get_user_message(give_qq)
#         if give_user:
#             sql_message.update_ls(give_qq, give_stone_num, 1)  # 增加用户灵石
#             msg = "共赠送{}枚灵石给{}道友！".format(give_stone_num, give_user.user_name)
#             if XiuConfig().img:
#                 pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#                 await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#             else:
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await gm_command.finish()
#         else:
#             msg = "对方未踏入修仙界，不可赠送！"
#             if XiuConfig().img:
#                 pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#                 await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#             else:
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await gm_command.finish()
#     elif nick_name:
#         give_message = sql_message.get_user_message2(nick_name[0])
#         if give_message:
#             sql_message.update_ls(give_message.user_id, give_stone_num, 1)  # 增加用户灵石
#             msg = "共赠送{}枚灵石给{}道友！".format(give_stone_num, give_message.user_name)
#             if XiuConfig().img:
#                 pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#                 await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#             else:
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await gm_command.finish()
#         else:
#             msg = "对方未踏入修仙界，不可赠送！"
#             if XiuConfig().img:
#                 pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#                 await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#             else:
#                 await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#             await gm_command.finish()
#     else:
#         sql_message.update_ls_all(give_stone_num)
#         msg = f"全服通告：赠送所有用户{give_stone_num}灵石,请注意查收！"
#         if XiuConfig().img:
#             pic = await get_msg_pic(f"@{event.sender.nickname}\n" + msg)
#             await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#         else:
#             await bot.send_group_msg(group_id=int(send_group_id), message=msg)
#         await gm_command.finish()


@rob_stone.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def rob_stone_(bot: Bot, event: GroupMessageEvent):
    """
    抢灵石
    """
    _, user_info, msg = check_user(event)
    user_id = user_info.user_id

    give_qq, msg = get_input_at_qq(event)
    if not give_qq:
        msg = "指令输入错误：【打劫+@对方】"
        return await xiuxian_send_message(rob_stone, message=msg)

    player1 = {"user_id": None, "道号": None, "气血": None, "攻击": None,
               "真元": None, '会心': None, '爆伤': None, '防御': 0}
    player2 = {"user_id": None, "道号": None, "气血": None, "攻击": None,
               "真元": None, '会心': None, '爆伤': None, '防御': 0}

    if str(give_qq) == str(user_id):
        msg = "请不要偷自己刷成就！"
        await xiuxian_send_message(rob_stone, message=msg)

    user_2 = sql_message.get_user_message(give_qq)
    if user_2:
        if user_info.hp is None:
            # 判断用户气血是否为None
            sql_message.update_user_hp(user_id)
            user_info = sql_message.get_user_message(user_id)
        if user_2.hp is None:
            sql_message.update_user_hp(give_qq)
            user_2 = sql_message.get_user_message(give_qq)

        if user_2.hp <= user_2.exp / 10:
            time_2 = leave_harm_time(give_qq)
            msg = f"对方重伤藏匿了，无法抢劫！距离对方脱离生命危险还需要{time_2}分钟！"
            await xiuxian_send_message(rob_stone, message=msg)

        if user_info.hp <= user_info.exp / 10:
            time_msg = leave_harm_time(user_id)
            msg = f"道友重伤未愈，动弹不得！距离脱离生命危险还需要{time_msg}分钟！"
            await xiuxian_send_message(rob_stone, message=msg)

        player1['user_id'] = user_info.user_id
        player1['道号'] = user_info.user_name
        player1['气血'] = user_info.hp
        player1['攻击'] = user_info.atk
        player1['真元'] = user_info.mp
        player1['会心'] = int(0)
        player1['爆伤'] = int(1.5 + 0)
        user_buff_data = UserBuffDate(user_id)
        user_armor_data = user_buff_data.get_user_armor_buff_data()
        if user_armor_data is not None:
            def_buff = int(user_armor_data['def_buff'])
        else:
            def_buff = 0
        player1['防御'] = def_buff

        player2['user_id'] = user_2.user_id
        player2['道号'] = user_2.user_name
        player2['气血'] = user_2.hp
        player2['攻击'] = user_2.atk
        player2['真元'] = user_2.mp
        player1['会心'] = int(0)
        player1['爆伤'] = int(1.5 + 0)
        user_buff_data = UserBuffDate(user_2.user_id)
        user_armor_data = user_buff_data.get_user_armor_buff_data()
        if user_armor_data is not None:
            def_buff = int(user_armor_data['def_buff'])
        else:
            def_buff = 0
        player2['防御'] = def_buff

        result, victor = OtherSet().player_fight(player1, player2)
        await xiuxian_send_group_img_message(event.group_id, result)

        if victor == player1['道号']:
            foe_stone = user_2.stone
            if foe_stone > 0:
                sql_message.update_ls(user_id, int(foe_stone * 0.1), 1)
                sql_message.update_ls(give_qq, int(foe_stone * 0.1), 2)
                exps = int(user_2.exp * 0.005)
                sql_message.update_exp(user_id, exps)
                sql_message.update_j_exp(give_qq, exps / 2)
                msg = "大战一番，战胜对手，获取灵石{}枚，修为增加{}，对手修为减少{}".format(int(foe_stone * 0.1), exps,
                                                                                        exps / 2)
                await xiuxian_send_message(rob_stone, message=msg)

            else:
                exps = int(user_2.exp * 0.005)
                sql_message.update_exp(user_id, exps)
                sql_message.update_j_exp(give_qq, exps / 2)
                msg = "大战一番，战胜对手，结果对方是个穷光蛋，修为增加{}，对手修为减少{}".format(exps, exps / 2)
                await xiuxian_send_message(rob_stone, message=msg)

        elif victor == player2['道号']:
            mind_stone = user_info.stone
            if mind_stone > 0:
                sql_message.update_ls(user_id, int(mind_stone * 0.1), 2)
                sql_message.update_ls(give_qq, int(mind_stone * 0.1), 1)
                exps = int(user_info.exp * 0.005)
                sql_message.update_j_exp(user_id, exps)
                sql_message.update_exp(give_qq, exps / 2)
                msg = "大战一番，被对手反杀，损失灵石{}枚，修为减少{}，对手获取灵石{}枚，修为增加{}".format(
                    int(mind_stone * 0.1), exps,
                    int(mind_stone * 0.1), exps / 2)
                await xiuxian_send_message(rob_stone, message=msg)

            else:
                exps = int(user_info.exp * 0.005)
                sql_message.update_j_exp(user_id, exps)
                sql_message.update_exp(give_qq, exps / 2)
                msg = "大战一番，被对手反杀，修为减少{}，对手修为增加{}".format(exps, exps / 2)
                await xiuxian_send_message(rob_stone, message=msg)

        else:
            msg = "发生错误！"
            await xiuxian_send_message(rob_stone, message=msg)
    else:
        msg = "没有对方的信息！"
        await xiuxian_send_message(rob_stone, message=msg)
