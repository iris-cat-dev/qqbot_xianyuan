from pathlib import Path

DATABASE = Path() / "nonebot_plugin_xiuxian3" / "resource"


class GameResource:
    BACKGROUND_FILE = DATABASE / "img" / "background.png"
    BANNER_FILE = DATABASE / "img" / "banner.png"
    TEXT_PATH = DATABASE / "img" / "info_img"
    FONT_FILE = DATABASE / "fonts" / "sarasa-mono-sc-regular.ttf"
    FONT_ORIGIN_PATH = DATABASE / "fonts" / 'font.ttf'
