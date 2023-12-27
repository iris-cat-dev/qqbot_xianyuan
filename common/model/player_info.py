from peewee import *

from . import db

class PlayerInfo(Model):
    uid = CharField(50)
    name = CharField(20)
    root = CharField(10)
    level = CharField(10)
    exp = IntegerField()
    hp = IntegerField(default=1)
    mp = IntegerField(default=1)
    attack = IntegerField(default=1)
    defense = IntegerField(default=1)
    money = IntegerField()
    created_at = TimestampField()

    class Meta:
        database = db


db.create_tables([PlayerInfo])
