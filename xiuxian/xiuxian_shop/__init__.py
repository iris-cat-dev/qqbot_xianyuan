import asyncio
import json
import os
import re
from pathlib import Path

from nonebot import on_fullmatch, Bot, on_startswith
from nonebot.adapters.onebot.v11 import GROUP, GroupMessageEvent

from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_img_message
from ..common.param_checker import check_admin, check_player
from ..lay_out import Cooldown, CooldownIsolateLevel
from ..read_buff import get_sec_msg, get_main_info_msg, get_armor_info_msg, get_weapon_info_msg
from ..utils import check_user
from ..xiuxian2_handle import XiuxianDateManage, items

shop_list = on_fullmatch("坊市查询", priority=8, permission=GROUP, block=True)
shop_added = on_startswith("坊市上架", priority=10, permission=GROUP, block=True)
shop_off = on_startswith("坊市下架", priority=5, permission=GROUP, block=True)
shop_off_all = on_fullmatch("清空坊市", priority=3, rule=check_admin(), block=True)
shop_buy = on_startswith("坊市购买", priority=5, block=True)
goods_re_root = on_startswith("坊市回收", priority=6, permission=GROUP, block=True)
chakan_wupin = on_startswith("查看物品大全", priority=25, permission=GROUP, block=True)
shop_added_by_admin = on_startswith("系统上架坊市", priority=5, rule=check_admin(), block=True)
shop_help = on_fullmatch("坊市帮助", priority=8, permission=GROUP, block=True)

buy_lock = asyncio.Lock()

PATH = Path(__file__).parent
FILEPATH = PATH / 'shop.json'

sql_message = XiuxianDateManage()


def read_shop():
    with open(FILEPATH, "r", encoding="UTF-8") as f:
        data = f.read()
    return json.loads(data)


def save_shop(data):
    data = json.dumps(data, ensure_ascii=False, indent=4)
    savemode = "w" if os.path.exists(FILEPATH) else "x"
    with open(FILEPATH, mode=savemode, encoding="UTF-8") as f:
        f.write(data)
        f.close()
    return True


def get_shop_data(group_id):
    try:
        data = read_shop()
    except:
        data = {}
    try:
        data[group_id]
    except:
        data[group_id] = {}
    save_shop(data)
    return data


def reset_dict_num(dict_):
    i = 1
    temp_dict = {}
    for k, v in dict_.items():
        temp_dict[i] = v
        temp_dict[i]['编号'] = i
        i += 1
    return temp_dict


__shop_help__ = f"""
坊市帮助信息:
指令：
1、坊市购买+物品编号:购买坊市内的物品
2、坊市查询:查询坊市在售物品
3、坊市上架:坊市上架 物品 金额 数量，上架背包内的物品,最低金额50w
4、坊市下架+物品编号：下架坊市内的物品，管理员和群主可以下架任意编号的物品！
5、坊市回收+物品名字：将物品炼化为灵石,支持批量炼金和绑定丹药炼金
6、系统上架坊市:系统商城，坊市上架 物品 金额 数量，上架任意存在的物品，超管权限
7、清空坊市:清空本群坊市,管理员权限
8、查看物品大全:支持类型【功法|神通|丹药|合成丹药|法器|防具】
""".strip()


@shop_help.handle(parameterless=[Cooldown(at_sender=True)])
async def back_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(shop_help, message=__shop_help__)


@shop_list.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def shop_list_(bot: Bot, event: GroupMessageEvent):
    """
    坊市查看
    """
    group_id = str(event.group_id)
    shop_data = get_shop_data(group_id)
    data_list = []
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        await xiuxian_send_message(shop_list, msg)

    for k, v in shop_data[group_id].items():
        msg = f"编号：{k}\n"
        msg += f"{v['desc']}"
        msg += f"\n价格：{v['price']}枚灵石\n"
        if v['user_id'] != 0:
            msg += f"拥有人：{v['user_name']} 道友\n"
            msg += f"批次数量：{v['number']}"
        else:
            msg += f"系统出售\n"
            msg += f"批次数量：{v['number']}"
        data_list.append(msg)

    await xiuxian_send_group_img_message(event.group_id, data_list)


@shop_buy.handle(parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GROUP), check_player()])
async def shop_buy_(bot: Bot, event: GroupMessageEvent):
    """
    购物
    """
    async with buy_lock:
        _, user_info, msg = check_user(event)

        user_id = user_info.user_id
        group_id = str(event.group_id)
        shop_data = get_shop_data(group_id)
        if shop_data[group_id] == {}:
            msg = "坊市目前空空如也！"
            await xiuxian_send_message(shop_buy, msg)

        try:
            msg = str(event.message)
            arg = re.findall("\d+", msg)
            arg = int(arg[0])
            if arg <= 0 or arg > len(shop_data[group_id]):
                msg = "请输入正确的编号！"
                await xiuxian_send_message(shop_buy, msg)

        except ValueError:
            msg = "请输入正确的编号！"
            await xiuxian_send_message(shop_buy, msg)

        goods_price = shop_data[group_id][str(arg)]['price']
        if user_info.stone < goods_price:
            msg = '没钱还敢来买东西！！'
            await xiuxian_send_message(shop_buy, msg)

        elif int(user_id) == int(shop_data[group_id][str(arg)]['user_id']):
            msg = "道友自己的东西就不要自己购买啦！"
            await xiuxian_send_message(shop_buy, msg)

        else:
            sql_message.update_ls(user_id, goods_price, 2)
            shop_user_id = shop_data[group_id][str(arg)]['user_id']
            shop_goods_name = shop_data[group_id][str(arg)]['goods_name']
            shop_user_name = shop_data[group_id][str(arg)]['user_name']
            shop_goods_id = shop_data[group_id][str(arg)]['goods_id']
            shop_goods_type = shop_data[group_id][str(arg)]['goods_type']
            shop_goods_number = shop_data[group_id][str(arg)]['number']
            sql_message.send_back(user_id, shop_goods_id, shop_goods_name, shop_goods_type, goods_num=shop_goods_number)
            if shop_user_id == 0:  # 0为系统
                msg = f"道友成功购买物品{shop_goods_name}，消耗灵石{goods_price}枚，数量{shop_goods_number}！"
            else:
                service_charge = int(goods_price * 0.1)  # 手续费10%
                give_stone = goods_price - service_charge
                msg = f"道友成功购买{shop_user_name}道友寄售的物品{shop_goods_name}，消耗灵石{goods_price}枚，数量{shop_goods_number}，坊市收取手续费：{service_charge}枚灵石！"
                sql_message.update_ls(shop_user_id, give_stone, 1)
            del shop_data[group_id][str(arg)]
            shop_data[group_id] = reset_dict_num(shop_data[group_id])
            save_shop(shop_data)
            await xiuxian_send_message(shop_buy, msg)


@shop_added_by_admin.handle(
    parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GROUP, parallel=1), check_player()])
async def shop_added_by_admin_(bot: Bot, event: GroupMessageEvent):
    """
    系统上架坊市
    """
    message = str(event.message)
    args = message.split(" ")
    if len(args) < 2:
        msg = "请输入正确指令！例如：系统上架坊市 物品 金额 数量"
        await xiuxian_send_message(shop_added_by_admin, msg)

    goods_name = args[1]
    goods_id = -1
    for k, v in items.items.items():
        if goods_name == v['name']:
            goods_id = k
            break
        else:
            continue
    if goods_id == -1:
        msg = f"不存在物品：{goods_name}的信息，请检查名字是否输入正确！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    price = None
    try:
        price = args[2]
    except LookupError:
        msg = "请输入正确指令！例如：系统坊市上架 物品 金额 数量"
        await xiuxian_send_message(shop_added_by_admin, msg)

    try:
        price = int(price)
        if price < 0:
            msg = "请不要设置负数！"
            await xiuxian_send_message(shop_added_by_admin, msg)

    except LookupError:
        msg = "请输入正确的金额！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    try:
        number = args[3]
        if int(number) >= 1:
            number = int(number)
        else:
            number = 1
    except:
        number = 1

    group_id = str(event.group_id)
    shop_data = get_shop_data(group_id)
    if shop_data == {}:
        shop_data[group_id] = {}
    goods_info = items.get_data_by_item_id(goods_id)

    id_ = len(shop_data[group_id]) + 1
    shop_data[group_id][id_] = {}
    shop_data[group_id][id_]['user_id'] = 0
    shop_data[group_id][id_]['goods_name'] = goods_name
    shop_data[group_id][id_]['goods_id'] = goods_id
    shop_data[group_id][id_]['goods_type'] = goods_info['type']
    shop_data[group_id][id_]['desc'] = get_item_msg(goods_id)
    shop_data[group_id][id_]['number'] = number
    shop_data[group_id][id_]['price'] = price
    shop_data[group_id][id_]['user_name'] = '系统'
    save_shop(shop_data)
    msg = f"物品：{goods_name}成功上架坊市，金额：{price}枚灵石，数量{number}！"
    await xiuxian_send_message(shop_added_by_admin, msg)


@shop_added.handle(parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GROUP), check_player()])
async def shop_added_(bot: Bot, event: GroupMessageEvent):
    """
    上架坊市
    """
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    message = str(event.message)
    args = message.split(" ")
    if len(args) < 2:
        msg = "请输入正确指令！例如：坊市上架 物品 金额 数量"
        await xiuxian_send_message(shop_added_by_admin, msg)

    goods_name = args[1]
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await xiuxian_send_message(shop_added, msg)

    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    goods_bind_num = None
    for back in back_msg:
        if goods_name == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            goods_type = back.goods_type
            goods_state = back.state
            goods_num = back.goods_num
            goods_bind_num = back.bind_num
            break
    if not in_flag:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        await xiuxian_send_message(shop_added, msg)

    price = None
    try:
        price = args[2]
    except LookupError:
        msg = "请输入正确的指令！例如：坊市上架 物品 金额 数量"
        await xiuxian_send_message(shop_added, msg)

    try:
        price = int(price)
        if price < 0:
            msg = "请不要设置负数！"
            await xiuxian_send_message(shop_added, msg)

    except ValueError:
        msg = "请输入正确的金额！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    try:
        number = args[3]
        if 1 <= int(number) <= int(goods_num):
            number = int(number)
        else:
            number = 1
    except:
        number = 1

    if price < 100000:
        msg = "这位道友，坊市也要赚钱，请输入大于 100000 金额"
        await xiuxian_send_message(shop_added_by_admin, msg)

    if goods_type == "装备" and int(goods_state) == 1 and int(goods_num) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法上架！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    if int(goods_num) <= int(goods_bind_num):
        msg = f"该物品是绑定物品，无法上架！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    if goods_type == "丹药" or goods_type == "聚灵旗" or goods_type == "炼丹炉":
        pass

    group_id = str(event.group_id)
    shop_data = get_shop_data(group_id)

    num = 0
    for k, v in shop_data[group_id].items():
        if str(v['user_id']) == str(user_info.user_id):
            num += 1
        else:
            pass
    if num >= 10:
        msg = f"每人只可上架10个物品！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    if shop_data == {}:
        shop_data[group_id] = {}
    id_ = len(shop_data[group_id]) + 1
    shop_data[group_id][id_] = {}
    shop_data[group_id][id_]['user_id'] = user_id
    shop_data[group_id][id_]['goods_name'] = goods_name
    shop_data[group_id][id_]['goods_id'] = goods_id
    shop_data[group_id][id_]['goods_type'] = goods_type
    shop_data[group_id][id_]['desc'] = get_item_msg(goods_id)
    shop_data[group_id][id_]['number'] = number
    shop_data[group_id][id_]['price'] = price
    shop_data[group_id][id_]['user_name'] = user_info.user_name
    sql_message.update_back_j(user_id, goods_id, num=number)
    save_shop(shop_data)
    msg = f"物品：{goods_name}成功上架坊市,金额：{price}枚灵石,数量{number}！"
    await xiuxian_send_message(shop_added_by_admin, msg)


@goods_re_root.handle(parameterless=[Cooldown(at_sender=True)])
async def goods_re_root_(bot: Bot, event: GroupMessageEvent):
    """
    物品回收
    """
    user_id = event.user_id
    message = str(event.message)
    args = message[4:]
    if args is None:
        msg = "请输入要回收的物品！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    goods_name = args
    back_msg = sql_message.get_back_msg(user_id)  # 背包sql信息,list(back)
    if back_msg is None:
        msg = "道友的背包空空如也！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    in_flag = False  # 判断指令是否正确，道具是否在背包内
    goods_id = None
    goods_type = None
    goods_state = None
    goods_num = None
    for back in back_msg:
        if goods_name == back.goods_name:
            in_flag = True
            goods_id = back.goods_id
            goods_type = back.goods_type
            goods_state = back.state
            goods_num = back.goods_num
            break
    if not in_flag:
        msg = f"请检查该道具 {goods_name} 是否在背包内！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    if goods_type == "装备" and int(goods_state) == 1 and int(goods_num) == 1:
        msg = f"装备：{goods_name}已经被道友装备在身，无法炼金！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    if get_item_msg_rank(goods_id) == 520:
        msg = "此类物品不支持！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    try:
        if 1 <= int(args[1]) <= int(goods_num):
            num = int(args[1])
        else:
            num = 1
    except:
        num = 1

    price = int(6000000 - get_item_msg_rank(goods_id) * 100000) * num
    if price <= 0:
        msg = f"物品：{goods_name}回收失败，获得{price}枚灵石！"
        await xiuxian_send_message(shop_added_by_admin, msg)

    sql_message.update_back_j(user_id, goods_id, num=num)
    sql_message.update_ls(user_id, price, 1)
    msg = f"物品：{goods_name} 数量：{num} 回收成功，获得{price}枚灵石！"
    await xiuxian_send_message(shop_added_by_admin, msg)


@shop_off.handle(parameterless=[Cooldown(1.4, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_off_(bot: Bot, event: GroupMessageEvent):
    """
    下架商品
    """

    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    group_id = str(event.group_id)
    shop_data = get_shop_data(group_id)
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        await xiuxian_send_message(shop_off, msg)

    message = str(event.message)
    arg = re.findall("\d+", message)  # boss编号

    try:
        arg = int(arg[0])
        if arg <= 0 or arg > len(shop_data[group_id]):
            msg = "请输入正确的编号！"
            await xiuxian_send_message(shop_off, msg)

    except ValueError:
        msg = "请输入正确的编号！"
        await xiuxian_send_message(shop_off, msg)

    if shop_data[group_id][str(arg)]['user_id'] == user_id:
        sql_message.send_back(user_id, shop_data[group_id][str(arg)]['goods_id'],
                              shop_data[group_id][str(arg)]['goods_name'], shop_data[group_id][str(arg)]['goods_type'],
                              shop_data[group_id][str(arg)]['number'])
        msg = f"成功下架物品：{shop_data[group_id][str(arg)]['goods_name']},数量{shop_data[group_id][str(arg)]['number']}！"
        del shop_data[group_id][str(arg)]
        shop_data[group_id] = reset_dict_num(shop_data[group_id])
        save_shop(shop_data)
        await xiuxian_send_message(shop_off, msg)

    elif event.sender.role == "admin" or event.sender.role == "owner" or event.get_user_id() in bot.config.superusers:
        if shop_data[group_id][str(arg)]['user_id'] == 0:  # 这么写为了防止bot.send发送失败，不结算
            msg = f"成功下架物品：{shop_data[group_id][str(arg)]['goods_name']},数量{shop_data[group_id][str(arg)]['number']}！"
            del shop_data[group_id][str(arg)]
            shop_data[group_id] = reset_dict_num(shop_data[group_id])
            save_shop(shop_data)
            await xiuxian_send_message(shop_off, msg)

        else:
            sql_message.send_back(shop_data[group_id][str(arg)]['user_id'], shop_data[group_id][str(arg)]['goods_id'],
                                  shop_data[group_id][str(arg)]['goods_name'],
                                  shop_data[group_id][str(arg)]['goods_type'], shop_data[group_id][str(arg)]['number'])
            msg = f"成功下架{shop_data[group_id][str(arg)]['user_id']}的物品：{shop_data[group_id][str(arg)]['goods_name']},数量{shop_data[group_id][str(arg)]['number']}！"
            del shop_data[group_id][str(arg)]
            shop_data[group_id] = reset_dict_num(shop_data[group_id])
            save_shop(shop_data)
            await xiuxian_send_message(shop_off, msg)

    else:
        msg = "这东西不是你的！"
        await xiuxian_send_message(shop_off, msg)


@chakan_wupin.handle(parameterless=[Cooldown(at_sender=True)])
async def chakan_wupin_(bot: Bot, event: GroupMessageEvent):
    """
    查看修仙界所有物品列表
    """
    message = str(event.message)
    args = message[6:]

    list_tp = []
    if args not in ["功法", "神通", "丹药", "合成丹药", "法器", "防具"]:
        msg = "请输入正确类型【功法|神通|丹药|合成丹药|法器|防具】！！！"
        await xiuxian_send_message(shop_off, msg)

    else:
        if args == "功法":
            gf_data = items.get_data_by_item_type(['功法'])
            for x in gf_data:
                name = gf_data[x]['name']
                rank = gf_data[x]['level']
                msg = "※{}:{}".format(rank, name)
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "神通":
            st_data = items.get_data_by_item_type(['神通'])
            for x in st_data:
                name = st_data[x]['name']
                rank = st_data[x]['level']
                msg = "※{}:{}".format(rank, name)
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "丹药":
            dy_data = items.get_data_by_item_type(['丹药'])
            for x in dy_data:
                name = dy_data[x]['name']
                rank = dy_data[x]['境界']
                desc = dy_data[x]['desc']
                msg = "※{}丹药:{}，效果：{}\n".format(rank, name, desc)
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id,
                                              "content": msg}})
        elif args == "合成丹药":
            hcdy_data = items.get_data_by_item_type(['合成丹药'])
            for x in hcdy_data:
                name = hcdy_data[x]['name']
                rank = hcdy_data[x]['境界']
                desc = hcdy_data[x]['desc']
                msg = "※{}丹药:{}，效果：{}\n\n".format(rank, name, desc)
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id, "content": msg}})
        elif args == "法器":
            fq_data = items.get_data_by_item_type(['法器'])
            for x in fq_data:
                name = fq_data[x]['name']
                rank = fq_data[x]['level']
                msg = "※{}:{}".format(rank, name)
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id, "content": msg}})
        elif args == "防具":
            fj_data = items.get_data_by_item_type(['防具'])
            for x in fj_data:
                name = fj_data[x]['name']
                rank = fj_data[x]['level']
                msg = "※{}:{}".format(rank, name)
                list_tp.append(
                    {"type": "node", "data": {"name": f"修仙界物品列表{args}", "uin": bot.self_id, "content": msg}})

        msg_list = []
        for item in list_tp:
            msg_list.append(item["data"]["content"])
        await xiuxian_send_group_img_message(event.group_id, msg_list)


@shop_off_all.handle(parameterless=[Cooldown(60, isolate_level=CooldownIsolateLevel.GROUP, parallel=1)])
async def shop_off_all_(bot: Bot, event: GroupMessageEvent):
    """
    坊市清空
    """
    _, user_info, msg = check_user(event)

    group_id = str(event.group_id)
    shop_data = get_shop_data(group_id)
    if shop_data[group_id] == {}:
        msg = "坊市目前空空如也！"
        await xiuxian_send_message(shop_off_all, msg)

    list_msg = []
    msg = ""
    num = len(shop_data[group_id])
    for x in range(num):
        x = num - x
        if shop_data[group_id][str(x)]['user_id'] == 0:  # 这么写为了防止bot.send发送失败，不结算
            msg += f"成功下架物品：{shop_data[group_id][str(x)]['goods_name']}，数量{shop_data[group_id][str(x)]['number']}!\n"
        else:
            sql_message.send_back(shop_data[group_id][str(x)]['user_id'], shop_data[group_id][str(x)]['goods_id'],
                                  shop_data[group_id][str(x)]['goods_name'],
                                  shop_data[group_id][str(x)]['goods_type'], shop_data[group_id][str(x)]['number'])
            msg += f"成功下架{shop_data[group_id][str(x)]['user_id']}的物品：{shop_data[group_id][str(x)]['goods_name']},数量{shop_data[group_id][str(x)]['number']}!\n"

    del shop_data[group_id][str(x)]
    shop_data[group_id] = reset_dict_num(shop_data[group_id])
    save_shop(shop_data)
    list_msg.append({"type": "node", "data": {"name": f"执行清空坊市ing", "uin": bot.self_id, "content": msg}})

    msg_list = []
    for item in list_msg:
        msg_list.append(item["data"]["content"])
    await xiuxian_send_group_img_message(event.group_id, msg_list)


def get_item_msg_rank(goods_id):
    """
    获取单个物品的rank
    """
    item_info = items.get_data_by_item_id(goods_id)
    if item_info['type'] == '丹药':
        msg = item_info['rank']
    elif item_info['item_type'] == '神通':
        msg = item_info['rank']
    elif item_info['item_type'] == '功法':
        msg = item_info['rank']
    elif item_info['item_type'] == '防具':
        msg = item_info['rank']
    elif item_info['item_type'] == '法器':
        msg = item_info['rank']
    elif item_info['item_type'] == "药材":
        msg = item_info['rank']
    elif item_info['item_type'] == "聚灵旗":
        msg = item_info['rank']
    elif item_info['item_type'] == "炼丹炉":
        msg = item_info['rank']
    else:
        msg = 520
    return int(msg)


def get_item_msg(goods_id):
    """
    获取单个物品的消息
    """
    item_info = items.get_data_by_item_id(goods_id)
    if item_info['type'] == '丹药':
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == '神通':
        msg = f"名字：{item_info['name']}\n"
        msg += f"品阶：{item_info['level']}\n"
        msg += f"效果：{get_sec_msg(item_info)}"

    elif item_info['item_type'] == '功法':
        msg = f"名字：{item_info['name']}\n"
        msg += f"品阶：{item_info['level']}\n"
        msg += f"效果：{get_main_info_msg(goods_id)[1]}"

    elif item_info['item_type'] == '防具':
        msg = get_armor_info_msg(goods_id, item_info)

    elif item_info['item_type'] == '法器':
        msg = get_weapon_info_msg(goods_id, item_info)

    elif item_info['item_type'] == "药材":
        msg = get_yaocai_info_msg(goods_id, item_info)

    elif item_info['item_type'] == "聚灵旗":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    elif item_info['item_type'] == "炼丹炉":
        msg = f"名字：{item_info['name']}\n"
        msg += f"效果：{item_info['desc']}"

    else:
        msg = '不支持的物品'
    return msg


YAOCAIINFOMSG = {
    "-1": "性寒",
    "0": "性平",
    "1": "性热",
    "2": "生息",
    "3": "养气",
    "4": "炼气",
    "5": "聚元",
    "6": "凝神",
}


def get_yaocai_info(yaocai_info):
    msg = f"主药 {YAOCAIINFOMSG[str(yaocai_info['主药']['h_a_c']['type'])]}"
    msg += f"{yaocai_info['主药']['h_a_c']['power']}"
    msg += f" {YAOCAIINFOMSG[str(yaocai_info['主药']['type'])]}"
    msg += f"{yaocai_info['主药']['power']}\n"
    msg += f"药引 {YAOCAIINFOMSG[str(yaocai_info['药引']['h_a_c']['type'])]}"
    msg += f"{yaocai_info['药引']['h_a_c']['power']}"
    msg += f"辅药 {YAOCAIINFOMSG[str(yaocai_info['辅药']['type'])]}"
    msg += f"{yaocai_info['辅药']['power']}"

    return msg


def get_yaocai_info_msg(goods_id, item_info):
    msg = f"名字：{item_info['name']}\n"
    msg += f"品级：{item_info['level']}\n"
    msg += get_yaocai_info(item_info)
    return msg
