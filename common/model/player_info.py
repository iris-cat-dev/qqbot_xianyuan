from peewee import *

from . import db


# 定义游戏玩家信息表模型
class PlayerInfo(Model):
    uid = CharField()
    name = CharField()
    root = CharField()
    level = CharField()
    exp = IntegerField()
    hp = IntegerField()
    mp = IntegerField()
    attack = IntegerField()
    defense = IntegerField()
    money = IntegerField()
    created_at = TimestampField()

    class Meta:
        database = db


# 创建游戏玩家信息表
db.create_tables([PlayerInfo])
