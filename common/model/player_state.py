from enum import Enum

from peewee import *

from . import db


class TBPlayerState(Model):
    uid = CharField(50)
    state = CharField(10, default="发呆中")
    position = CharField(20, default="新手村广场")
    update_at = TimestampField()

    class Meta:
        database = db


db.create_tables([TBPlayerState])
