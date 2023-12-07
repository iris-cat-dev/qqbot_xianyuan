import re

from nonebot import on_fullmatch, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GROUP, GroupMessageEvent

from .mix_elixir_config import MIXELIXIRCONFIG
from .mixelixirutil import get_mix_elixir_msg, tiaohe, check_mix, make_dict
from ..common.bot_utils import xiuxian_send_message, xiuxian_send_group_img_message, get_input_cmd
from ..common.game_sql_manager import XiuxianSqlManager
from ..common.item_json import Items
from ..common.param_checker import Cooldown, check_player
from ..common.read_buff import get_player_info, save_player_info
from ..common.xiuxian2_handle import XiuxianDateManage

sql_message = XiuxianDateManage()
sql_manager = XiuxianSqlManager()
items = Items()
cache_help = {}

mix_elixir = on_fullmatch("炼丹", priority=17, permission=GROUP, block=True)
mix_make = on_startswith("配方", priority=5, permission=GROUP, block=True)
elixir_help = on_fullmatch("炼丹帮助", priority=7, permission=GROUP, block=True)
mix_elixir_help = on_fullmatch("炼丹配方帮助", priority=7, permission=GROUP, block=True)
my_mix_elixir_info = on_fullmatch("我的炼丹信息", priority=6, permission=GROUP, block=True)
mix_elixir_sqdj_up = on_fullmatch("升级收取等级", priority=6, permission=GROUP, block=True)
mix_elixir_dykh_up = on_fullmatch("升级丹药控火", priority=6, permission=GROUP, block=True)

__elixir_help__ = f"""
炼丹帮助信息:
指令：
1、炼丹:会检测背包内的药材,自动生成配方【一次最多匹配25种药材】
2、配方:发送配方领取丹药【配方主药.....】
2、炼丹帮助:获取本帮助信息
3、炼丹配方帮助:获取炼丹配方帮助
5、我的炼丹信息:查询自己的炼丹信息
6、升级收取等级:每一个等级会增加灵田收取的数量
7、升级丹药控火:每一个等级会增加炼丹的产出数量
"""

__mix_elixir_help__ = f"""
炼丹配方信息
1、炼丹需要主药、药引、辅药
2、主药和药引控制炼丹时的冷热调和,冷热失和则炼不出丹药
3、草药的类型控制产出丹药的类型
4、来自群友猫猫头工具网址 
https://huggingface.co/spaces/chewing/liandan
"""


@mix_elixir_sqdj_up.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def mix_elixir_sqdj_up_(bot: Bot, event: GroupMessageEvent):
    """
    收取等级升级
    """
    user_info = sql_manager.get_user_info(event.user_id)
    user_id = user_info.user_id
    if int(user_info.blessed_spot_flag) == 0:
        msg = f"道友还没有洞天福地呢，请发送洞天福地购买吧~"
        await xiuxian_send_message(mix_elixir_sqdj_up, msg)

    SQDJCONFIG = MIXELIXIRCONFIG['收取等级']
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_level = mix_elixir_info['收取等级']
    if now_level >= len(SQDJCONFIG):
        msg = f"道友的收取等级已达到最高等级，无法升级了"
        await xiuxian_send_message(mix_elixir_sqdj_up, msg)

    next_level_cost = SQDJCONFIG[str(now_level + 1)]['level_up_cost']
    if mix_elixir_info['炼丹经验'] < next_level_cost:
        msg = f"下一个收取等级所需要的炼丹经验为{next_level_cost}点，道友请炼制更多的丹药再来升级吧~"
        await xiuxian_send_message(mix_elixir_sqdj_up, msg)

    mix_elixir_info['炼丹经验'] = mix_elixir_info['炼丹经验'] - next_level_cost
    mix_elixir_info['收取等级'] = now_level + 1
    save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
    msg = f"道友的收取等级目前为：{mix_elixir_info['收取等级']}级，可以使灵田收获的药材增加{mix_elixir_info['收取等级']}个！"
    await xiuxian_send_message(mix_elixir_sqdj_up, msg)


@mix_elixir_dykh_up.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def mix_elixir_dykh_up_(bot: Bot, event: GroupMessageEvent):
    """
    丹药控火升级
    """
    user_info = sql_manager.get_user_info(event.user_id)

    user_id = user_info.user_id
    DYKHCONFIG = MIXELIXIRCONFIG['丹药控火']
    mix_elixir_info = get_player_info(user_id, "mix_elixir_info")
    now_level = mix_elixir_info['丹药控火']
    if now_level >= len(DYKHCONFIG):
        msg = f"道友的丹药控火等级已达到最高等级，无法升级了"
        await xiuxian_send_message(mix_elixir_dykh_up, msg)

    next_level_cost = DYKHCONFIG[str(now_level + 1)]['level_up_cost']
    if mix_elixir_info['炼丹经验'] < next_level_cost:
        msg = f"下一个丹药控火等级所需要的炼丹经验为{next_level_cost}点，道友请炼制更多的丹药再来升级吧~"
        await xiuxian_send_message(mix_elixir_dykh_up, msg)

    mix_elixir_info['炼丹经验'] = mix_elixir_info['炼丹经验'] - next_level_cost
    mix_elixir_info['丹药控火'] = now_level + 1
    save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
    msg = f"道友的丹药控火等级目前为：{mix_elixir_info['丹药控火']}级，可以使炼丹收获的丹药增加{mix_elixir_info['丹药控火']}个！"
    await xiuxian_send_message(mix_elixir_dykh_up, msg)


@my_mix_elixir_info.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def my_mix_elixir_info_(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    mix_elixir_info = get_player_info(user_id, 'mix_elixir_info')
    l_msg = [f"☆------道友的炼丹信息------☆"]
    msg = f"药材收取等级：{mix_elixir_info['收取等级']}\n"
    msg += f"丹药控火等级：{mix_elixir_info['丹药控火']}\n"
    msg += f"丹药耐药性等级：{mix_elixir_info['丹药耐药性']}\n"
    msg += f"炼丹经验：{mix_elixir_info['炼丹经验']}\n"
    l_msg.append(msg)
    if mix_elixir_info['炼丹记录'] != {}:
        l_msg.append(f"☆------道友的炼丹记录------☆")
        i = 1
        for k, v in mix_elixir_info['炼丹记录'].items():
            msg = f"编号：{i},{v['name']}，炼成次数：{v['num']}次"
            l_msg.append(msg)
            i += 1

    await xiuxian_send_group_img_message(event.group_id, l_msg)


@elixir_help.handle(parameterless=[Cooldown(at_sender=True)])
async def elixir_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(mix_elixir_help, message=__elixir_help__)


@mix_elixir_help.handle(parameterless=[Cooldown(at_sender=True)])
async def mix_elixir_help_(_: Bot, __: GroupMessageEvent):
    await xiuxian_send_message(mix_elixir_help, message=__mix_elixir_help__)


user_ldl_dict = {}
user_ldl_flag = {}


@mix_elixir.handle(parameterless=[Cooldown(cd_time=10, at_sender=True), check_player()])
async def mix_elixir_(_: Bot, event: GroupMessageEvent):
    global user_ldl_dict, user_ldl_flag
    user_info = sql_manager.get_user_info(event.user_id)

    user_id = user_info.user_id
    user_back = sql_message.get_back_msg(user_id)
    if user_back is None:
        msg = "道友的背包空空如也，无法炼丹"
        await xiuxian_send_message(mix_elixir, msg)

    yaocai_dict = {}
    for back in user_back:
        if back.goods_type == "药材":
            yaocai_dict[back.goods_id] = items.get_data_by_item_id(back.goods_id)
            yaocai_dict[back.goods_id]['num'] = back.goods_num
            continue
        if back.goods_type == "炼丹炉":
            user_ldl_dict[user_id] = {}
            user_ldl_dict[user_id][back.goods_id] = back.goods_id
            user_ldl_dict[user_id][back.goods_id] = back.goods_name
            user_ldl_flag[user_id] = True
            continue
        else:
            continue
    if yaocai_dict == {}:
        msg = f"道友的背包内没有药材，无法炼丹！"
        await xiuxian_send_message(mix_elixir, msg)

    try:
        var = user_ldl_flag[user_id]
    except KeyError:
        msg = f"道友背包内没有炼丹炉，无法炼丹！"
        await xiuxian_send_message(mix_elixir, msg)

    yaocai_dict = await make_dict(yaocai_dict)
    finall_mix_elixir_msg = await get_mix_elixir_msg(yaocai_dict)
    if finall_mix_elixir_msg == {}:
        msg = "系统未检测到丹方，道友背包内的药材不满足！"
        await xiuxian_send_message(mix_elixir, msg)

    else:

        ldl_name = sorted(user_ldl_dict[user_id].items(), key=lambda x: x[0], reverse=False)[0][1]
        l_msg = []
        for k, v in finall_mix_elixir_msg.items():
            goods_info = items.get_data_by_item_id(v['id'])
            msg = f"名字：【{goods_info['name']}】\n"
            msg += f"效果：{goods_info['desc']}\n"
            msg += f"配方{v['配方']['配方简写']}丹炉{ldl_name}\n"
            msg += f"☆------药材清单------☆\n"
            msg += f"主药：{v['配方']['主药']},{v['配方']['主药_level']}，数量：{v['配方']['主药_num']}\n"
            msg += f"药引：{v['配方']['药引']},{v['配方']['药引_level']}，数量：{v['配方']['药引_num']}\n"
            if v['配方']['辅药_num'] != 0:
                msg += f"辅药：{v['配方']['辅药']},{v['配方']['辅药_level']}，数量：{v['配方']['辅药_num']}\n"
            l_msg.append(msg)

        if len(l_msg) > 51:
            l_msg = l_msg[:50]

        text = ""
        for msg in l_msg:
            text += msg + "\n"

        await xiuxian_send_message(mix_elixir, text)


# 配方
@mix_make.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def _mix_elixir(_: Bot, event: GroupMessageEvent):
    user_id = event.user_id
    mode, msg = get_input_cmd(event, 2)
    pattern = r"主药([\u4e00-\u9fa5]+)(\d+)药引([\u4e00-\u9fa5]+)(\d+)辅药([\u4e00-\u9fa5]+)(\d+)丹炉([\u4e00-\u9fa5]+)+"
    matched = re.search(pattern, mode)
    if matched is None:
        msg = f"请输入正确的配方！"
        await xiuxian_send_message(mix_make, msg)

    else:
        zhuyao_name = matched.groups()[0]
        zhuyao_num = int(matched.groups()[1])  # 数量一定会有
        check, zhuyao_goods_id = await check_yaocai_name_in_back(user_id, zhuyao_name, zhuyao_num)
        if not check:
            msg = f"请检查药材：{zhuyao_name} 是否在背包中，或者数量是否足够！"
            await xiuxian_send_message(mix_make, msg)

        yaoyin_name = matched.groups()[2]
        yaoyin_num = int(matched.groups()[3])  # 数量一定会有
        check, yaoyin_goods_id = await check_yaocai_name_in_back(user_id, yaoyin_name, yaoyin_num)
        if not check:
            msg = f"请检查药材：{yaoyin_name} 是否在背包中，或者数量是否足够！"
            await xiuxian_send_message(mix_make, msg)

        fuyao_name = matched.groups()[4]
        fuyao_num = int(matched.groups()[5])
        check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num)
        if not check:
            msg = f"请检查药材：{fuyao_name} 是否在背包中，或者数量是否足够！"
            await xiuxian_send_message(mix_make, msg)

        if zhuyao_name == fuyao_name:
            check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num + zhuyao_num)
            if not check:
                msg = f"请检查药材：{zhuyao_name} 是否在背包中，或者数量是否足够！"
                await xiuxian_send_message(mix_make, msg)

        if yaoyin_name == fuyao_name:
            check, fuyao_goods_id = await check_yaocai_name_in_back(user_id, fuyao_name, fuyao_num + yaoyin_num)
            if not check:
                msg = f"请检查药材：{yaoyin_name} 是否在背包中，或者数量是否足够！"
                await xiuxian_send_message(mix_make, msg)

        ldl_name = matched.groups()[6]
        check, ldl_info = await check_ldl_name_in_back(user_id, ldl_name)
        if not check:
            msg = f"请检查炼丹炉：{ldl_name} 是否在背包中！"
            await xiuxian_send_message(mix_make, msg)

        # 检测通过
        zhuyao_info = Items().get_data_by_item_id(zhuyao_goods_id)
        yaoyin_info = Items().get_data_by_item_id(yaoyin_goods_id)
        if await tiaohe(zhuyao_info, zhuyao_num, yaoyin_info, yaoyin_num):  # 调和失败
            msg = f"冷热调和失败！小心炸炉哦~"
            await xiuxian_send_message(mix_make, msg)

        else:
            elixir_config = {
                str(zhuyao_info['主药']['type']): zhuyao_info['主药']['power'] * zhuyao_num
            }
            fuyao_info = Items().get_data_by_item_id(fuyao_goods_id)
            elixir_config[str(fuyao_info['辅药']['type'])] = fuyao_info['辅药']['power'] * fuyao_num
            is_mix, id = await check_mix(elixir_config)
            if is_mix:
                mix_elixir_info = get_player_info(user_id, 'mix_elixir_info')
                goods_info = Items().get_data_by_item_id(id)
                # 加入传承
                impart_data = None
                impart_mix_per = impart_data.impart_mix_per if impart_data is not None else 0
                num = 1 + ldl_info['buff'] + mix_elixir_info['丹药控火'] + impart_mix_per
                msg = f"恭喜道友成功炼成丹药：{goods_info['name']}{num}枚"
                # 背包sql
                sql_message.send_back(user_id, id, goods_info['name'], "丹药", num)
                sql_message.update_back_j(user_id, zhuyao_goods_id, zhuyao_num)
                sql_message.update_back_j(user_id, fuyao_goods_id, fuyao_num)
                sql_message.update_back_j(user_id, yaoyin_goods_id, yaoyin_num)
                try:
                    var = mix_elixir_info['炼丹记录'][id]
                    now_num = mix_elixir_info['炼丹记录'][id]['num']
                    if now_num >= goods_info['mix_all']:
                        msg += f"该丹药道友已炼制{now_num}次，无法获得炼丹经验了~"
                    elif now_num + num >= goods_info['mix_all']:
                        exp_num = goods_info['mix_all'] - now_num
                        mix_elixir_info['炼丹经验'] += goods_info['mix_exp'] * exp_num
                        msg += f"获得炼丹经验{goods_info['mix_exp'] * exp_num}点"
                    else:
                        mix_elixir_info['炼丹经验'] += goods_info['mix_exp'] * num
                        msg += f"获得炼丹经验{goods_info['mix_exp'] * num}点"
                    mix_elixir_info['炼丹记录'][id]['num'] += num
                except:
                    mix_elixir_info['炼丹记录'][id] = {}
                    mix_elixir_info['炼丹记录'][id]['name'] = goods_info['name']
                    mix_elixir_info['炼丹记录'][id]['num'] = num
                    mix_elixir_info['炼丹经验'] += goods_info['mix_exp'] * num
                    msg += f"获得炼丹经验{goods_info['mix_exp'] * num}点"
                save_player_info(user_id, mix_elixir_info, 'mix_elixir_info')
                await xiuxian_send_message(mix_make, msg)
            else:
                msg = f"没有炼成丹药哦~就不扣你药材啦"
                await xiuxian_send_message(mix_make, msg)


async def check_yaocai_name_in_back(user_id, yaocai_name, yaocai_num):
    flag = False
    goods_id = 0
    user_back = sql_message.get_back_msg(user_id)
    for back in user_back:
        if back.goods_type == '药材':
            if Items().get_data_by_item_id(back.goods_id)['name'] == yaocai_name:
                if int(back.goods_num) >= int(yaocai_num):
                    flag = True
                    goods_id = back.goods_id
                    break
            else:
                continue
        else:
            continue
    return flag, goods_id


async def check_ldl_name_in_back(user_id, ldl_name):
    flag = False
    goods_info = {}
    user_back = sql_message.get_back_msg(user_id)
    for back in user_back:
        if back.goods_type == '炼丹炉':
            if back.goods_name == ldl_name:
                flag = True
                goods_info = Items().get_data_by_item_id(back.goods_id)
                break
            else:
                continue
        else:
            continue
    return flag, goods_info
