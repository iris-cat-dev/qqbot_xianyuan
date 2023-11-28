import json
from pathlib import Path

DATABASE = Path() / "data" / "xiuxian"

MAX_RANK = 56

USERRANK = {
    '江湖好手': 56,
    '练气境初期': 55,  # '练气境初期': 54,
    '练气境中期': 54,
    '练气境圆满': 53,
    '筑基境初期': 52,  # '筑基境初期': 51,
    '筑基境中期': 51,
    '筑基境圆满': 50,
    '结丹境初期': 49,  # '结丹境初期': 48,
    '结丹境中期': 48,
    '结丹境圆满': 47,
    '元婴境初期': 46,  # '元婴境初期': 45,
    '元婴境中期': 45,
    '元婴境圆满': 44,
    '化神境初期': 43,  # '化神境中期': 41,
    '化神境中期': 42,
    '化神境圆满': 41,
    '炼虚境初期': 40,  # '炼虚境初期': 39,
    '炼虚境中期': 39,
    '炼虚境圆满': 38,
    '合体境初期': 37,  # '合体境初期': 36,
    '合体境中期': 36,
    '合体境圆满': 35,
    '大乘境初期': 34,  # '大乘境初期': 33,
    '大乘境中期': 33,
    '大乘境圆满': 32,
    '渡劫境初期': 31,  # '渡劫境初期': 30,
    '渡劫境中期': 30,
    '渡劫境圆满': 29,
    '真仙境初期': 28,  # '半步真仙': 37,
    '真仙境中期': 27,
    '真仙境圆满': 26,
    '玄仙境初期': 25,  # '真仙境初期': 36,
    '玄仙境中期': 24,
    '玄仙境圆满': 23,
    '地仙境初期': 22,  # '金仙境初期': 33,
    '地仙境中期': 21,
    '地仙境圆满': 20,
    '天仙境初期': 19,  # '太乙境圆满': 28,
    '天仙境中期': 18,
    '天仙境圆满': 17,
    '太乙境初期': 16,
    '太乙境中期': 15,
    '太乙境圆满': 14,
    '大罗境初期': 13,
    '大罗境中期': 12,
    '大罗境圆满': 11,
    '仙王境初期': 10,
    '仙王境中期': 9,
    '仙王境圆满': 8,
    '准帝境初期': 7,
    '准帝境中期': 6,
    '准帝境圆满': 5,
    '仙帝境初期': 4,
    '仙帝境中期': 3,
    '仙帝境圆满': 2,
    '祭道之上': 1,
}


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
        self.user_info_image = False
        self.level = list(USERRANK.keys())
        self.user_info_cd = 60  # 我的存档冷却时间
        self.level_up_cd = 60  # 突破CD(分钟)
        self.closing_exp = 30  # 闭关每分钟获取的修为
        self.put_bot = ["2906783821"]  # 接收消息qq,主qq，框架将只处理此qq的消息，
        self.main_bo = ["2906783821"]  # 负责发送消息的qq
        self.shield_group = []  # 屏蔽的群聊
        self.layout_bot_dict = {

        }
        # QQ所负责的群聊 #{群 ：bot}   其中 bot类型 []或str }
        self.sect_min_level = "元婴境圆满"
        self.sect_create_cost = 5000000
        self.closing_exp_upper_limit = 1.5  # 闭关获取修为上限（例如：1.5 下个境界的修为数*1.5）
        self.level_punishment_floor = 1  # 突破失败扣除修为，惩罚下限（百分比）
        self.level_punishment_limit = 10  # 突破失败扣除修为，惩罚上限(百分比)
        self.level_up_probability = 0.3  # 突破失败增加当前境界突破概率的比例
        self.sign_in_lingshi_lower_limit = 10000  # 每日签到灵石下限
        self.sign_in_lingshi_upper_limit = 100000  # 每日签到灵石上限
        self.tou = 1000000  # 偷灵石惩罚
        self.tou_cd = 600  # 偷灵石cd/秒
        self.tou_lower_limit = 0.01  # 偷灵石下限(百分比)
        self.tou_upper_limit = 0.2  # 偷灵石上限(百分比)
        self.remake = 200000  # 重入仙途的消费
        self.del_boss_id = []  # 支持非管理员和超管天罚boss
        self.version = "xiuxian_3"


class JsonConfig:
    def __init__(self):
        self.config_jsonpath = DATABASE / "config.json"

    def read_data(self):
        """配置数据"""
        with open(self.config_jsonpath, 'r', encoding='utf-8') as e:
            data = json.load(e)
            return data

    def write_data(self, key, group_id=None):
        """
        说明：设置修仙开启或关闭
        参数：
            key: 群聊 1 为开启， 2为关闭,默认关闭
        """
        json_data = self.read_data()
        if key == 1:
            try:
                json_data['group'].append(group_id)
            except ValueError:
                print('加入数据失败')
                return False
        elif key == 2:
            try:
                json_data['group'].remove(group_id)
            except ValueError:
                print('删除数据失败')
                return False
        else:
            print('未知key')
            return False

        with open(self.config_jsonpath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
