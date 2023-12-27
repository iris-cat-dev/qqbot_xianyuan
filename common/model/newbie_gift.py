from peewee import *

from . import db


class NewbieGift(Model):
    uid = CharField(50)
    times = IntegerField(default=0)
    update_at = TimestampField()

    class Meta:
        database = db


db.create_tables([NewbieGift])
