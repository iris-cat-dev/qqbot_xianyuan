from ...common.bot.depends import Player, PlayerPosition
from ...common.bot.matcher import full_match

walk_n = full_match("向北走", "")
walk_s = full_match("向南走", "")
walk_w = full_match("向西走", "")
walk_e = full_match("向东走", "")


@walk_n.handle()
async def walk_n_(player: Player, position: PlayerPosition):
    msg = position.move("n")
    await walk_n.finish(msg)


@walk_s.handle()
async def walk_s_(player: Player, position: PlayerPosition):
    msg = position.move("s")
    await walk_n.finish(msg)


@walk_w.handle()
async def walk_w_(player: Player, position: PlayerPosition):
    msg = position.move("w")
    await walk_n.finish(msg)


@walk_e.handle()
async def walk_e_(player: Player, position: PlayerPosition):
    msg = position.move("e")
    await walk_n.finish(msg)
