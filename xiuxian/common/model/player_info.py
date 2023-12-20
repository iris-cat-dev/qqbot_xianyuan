from peewee import *

# 连接数据库
db = SqliteDatabase('players.db')

# 定义游戏玩家信息表模型
class Player(Model):
    name = CharField()
    level = IntegerField()
    score = IntegerField()
    created_at = TimestampField()

    class Meta:
        database = db

# 创建游戏玩家信息表
db.create_tables([Player])