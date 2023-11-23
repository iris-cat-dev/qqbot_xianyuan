from nonebot.adapters.onebot.v11 import MessageSegment
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

async def xiuxian_send_message(matcher, message):
    """
    TODO: img cache
    """
    try:
        if XiuConfig().img:
            pic = await get_msg_pic(message)
            await matcher.finish(message=MessageSegment.image(pic), reply_message=True)
        else:
            await matcher.finish(message=message, reply_message=True)
    except ActionFailed:
        await matcher.finish("修仙界网络堵塞，发送失败!", reply_message=True)
