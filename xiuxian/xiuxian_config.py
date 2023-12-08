from .common import singleton
from .common.game_data_manager import GameData


@singleton
class GlobalGameData(GameData):

    def __init__(self):
        self.groups = []
        super().__init__("global")


@singleton
class XiuConfig:

    def __init__(self):
        self.version = "xiuxian_3"
        self.img = False
        self.user_info_image = True

        self.user_info_cd = 120  # 我的修仙信息冷却时间
        self.level_up_cd = 60  # 突破CD(分钟)
        self.level_punishment_floor = 1  # 突破失败扣除修为，惩罚下限（百分比）
        self.level_punishment_limit = 10  # 突破失败扣除修为，惩罚上限(百分比)
        self.level_up_probability = 0.5  # 突破失败增加当前境界突破概率的比例

        self.closing_exp = 30  # 闭关每分钟获取的修为
        self.closing_hp = 50  # 闭关每分钟获取的HP
        self.closing_mp = 25  # 闭关每分钟获取的MP
        self.closing_exp_upper_limit = 1.5  # 闭关获取修为上限（例如：1.5 下个境界的修为数*1.5）

        self.sect_min_level = "元婴境圆满"
        self.sect_create_cost = 4000000

        self.sign_in_stone_lower_limit = 10000  # 每日签到灵石下限
        self.sign_in_stone_upper_limit = 100000  # 每日签到灵石上限

        self.tou = 100000  # 偷灵石惩罚
        self.tou_cd = 600  # 偷灵石cd/秒
        self.tou_lower_limit = 0.01  # 偷灵石下限(百分比)
        self.tou_upper_limit = 0.2  # 偷灵石上限(百分比)

        self.remake = 200000  # 重入仙途的消费
