from pathlib import Path

DATABASE = Path() / "data" / "xiuxian"


class GameResource:
    BACKGROUND_FILE = DATABASE / "image" / "background.png"
    BOSS_IMG = DATABASE / "boss_img"
    BANNER_FILE = DATABASE / "image" / "banner.png"
    FONT_FILE = DATABASE / "font" / "sarasa-mono-sc-regular.ttf"
