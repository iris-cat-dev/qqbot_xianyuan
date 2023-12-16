import datetime
import sqlite3
from collections import namedtuple
from pathlib import Path

from nonebot import logger

from . import singleton
from .rank import Rank
from .root import Root
from .xiuxian2_handle import XiuxianDateManage
from ..xiuxian_config import XiuConfig

rank = Rank()
root = Root()
game_config = XiuConfig()
DATABASE = Path() / "data" / "xiuxian"

UserInfo = namedtuple("UserData", [
    "id",
    "user_id",
    "stone",
    "root",
    "root_type",
    "level",
    "power",
    "create_time",
    "is_sign",
    "exp",
    "user_name",
    "level_up_cd",
    "level_up_rate",
    "sect_id",
    "sect_position",
    "hp",
    "mp",
    "atk",
    "atkpractice",
    "sect_task",
    "sect_contribution",
    "sect_elixir_get",
    "blessed_spot_flag",
    "blessed_spot_name"
])

UserCd = namedtuple("UserCd", [
    "user_id",
    "type",
    "create_time",
    "scheduled_time"
])

GoodsInfo = namedtuple("GoodsInfo", [
    "user_id",
    "goods_id",
    "goods_name",
    "goods_type",
    "goods_num",
    "create_time",
    "update_time",
    "remake",
    "day_num",
    "all_num",
    "action_time",
    "state",
    "bind_num"
])


@singleton
class XiuxianSqlManager:

    def __init__(self):
        self.connect = XiuxianDateManage().get_connect()
        # self.database_path = DATABASE
        # if not self.database_path.exists():
        #     self.database_path.mkdir(parents=True)
        #     self.database_path /= "xiuxian.db"
        #     self.conn = sqlite3.connect(self.database_path)
        #     # self._create_file()
        # else:
        #     self.database_path /= "xiuxian.db"
        #     self.conn = sqlite3.connect(self.database_path)
        # logger.info(f"修仙数据库已连接！")

    def close(self):
        self.connect.close()
        logger.info(f"修仙数据库关闭！")

    def get_user_info(self, user_id: int):
        """
        获取用户基础信息
        """
        cur = self.connect.cursor()
        sql = f"select * from user_xiuxian where user_id=?"
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if not result:
            return None
        else:
            return UserInfo(*result)

    def get_user_list(self, only_active=False) -> list[int]:
        """
        获取用户列表
        """
        cur = self.connect.cursor()
        if only_active:
            sql = f"select user_id from user_xiuxian WHERE is_sign=1"
        else:
            sql = f"select user_id from user_xiuxian"
        cur.execute(sql)
        result = cur.fetchall()
        if not result:
            return []
        else:
            return [item[0] for item in result]

    def get_top1_user(self, only_active=False):
        """
        获取修为第一的用户
        """
        cur = self.connect.cursor()
        if only_active:
            sql = f"select * from user_xiuxian WHERE is_sign=1 ORDER BY exp DESC LIMIT 1"
        else:
            sql = f"select * from user_xiuxian ORDER BY exp DESC LIMIT 1"
        cur.execute(sql)
        result = cur.fetchone()
        if not result:
            return None
        else:
            return UserInfo(*result)

    def get_last_user(self, only_active=False):
        """
        获取修为最后的用户
        """
        cur = self.connect.cursor()
        if only_active:
            sql = f"select * from user_xiuxian WHERE is_sign=1 ORDER BY exp LIMIT 1"
        else:
            sql = f"select * from user_xiuxian ORDER BY exp LIMIT 1"

        cur.execute(sql)
        result = cur.fetchone()
        if not result:
            return None
        else:
            return UserInfo(*result)

    def get_user_cd(self, user_id):
        """
        获取用户操作CD
        """
        sql = f"SELECT * FROM user_cd WHERE user_id=?"
        cur = self.connect.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchone()
        if result:
            return UserCd(*result)
        else:
            sql = f"INSERT INTO user_cd (user_id) VALUES (?)"
            cur.execute(sql, (user_id,))
            self.connect.commit()
            return None

    def add_money(self, user_id, price):
        """
        增加灵石
        """
        cur = self.connect.cursor()
        sql = f"UPDATE user_xiuxian SET stone=stone+? WHERE user_id=?"
        cur.execute(sql, (price, user_id))
        self.connect.commit()

    def set_sign_in(self, user_id, value):
        """
        设置签到
        """
        cur = self.connect.cursor()
        sql = f"UPDATE user_xiuxian SET is_sign=? WHERE user_id=?"
        cur.execute(sql, (value, user_id))
        self.connect.commit()

    def sub_money(self, user_id, price) -> bool:
        """
        减少灵石
        """
        user_info = self.get_user_info(user_id)

        cur = self.connect.cursor()
        sql = f"UPDATE user_xiuxian SET stone=stone-? WHERE user_id=?"
        cur.execute(sql, (price, user_id))
        self.connect.commit()
        return True

    def add_exp(self, user_id, exp: int):
        """
        增加修为
        """
        user_info = self.get_user_info(user_id)
        next_exp = rank.get_next_rank_exp(user_info.level)
        max_exp = next_exp * game_config.closing_exp_upper_limit
        if user_info.exp + exp > max_exp:
            sql = f"UPDATE user_xiuxian SET exp={max_exp} where user_id={user_id}"
            exp = 0
        else:
            sql = f"UPDATE user_xiuxian SET exp={user_info.exp + exp} where user_id={user_id}"
        cur = self.connect.cursor()
        cur.execute(sql)
        self.connect.commit()
        self.update_power(user_id)
        return exp

    def update_power(self, user_id) -> None:
        """
        更新战力
        """
        user_info = self.get_user_info(user_id)
        cur = self.connect.cursor()
        rank_speed = rank.get_rank_speed(user_info.level)
        root_speed = root.get_root_speed(user_info.root_type)
        sql = f"UPDATE user_xiuxian SET power=round(exp*?*?,0) WHERE user_id=?"
        cur.execute(sql, (root_speed, rank_speed, user_id))
        self.connect.commit()

    def update_user_attribute(self, user_id, hp, mp, atk):
        """
        更新用户HP,MP,ATK信息
        """
        sql = f"UPDATE user_xiuxian SET hp=?,mp=?,atk=? where user_id=?"
        cur = self.connect.cursor()
        cur.execute(sql, (hp, mp, atk, user_id))
        self.connect.commit()

    def set_user_state(self, user_id, the_type, sc_time=None):
        """
        更新用户状态
        :param sc_time: 任务
        :param user_id: qq
        :param the_type: 0:无状态  1:闭关中  2:历练中  3:探索秘境中
        :return:
        """
        if the_type == 0:
            now_time = 0
        else:
            now_time = datetime.datetime.now()

        sql = f"UPDATE user_cd SET type=?,create_time=?,scheduled_time=? where user_id=?"
        cur = self.connect.cursor()
        cur.execute(sql, (the_type, now_time, sc_time, user_id))
        self.connect.commit()

    def insert_backpack(self, user_id, goods_id, goods_name, goods_type, goods_num, bind_flag=0):
        """
        插入物品至背包
        :param user_id: 用户qq
        :param goods_id: 物品id
        :param goods_name: 物品名称
        :param goods_type: 物品类型
        :param goods_num: 物品数量
        :param bind_flag: 是否绑定物品,0-非绑定,1-绑定
        :return: None
        """
        now_time = datetime.datetime.now()
        # 检查物品是否存在，存在则 update
        cur = self.connect.cursor()
        back = self.get_user_goods_by_id(user_id, goods_id)
        if back:
            # 判断是否存在，存在则 update
            if bind_flag == 1:
                bind_num = back.bind_num + goods_num
            else:
                bind_num = back.bind_num
            goods_nums = back.goods_num + goods_num
            sql = f"UPDATE back set goods_num=?,update_time=?,bind_num={bind_num} WHERE user_id=? and goods_id=?"
            cur.execute(sql, (goods_nums, now_time, user_id, goods_id))
            self.connect.commit()
        else:
            # 判断是否存在，不存在则 INSERT
            if bind_flag == 1:
                bind_num = goods_num
            else:
                bind_num = 0
            sql = "INSERT INTO back (user_id, goods_id, goods_name, goods_type, goods_num, create_time, update_time, bind_num) VALUES (?,?,?,?,?,?,?,?)"
            cur.execute(sql, (user_id, goods_id, goods_name, goods_type, goods_num, now_time, now_time, bind_num))
            self.connect.commit()

    def get_user_goods_by_id(self, user_id, goods_id):
        """
        根据物品id、用户id获取物品信息
        """
        sql = f"select * from back where user_id=? and goods_id=?"
        cur = self.connect.cursor()
        cur.execute(sql, (user_id, goods_id))
        result = cur.fetchone()
        if not result:
            return None
        else:
            return GoodsInfo(*result)

    def get_backpack_list(self, user_id):
        """
        获取用户背包信息
        """
        sql = f"SELECT * FROM back where user_id=? and goods_num >= 1"
        cur = self.connect.cursor()
        cur.execute(sql, (user_id,))
        result = cur.fetchall()
        results = []
        if not result:
            results = None
        for r in result:
            results.append(GoodsInfo(*r))
        return results

    def delete_backpack(self, user_id, goods_id, num=1):
        """
        使用物品
        :num 减少数量  默认1
        :use_key 是否使用，丹药使用才传 默认0
        """
        # TODO:to check num
        now_time = datetime.datetime.now()
        sql_str = f"UPDATE back set update_time='{now_time}',action_time='{now_time}',goods_num=goods_num-{num} WHERE user_id={user_id} and goods_id={goods_id}"
        cur = self.connect.cursor()
        cur.execute(sql_str)
        self.connect.commit()
