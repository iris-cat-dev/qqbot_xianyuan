from ...common.bot.depends import Player
from ...common.bot.matcher import full_match

walk_n = full_match("向北走", "")
walk_s = full_match("向南走", "")
walk_w = full_match("向东走", "")
walk_e = full_match("向西走", "")


@walk_n.handle()
async def walk_n_(player: Player):
    await walk_n.finish("你来到铁匠铺")


@walk_s.handle()
async def walk_s_(player: Player):
    await walk_s.finish("你来到铁匠铺")


@walk_w.handle()
async def walk_w_(player: Player):
    await walk_w.finish("你来到铁匠铺")


@walk_e.handle()
async def walk_e_(player: Player):
    await walk_e.finish("你来到铁匠铺")
