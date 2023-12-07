from .common import singleton
from .common.game_data_manager import GameData
from .common.rank import RANK


@singleton
class GlobalGameData(GameData):

    def __init__(self):
        self.groups = []
        super().__init__("global")


class XiuConfig:
    def __init__(self):
        self.sql_table = ["user_xiuxian", "user_cd", "sects", "back", "BuffInfo"]  # 数据库表校验
        self.sql_user_xiuxian = ["id", "user_id", "stone", "root",
                                 "root_type", "level", "power",
                                 "create_time", "is_sign", "exp",
                                 "user_name", "level_up_cd",
                                 "level_up_rate", "sect_id",
                                 "sect_position", "hp", "mp", "atk",
                                 "atkpractice", "sect_task", "sect_contribution",
                                 "sect_elixir_get", "blessed_spot_flag",
                                 "blessed_spot_name"]  # 数据库字段校验
        self.sql_sects = ["sect_id", "sect_name", "sect_owner", "sect_scale", "sect_used_stone", "sect_fairyland",
                          "sect_materials", "mainbuff", "secbuff", "elixir_room_level"]
        self.sql_buff = ["id", "user_id", "main_buff", "sec_buff", "faqi_buff", "fabao_weapon", "armor_buff",
                         "atk_buff", "blessed_spot"]
        self.sql_back = ["user_id", "goods_id", "goods_name", "goods_type", "goods_num", "create_time", "update_time",
                         "remake", "day_num", "all_num", "action_time", "state", "bind_num"]
        self.img = False
        self.user_info_image = True
        self.level = list(RANK.keys())
        self.user_info_cd = 120  # 我的修仙信息冷却时间
        self.level_up_cd = 60  # 突破CD(分钟)
        self.closing_exp = 30  # 闭关每分钟获取的修为
        self.sect_min_level = "元婴境圆满"
        self.sect_create_cost = 4000000
        self.closing_exp_upper_limit = 1.5  # 闭关获取修为上限（例如：1.5 下个境界的修为数*1.5）
        self.level_punishment_floor = 1  # 突破失败扣除修为，惩罚下限（百分比）
        self.level_punishment_limit = 10  # 突破失败扣除修为，惩罚上限(百分比)
        self.level_up_probability = 0.3  # 突破失败增加当前境界突破概率的比例
        self.sign_in_stone_lower_limit = 10000  # 每日签到灵石下限
        self.sign_in_stone_upper_limit = 100000  # 每日签到灵石上限
        self.tou = 100000  # 偷灵石惩罚
        self.tou_cd = 600  # 偷灵石cd/秒
        self.tou_lower_limit = 0.01  # 偷灵石下限(百分比)
        self.tou_upper_limit = 0.2  # 偷灵石上限(百分比)
        self.remake = 200000  # 重入仙途的消费
        self.del_boss_id = []  # 支持非管理员和超管天罚boss
        self.version = "xiuxian_3"
