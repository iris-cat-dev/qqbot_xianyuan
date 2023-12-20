import re

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent
from nonebot.exception import ActionFailed

from .send_image_tool import get_msg_pic, save_tmp_img
from ..xiuxian_config import XiuConfig


async def xiuxian_send_message(matcher, message):
    """
    TODO: img cache
    """
    try:
        if XiuConfig().img:
            pic = await get_msg_pic(message)
            path = save_tmp_img(pic)
            await matcher.finish(message=MessageSegment.image(path), reply_message=True)
        else:
            await matcher.finish(message=message, reply_message=True)
    except ActionFailed:
        await matcher.finish("修仙界网络堵塞，发送失败!", reply_message=True)


async def xiuxian_send_img_message(matcher, img):
    try:
        path = save_tmp_img(img)
        await matcher.finish(message=MessageSegment.image(path), reply_message=True)
    except ActionFailed:
        await matcher.finish("修仙界网络堵塞，发送失败!", reply_message=True)


async def xiuxian_send_group_message(group_id, message):
    """

    """
    api = 'send_msg'
    data = {
        'group_id': int(group_id),
        "message_type": "group",
        "message": []
    }
    msg_seg = MessageSegment.text(message)
    data['message'].append(msg_seg)
    await get_bot().call_api(api, **data)


async def xiuxian_send_group_img_message(group_id, msg_list: list):
    """

    """
    api = 'send_msg'
    data = {
        'group_id': int(group_id),
        "message_type": "group",
        "message": []
    }
    text = ""
    for msg in msg_list:
        text += msg + "\n"

    pic = await get_msg_pic(text)
    path = save_tmp_img(pic)
    msg_seg = MessageSegment.image(path)
    data['message'].append(msg_seg)
    await get_bot().call_api(api, **data)


def remove_at_qq(msg):
    start_pos = msg.find("[")
    end_pos = msg.find("]")
    if start_pos > 0:
        msg = msg.replace(msg[start_pos:end_pos + 1], "")
    return msg


def get_input_at_qq(event: MessageEvent) -> (int, str):
    try:
        give_qq = event.original_message[1].data.get("qq", "")
        return int(give_qq), ""
    except:
        return None, "指令输入错误，"


def get_input_number(event: MessageEvent) -> (int, str):
    try:
        msg = str(event.message)
        msg = remove_at_qq(msg)
        num = re.findall("\d+", msg)
        return int(num[0]), ""
    except:
        return None, "指令输入错误，"


def get_input_cmd(event: MessageEvent, position: int) -> (str, str):
    try:
        msg = str(event.message)
        msg = remove_at_qq(msg)
        cmd = msg[position:]
        return cmd, ""
    except:
        return None, "指令输入错误，"
