import base64
import math
import re
import unicodedata
from io import BytesIO

from PIL import ImageFont, Image, ImageDraw
from nonebot import get_bot
from nonebot.adapters.onebot.v11 import MessageSegment, MessageEvent
from nonebot.exception import ActionFailed

from .game_resource import GameResource
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




class Txt2Img:
    """文字转图片"""

    def __init__(self, size=36):
        self.font = str(GameResource.FONT_FILE)
        self.font_size = int(size)
        self.use_font = ImageFont.truetype(font=self.font, size=self.font_size)
        self.upper_size = 30
        self.below_size = 30
        self.left_size = 40
        self.right_size = 55
        self.padding = 12
        self.img_width = 780
        self.black_clor = (255, 255, 255)
        self.line_num = 0

    def prepare(self, text, scale):
        text = unicodedata.normalize('NFKC', text)
        if scale:
            max_text_len = self.img_width - self.left_size - self.right_size
        else:
            max_text_len = 1080 - self.left_size - self.right_size
        use_font = self.use_font
        line_num = self.line_num
        text_len = 0
        text_new = ""
        for x in text:
            text_new += x
            text_len += use_font.getlength(x)
            if x == '\n':
                text_len = 0
            if text_len >= max_text_len:
                text_len = 0
                text_new += '\n'
        text_new = text_new.replace("\n\n", "\n")
        text_new = text_new.rstrip()
        line_num = line_num + text_new.count("\n")
        return text_new, line_num

    def draw_to(self, text, boss_name="", scale=True):
        font_size = self.font_size
        black_clor = self.black_clor
        upper_size = self.upper_size
        below_size = self.below_size
        left_size = self.left_size
        padding = self.padding
        img_width = self.img_width
        use_font = self.use_font
        text, line_num = self.prepare(text=text, scale=scale)
        if scale:
            if line_num < 4:
                blank_space = int(4 - line_num)
                line_num = 4
                text += "\n"
                for k in range(blank_space):
                    text += "\n"
            else:
                line_num = line_num
        else:
            img_width = 1080
            line_num = line_num
        img_hight = int(upper_size + below_size + font_size * (line_num + 1) + padding * line_num)
        out_img = Image.new(mode="RGB", size=(img_width, img_hight),
                            color=black_clor)
        draw = ImageDraw.Draw(out_img, "RGBA")

        # # # #
        banner_size = 12
        border_color = (220, 211, 196)
        out_padding = 15
        mi_img = Image.open(GameResource.BACKGROUND_FILE)
        mi_banner = Image.open(GameResource.BANNER_FILE).resize(
            (banner_size, banner_size), resample=3
        )

        # add background
        for x in range(int(math.ceil(img_hight / 100))):
            out_img.paste(mi_img, (0, x * 100))

        # add border
        def draw_rectangle(draw, rect, width):
            for i in range(width):
                draw.rectangle(
                    (rect[0] + i, rect[1] + i, rect[2] - i, rect[3] - i),
                    outline=border_color,
                )

        draw_rectangle(
            draw, (out_padding, out_padding, img_width - out_padding, img_hight - out_padding), 2
        )

        # add banner
        out_img.paste(mi_banner, (out_padding, out_padding))
        out_img.paste(
            mi_banner.transpose(Image.FLIP_TOP_BOTTOM),
            (out_padding, img_hight - out_padding - banner_size + 1),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT),
            (img_width - out_padding - banner_size + 1, out_padding),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM),
            (img_width - out_padding - banner_size + 1, img_hight - out_padding - banner_size + 1),
        )

        # # # #
        draw.text(
            (left_size, upper_size),
            text,
            font=use_font,
            fill=(125, 101, 89),
            spacing=padding,
        )

        return self.img2b64(out_img)

    def img2b64(self, out_img) -> str:
        """ image to base64 """
        buf = BytesIO()
        out_img.save(buf, format="PNG")
        base64_str = "base64://" + base64.b64encode(buf.getvalue()).decode()
        return base64_str


async def get_msg_pic(msg, boss_name="", scale=True):
    img = Txt2Img()
    pic = img.draw_to(msg, boss_name, scale)
    return pic

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


def get_input_at_qq(event: MessageEvent) -> (int, str):
    try:
        give_qq = event.original_message[1].data.get("qq", "")
        return give_qq, ""
    except:
        return None, "指令输入错误，"


def get_input_number(event: MessageEvent) -> (int, str):
    try:
        msg = str(event.message)
        pos = msg.find("]")
        if pos > 0:
            msg = msg[pos:]
        num = re.findall("\d+", msg)
        return int(num[0]), ""
    except:
        return None, "指令输入错误，"


def get_input_cmd(event: MessageEvent, position: int) -> (str, str):
    try:
        message = str(event.message)
        cmd = message[position:]
        return cmd, ""
    except:
        return None, "指令输入错误，"
