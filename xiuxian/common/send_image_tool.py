import math
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Union
from base64 import b64encode
from PIL import Image, ImageDraw, ImageFont

from nonebot_plugin_xiuxian3.xiuxian.common.game_resource import GameResource


async def convert_img(
    img: Union[Image.Image, str, Path, bytes], is_base64: bool = False
):
    """
    :说明:
      将PIL.Image对象转换为bytes或者base64格式。
    :参数:
      * img (Image): 图片。
      * is_base64 (bool): 是否转换为base64格式, 不填默认转为bytes。
    :返回:
      * res: bytes对象或base64编码图片。
    """
    if isinstance(img, Image.Image):
        img = img.convert('RGB')
        result_buffer = BytesIO()
        img.save(result_buffer, format='JPEG', quality=50, subsampling=0)
        res = result_buffer.getvalue()
        if is_base64:
            res = 'base64://' + b64encode(res).decode()
        return res
    elif isinstance(img, bytes):
        return 'base64://' + b64encode(img).decode()
    else:
        return f'[CQ:image,file=file:///{str(img)}]'



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
        img_height = int(upper_size + below_size + font_size * (line_num + 1) + padding * line_num)
        out_img = Image.new(mode="RGB", size=(img_width, img_height), color=black_clor)
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
        for x in range(int(math.ceil(img_height / 100))):
            out_img.paste(mi_img, (0, x * 100))

        # add border
        def draw_rectangle(draw, rect, width):
            for i in range(width):
                draw.rectangle(
                    (rect[0] + i, rect[1] + i, rect[2] - i, rect[3] - i),
                    outline=border_color,
                )

        draw_rectangle(
            draw, (out_padding, out_padding, img_width - out_padding, img_height - out_padding), 2
        )

        # add banner
        out_img.paste(mi_banner, (out_padding, out_padding))
        out_img.paste(
            mi_banner.transpose(Image.FLIP_TOP_BOTTOM),
            (out_padding, img_height - out_padding - banner_size + 1),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT),
            (img_width - out_padding - banner_size + 1, out_padding),
        )
        out_img.paste(
            mi_banner.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM),
            (img_width - out_padding - banner_size + 1, img_height - out_padding - banner_size + 1),
        )

        # # # #
        draw.text(
            (left_size, upper_size),
            text,
            font=use_font,
            fill=(125, 101, 89),
            spacing=padding,
        )

        buf = BytesIO()
        out_img.save(buf, format="JPEG", quality=5)
        return buf.getvalue()


async def get_msg_pic(msg, boss_name="", scale=True):
    img = Txt2Img()
    pic = img.draw_to(msg, boss_name, scale)
    return pic


def save_tmp_img(img: bytes):
    path = "/Users/bytedance/Library/Containers/com.tencent.qq/Data/Documents/LiteLoaderQQNT/plugins_data/LLOneBot/tmp.jpg"
    with open(path, 'wb') as f:
        f.write(img)
    return path

