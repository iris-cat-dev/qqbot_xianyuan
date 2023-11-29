import base64
import re

from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent
from nonebot.exception import ActionFailed

from ..utils import get_msg_pic
from ..xiuxian_config import XiuConfig


# @help_in.handle(parameterless=[Cooldown(at_sender=True)])
# async def help_in_(bot: Bot, event: GroupMessageEvent, session_id: int = CommandObjectID()):
#     """修仙帮助"""
#     bot, send_group_id = await assign_bot(bot=bot, event=event)
#     if session_id in cache_help:
#         await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(cache_help[session_id]))
#         await help_in.finish()
#     else:
#         msg = __xiuxian_notes__
#         if XiuConfig().img:
#             pic = await get_msg_pic(msg, scale=False)
#             cache_help[session_id] = pic
#             await bot.send_group_msg(group_id=int(send_group_id), message=MessageSegment.image(pic))
#         else:
#             await help_in.finish(message=msg, reply_message=True)

def save_tmp_img(img: bytes):
    path = "/Users/bytedance/Library/Containers/com.tencent.qq/Data/Documents/LiteLoaderQQNT/plugins_data/LLOneBot/tmp.png"
    with open(path, 'wb') as f:
        f.write(img)
    return path


async def xiuxian_send_message(matcher, message):
    """
    TODO: img cache
    """
    try:
        if XiuConfig().img:
            pic = await get_msg_pic(message)
            base64_data = base64.b64decode(pic.encode())
            path = save_tmp_img(base64_data[6:])
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
    base64_data = base64.b64decode(pic.encode())
    path = save_tmp_img(base64_data[6:])
    msg_seg = MessageSegment.image(path)
    data['message'].append(msg_seg)
    await get_bot().call_api(api, **data)


def get_input_at_qq(event: MessageEvent):
    try:
        give_qq = event.original_message[1].data.get("qq", "")
        return give_qq, ""
    except:
        return None, "指令输入错误，"


def get_input_number(event: MessageEvent):
    try:
        msg = str(event.message)
        pos = msg.find("]")
        if pos > 0:
            msg = msg[pos:]
        num = re.findall("\d+", msg)
        return num[0], ""
    except:
        return None, "指令输入错误，"
