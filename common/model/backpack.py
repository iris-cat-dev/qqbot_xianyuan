from peewee import *

from . import db


class Backpack(Model):
    uid = CharField(50)
    item_id = IntegerField()
    count = IntegerField()
    is_bind = BooleanField()

    class Meta:
        database = db


db.create_tables([Backpack])
