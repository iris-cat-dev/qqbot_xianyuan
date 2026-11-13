'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data, items, stats, dayKey, MINUTE, playerRank } = require('../src/rules');
const encounters = require('../data/encounter-data.json');

const DAY = 24 * 60 * MINUTE;
const BOSS_INTERVAL = encounters.boss.intervalMinutes * MINUTE;

function boundary(now) { return Math.floor((now - 6 * 60 * MINUTE) / DAY) * DAY + 6 * 60 * MINUTE; }

function roll(weights, key) {
  let before = 0;
  const total = Object.values(weights).reduce((sum, weight) => sum + weight, 0);
  for (const [name, weight] of Object.entries(weights)) {
    if (name === key) return (before + weight / 2) / total;
    before += weight;
  }
  throw new Error(`Missing test distribution member: ${key}`);
}

// Fixtures retain the real registration state and alter only already-achievable player/world state.
// A separate connection observes committed state; rejected commands must roll back both records.
function session(t, start = '2026-11-13T01:00:00Z') {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-encounters-'));
  const databasePath = join(directory, 'game.sqlite');
  let now = Date.parse(start);
  let values = [];
  let fallback = 0.5;
  const game = createGame({ databasePath, now: () => now, random: () => values.length ? values.shift() : fallback });
  t.after(() => { game.close(); rmSync(directory, { recursive: true, force: true }); });
  function withStore(action) {
    const store = openStore(databasePath);
    try { return action(store); } finally { store.close(); }
  }
  const s = {
    run(text, userId = 'a', groupId = 'group', targetId) {
      return game.handleCommand({ text, userId, groupId, targetId, nickname: userId });
    },
    answer(text, userId = 'a', groupId = 'group') {
      return game.handleCommand({ text, userId, groupId, nickname: userId, answer: true });
    },
    resolve(request, review, userId = 'a', groupId = 'group') {
      return game.resolveReview({
        groupId, userId, kind: request.kind, requestId: request.requestId,
        revision: request.revision, review
      });
    },
    player(userId = 'a', groupId = 'group') { return game.getPlayer(groupId, userId); },
    world(groupId = 'group') { return withStore(store => store.getWorld(groupId)); },
    patchPlayer(change, userId = 'a', groupId = 'group') {
      return withStore(store => {
        const player = store.get(groupId, userId);
        change(player);
        store.save(groupId, player);
        return player;
      });
    },
    patchWorld(change, groupId = 'group') {
      return withStore(store => {
        const world = store.getWorld(groupId);
        change(world);
        store.saveWorld(groupId, world);
        return world;
      });
    },
    random(next, defaultValue = 0.5) { values = [...next]; fallback = defaultValue; },
    advance(milliseconds) { now += milliseconds; },
    setTime(value) { now = Date.parse(value); },
    now() { return now; }
  };
  s.run('我要修仙');
  s.patchWorld(world => {
    world.rift = { name: '东玄域', ...encounters.rifts.东玄域 };
    world.riftGeneratedAt = boundary(now);
    world.bossGeneratedAt = Math.floor(now / BOSS_INTERVAL) * BOSS_INTERVAL;
  });
  return s;
}

function realm(s, index, userId = 'a', equipment = {}) {
  return s.patchPlayer(player => {
    player.realm = index;
    player.exp = data.realms[index].exp;
    player.equipment = { weapon: null, armor: null, technique: null, skill: null, ...equipment };
    for (const id of Object.values(equipment)) if (id) player.inventory[id] = 1;
    const attributes = stats(player);
    player.hp = attributes.maxHp;
    player.mp = attributes.maxMp;
  }, userId);
}

function boss(index, overrides = {}) {
  const exp = data.realms[index].exp;
  const maxHp = Math.floor(exp * encounters.boss.multipliers.hp);
  return {
    name: encounters.boss.names[0], realm: index, hp: maxHp, maxHp,
    mp: Math.floor(exp * encounters.boss.multipliers.mp),
    attack: Math.floor(exp * encounters.boss.multipliers.attack),
    money: Math.floor(exp * encounters.boss.multipliers.money), ...overrides
  };
}

function unchanged(s, action, userIds = ['a']) {
  const players = userIds.map(id => s.player(id));
  const world = s.world();
  action();
  assert.deepEqual(userIds.map(id => s.player(id)), players);
  assert.deepEqual(s.world(), world);
}

function enter(s) {
  const count = s.world().rift.count;
  s.run('秘境探索');
  const activity = s.player().activity;
  assert.equal(activity.kind, 'rift');
  assert.equal(s.world().rift.count, count - 1);
  s.advance(activity.rift.time * MINUTE);
  return activity.rift;
}

function settle(s, values) {
  enter(s);
  const before = s.player();
  s.random(values);
  const result = s.run('秘境结算');
  assert.equal(result.handled, true);
  assert.equal(s.player().activity, null);
  return { before, after: s.player(), result };
}
function riftResources(player) {
  const { realm, exp, money, hp, mp, inventory, equipment } = player;
  return { realm, exp, money, hp, mp, inventory, equipment };
}

function riftDecision(outcome = 'success', narrative = '你稳住身形，借地势化开了眼前危机。') {
  return { outcome, reason: '行动回应了当前场景的主要危险。', narrative };
}


test('切磋使用本群稳定身份，目标缺失、自身、跨群和非法ID拒绝且原子不变', t => {
  const s = session(t);
  s.run('我要修仙', 'b');
  s.run('我要修仙', 'outsider', 'other');
  for (const targetId of [undefined, 'a', 'missing', 'outsider']) {
    unchanged(s, () => s.run('切磋 @相同昵称', 'a', 'group', targetId), ['a', 'b']);
  }
  for (const targetId of ['', ' ', 17]) {
    unchanged(s, () => assert.throws(() => s.run('切磋', 'a', 'group', targetId), TypeError), ['a', 'b']);
  }
  assert.equal(s.player('outsider'), null);
  const absent = s.world('missing-group');
  s.run('切磋', 'new', 'missing-group', 'b');
  assert.equal(s.player('new', 'missing-group'), null);
  assert.deepEqual(s.world('missing-group'), absent);
});

test('切磋不写回双方战斗资源或奖励，冷却59999毫秒拒绝而60000毫秒允许', t => {
  const s = session(t);
  s.run('我要修仙', 'b');
  realm(s, 3, 'a', { skill: '8001' });
  realm(s, 3, 'b');
  const original = s.player();
  const target = s.player('b');
  s.run('切磋 @b', 'a', 'group', 'b');
  assert.deepEqual(s.player(), { ...original, lastDuelAt: s.now() });
  assert.deepEqual(s.player('b'), target);
  s.advance(MINUTE - 1);
  unchanged(s, () => s.run('切磋', 'a', 'group', 'b'), ['a', 'b']);
  s.advance(1);
  s.run('切磋', 'a', 'group', 'b');
  assert.equal(s.player().lastDuelAt, s.now());
  assert.deepEqual(s.player('b'), target);
});

test('14点前新群补昨日秘境，14点精确刷新且进行中的探索使用旧快照', t => {
  const s = session(t, '2026-11-13T05:59:59.999Z');
  s.patchWorld(world => { world.rift = null; world.riftGeneratedAt = null; });
  s.random([], 0);
  s.run('秘境查询');
  assert.equal(s.world().riftGeneratedAt, Date.parse('2026-11-12T06:00:00Z'));
  assert.equal(s.world().rift.name, '东玄域');
  const count = s.world().rift.count;
  s.run('秘境探索');
  const activity = s.player().activity;
  s.advance(1);
  s.random([], 0.999999);
  s.run('秘境查询');
  assert.equal(s.world().riftGeneratedAt, Date.parse('2026-11-13T06:00:00Z'));
  assert.equal(s.world().rift.name, '黑水湖');
  assert.equal(s.world().rift.count, encounters.rifts.黑水湖.count);
  assert.deepEqual(s.player().activity, activity);
  s.advance(activity.rift.time * MINUTE - 1);
  s.random([roll(encounters.rift.eventWeights, 'nothing')]);
  const before = s.player();
  s.run('秘境结算');
  assert.equal(s.player().money, before.money + 50000);
  assert.equal(s.player().activity, null);
  assert.equal(s.world().rift.count, encounters.rifts.黑水湖.count);
  assert.equal(count, encounters.rifts.东玄域.count);
});

test('秘境共享次数全群扣减，重复探索、未到期和耗尽拒绝；终止不返次不奖励', t => {
  const s = session(t);
  s.run('我要修仙', 'b');
  s.patchWorld(world => { world.rift.count = 1; });
  unchanged(s, () => s.run('秘境结算'));
  unchanged(s, () => s.run('秘境探索终止'));
  s.run('秘境探索');
  assert.equal(s.world().rift.count, 0);
  unchanged(s, () => s.run('秘境探索'));
  unchanged(s, () => s.run('秘境探索', 'b'), ['a', 'b']);
  s.advance(60 * MINUTE - 1);
  unchanged(s, () => s.run('秘境结算'));
  const before = riftResources(s.player());
  s.run('秘境探索终止');
  assert.deepEqual(riftResources(s.player()), before);
  assert.equal(s.player().activity, null);
  assert.equal(s.player().riftAdventure.status, 'cancelled');
  assert.equal(s.world().rift.count, 0);
  unchanged(s, () => s.run('秘境探索终止'));
  unchanged(s, () => s.run('秘境结算'));
});

test('无事事件只奖励固定灵石并只能结算一次；同一玩家可以再次进入', t => {
  const s = session(t);
  const { before, after } = settle(s, [roll(encounters.rift.eventWeights, 'nothing')]);
  assert.deepEqual(riftResources(after), { ...riftResources(before), money: before.money + 50000 });
  unchanged(s, () => s.run('秘境结算'));
  s.run('秘境探索');
  assert.equal(s.player().activity.kind, 'rift');
  assert.equal(s.world().rift.count, 28);
});

test('宝藏灵石使用进入时rank，随机金额两端均实际入账', t => {
  const s = session(t);
  for (const [random, extra] of [[0, 1], [0.999999, 10]]) {
    const snapshot = enter(s);
    const before = s.player();
    s.random([roll(encounters.rift.eventWeights, 'treasure'), roll(encounters.rift.treasureWeights, 'money'), random]);
    s.run('秘境结算');
    assert.equal(s.player().money - before.money, (snapshot.rank + extra) * 100000);
    assert.deepEqual(s.player().inventory, before.inventory);
    assert.equal(s.player().activity, null);
  }
});

for (const kind of ['technique', 'skill', 'weapon', 'armor']) {
  test(`秘境${kind}掉落真实合法物品且遵守rank窗口`, t => {
    const s = session(t);
    realm(s, 3);
    const { before, after } = settle(s, [
      roll(encounters.rift.eventWeights, 'treasure'), roll(encounters.rift.treasureWeights, kind), 0, 0
    ]);
    const gains = Object.entries(after.inventory).filter(([id, count]) => count > (before.inventory[id] ?? 0));
    assert.equal(gains.length, 1);
    const [id, count] = gains[0];
    const item = items.get(id);
    assert.equal(item.kind, kind);
    assert.equal(count, (before.inventory[id] ?? 0) + 1);
    const rank = playerRank(before) - (kind === 'weapon' || kind === 'armor' ? before.activity.rift.rank : 0);
    assert.ok(Number(item.rank) - rank >= 0);
    assert.ok(Number(item.rank) - rank <= (kind === 'weapon' || kind === 'armor' ? 30 : 6));
    assert.equal(after.money, before.money);
    assert.equal(after.exp, before.exp);
  });
}

for (const kind of ['technique', 'skill', 'armor']) {
  test(`秘境${kind}空rank窗口不会凭空造物或扣钱`, t => {
    const s = session(t);
    if (kind === 'armor') {
      realm(s, data.realms.length - 1);
      s.patchWorld(world => { world.rift = { name: '黑水湖', ...encounters.rifts.黑水湖 }; });
    }
    const { before, after } = settle(s, [roll(encounters.rift.eventWeights, 'treasure'), roll(encounters.rift.treasureWeights, kind)]);
    assert.deepEqual(riftResources(after), riftResources(before));
  });
}

for (const kind of ['technique', 'skill']) {
  test(`秘境${kind}争夺概率上界成功，超出上界失败只获得补偿`, t => {
    const s = session(t);
    realm(s, 3);
    const threshold = 65;
    const success = settle(s, [roll(encounters.rift.eventWeights, 'treasure'), roll(encounters.rift.treasureWeights, kind), 0, (threshold + 0.5) / 101]);
    assert.equal(Object.values(success.after.inventory).reduce((sum, count) => sum + count, 0), 1);
    const { before, after } = settle(s, [roll(encounters.rift.eventWeights, 'treasure'), roll(encounters.rift.treasureWeights, kind), 0, (threshold + 1.5) / 101]);
    assert.deepEqual(after.inventory, before.inventory);
    assert.equal(after.money, before.money + 50000);
    assert.equal(after.exp, before.exp);
  });
}

for (const kind of ['exp', 'hp', 'money']) {
  test(`秘境${kind}损失真正扣除对应资源而非错误扣血，并获得补偿`, t => {
    const s = session(t);
    realm(s, 3);
    s.patchPlayer(player => { player.money = 2000000; });
    const { before, after } = settle(s, [
      roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'loss'),
      roll(encounters.rift.lossWeights, kind), 0
    ]);
    const expected = { ...riftResources(before), money: before.money + 50000 };
    if (kind === 'exp') { expected.exp -= 90; expected.hp = Math.min(expected.hp - 45, expected.exp); expected.mp -= 90; }
    if (kind === 'hp') expected.hp -= 450;
    if (kind === 'money') expected.money -= 500000;
    assert.deepEqual(riftResources(after), expected);
  });
}

test('秘境金钱损失不透支，气血真元损失最低保留1且最高损失值生效', t => {
  const s = session(t);
  realm(s, 3);
  s.patchPlayer(player => { player.money = 250; });
  const money = settle(s, [roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'loss'), roll(encounters.rift.lossWeights, 'money'), 0.999999]);
  assert.equal(money.after.money, 50000);
  assert.equal(money.after.hp, money.before.hp);
  s.patchPlayer(player => { player.hp = 1; player.mp = 1; });
  const exp = settle(s, [roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'loss'), roll(encounters.rift.lossWeights, 'exp'), 0.999999]);
  assert.equal(exp.after.exp, exp.before.exp - 150);
  assert.equal(exp.after.hp, 1);
  assert.equal(exp.after.mp, 1);
  const hp = settle(s, [roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'loss'), roll(encounters.rift.lossWeights, 'hp'), 0.999999]);
  assert.equal(hp.after.hp, 1);
});

test('秘境妖兽胜利写回真实技能消耗并奖励修为灵石，低境界奖金不为负', t => {
  const s = session(t);
  realm(s, 33, 'a', { technique: '9801', weapon: '7093', armor: '6091', skill: '8907' });
  const { before, after } = settle(s, [
    roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'boss'),
    0, 0, 0, 0.5, 0.5, 0.5, 0
  ]);
  assert.equal(after.exp, before.exp + Math.floor(before.exp * 0.01));
  assert.equal(after.hp, before.hp - Math.floor(before.hp * 0.1));
  assert.equal(after.mp, before.mp - Math.floor(before.exp * 0.4));
  assert.equal(after.money, before.money + (1 + 50 - playerRank(before)) * 200000);
  assert.deepEqual(after.inventory, before.inventory);
  const low = session(t);
  realm(low, 3, 'a', { technique: '9001', skill: '8001' });
  const won = settle(low, [roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'boss'), 0, 0, 0]);
  assert.ok(won.after.exp > won.before.exp);
  assert.equal(won.after.money, won.before.money);
});

test('秘境战败最低保留1气血且无修为奖励，零攻击长战平局也正常退出', t => {
  const s = session(t);
  const lost = settle(s, [roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'boss'), 0, 0, 0]);
  assert.equal(lost.after.hp, 1);
  assert.equal(lost.after.mp, lost.before.mp);
  assert.equal(lost.after.exp, lost.before.exp);
  assert.equal(lost.after.money, lost.before.money + 50000);
  const draw = session(t);
  draw.patchPlayer(player => { player.exp = 1; player.hp = 1; player.mp = 0; });
  const tied = settle(draw, [roll(encounters.rift.eventWeights, 'battle'), roll(encounters.rift.battleWeights, 'boss'), 0, 0, 0]);
  assert.deepEqual(riftResources(tied.after), { ...riftResources(tied.before), money: tied.before.money + 50000 });
});

test('邪魔没有当日签到活跃者不生成，同批次签到不追溯生成，下一30分钟才出现', t => {
  const s = session(t);
  s.patchWorld(world => { world.bossGeneratedAt = null; });
  s.run('邪魔查询');
  assert.deepEqual(s.world().bosses, []);
  assert.equal(s.world().bossGeneratedAt, s.now());
  s.run('修仙签到');
  s.run('邪魔查询');
  assert.deepEqual(s.world().bosses, []);
  s.advance(BOSS_INTERVAL - 1);
  s.run('邪魔查询');
  assert.equal(s.world().bosses.length, 0);
  s.advance(1);
  s.run('邪魔查询');
  const generated = s.world().bosses;
  assert.equal(generated.length, 1);
  assert.equal(generated[0].realm, 0);
  assert.equal(generated[0].maxHp, 5000);
  assert.equal(generated[0].money, 25);
});

test('邪魔补批次优先最低实际境界和未覆盖大境界中期，并能覆盖最高境界', t => {
  const s = session(t);
  s.run('我要修仙', 'b');
  s.run('我要修仙', 'c');
  for (const [id, index] of [['a', 1], ['b', 4], ['c', data.realms.length - 1]]) {
    realm(s, index, id);
    s.patchPlayer(player => { player.signDate = dayKey(s.now()); }, id);
  }
  s.advance(3 * BOSS_INTERVAL);
  s.run('邪魔查询');
  assert.deepEqual(s.world().bosses.map(value => value.realm), [1, 5, data.realms.length - 1]);
  const first = s.world().bosses[0];
  assert.equal(first.maxHp, data.realms[1].exp * 50);
  assert.equal(first.attack, data.realms[1].exp * 0.2);
  assert.equal(first.mp, data.realms[1].exp * 20);
  s.advance(BOSS_INTERVAL);
  s.random([], 0.999999);
  s.run('邪魔查询');
  assert.equal(s.world().bosses[3].realm, data.realms.length - 1);
});

test('补批次从已覆盖最低境界取中期，生成上限10并且未刷新批次不重复生成', t => {
  const s = session(t);
  realm(s, 1);
  s.patchPlayer(player => { player.signDate = dayKey(s.now()); });
  s.advance(20 * BOSS_INTERVAL);
  s.run('邪魔查询');
  assert.equal(s.world().bosses.length, 10);
  assert.deepEqual(s.world().bosses.map(value => value.realm), [1, ...Array(9).fill(2)]);
  const full = s.world();
  s.run('邪魔查询');
  assert.deepEqual(s.world(), full);
  s.advance(BOSS_INTERVAL);
  s.run('邪魔查询');
  assert.equal(s.world().bosses.length, 10);
  assert.equal(s.world().bossGeneratedAt, s.now());
  assert.deepEqual(s.world().bosses, full.bosses);
});

test('已覆盖江湖境也能补批次，昨日签到不计作今日活跃者', t => {
  const s = session(t);
  s.patchPlayer(player => { player.signDate = dayKey(s.now()); });
  s.advance(2 * BOSS_INTERVAL);
  s.run('邪魔查询');
  assert.deepEqual(s.world().bosses.map(value => value.realm), [0, 0]);
  s.setTime('2026-11-14T01:00:00Z');
  s.run('邪魔查询');
  assert.equal(s.world().bosses.length, 2);
});

test('邪魔无效格式、非法编号和重伤均不扣资源、不改Boss或积分', t => {
  const s = session(t);
  s.patchWorld(world => { world.bosses = [boss(0)]; });
  for (const text of ['讨伐邪魔', '讨伐邪魔x', '讨伐邪魔0', '讨伐邪魔-1', '讨伐邪魔1.5', '讨伐邪魔9007199254740992', '讨伐邪魔2']) {
    unchanged(s, () => s.run(text));
  }
  s.patchPlayer(player => { player.hp = player.exp / 10; });
  unchanged(s, () => s.run('讨伐邪魔 1'));
});

test('邪魔战败保留持续气血和剩余赏金，另一玩家继续真实扣血与按实际伤害分奖', t => {
  const s = session(t);
  s.run('我要修仙', 'b');
  realm(s, 3);
  realm(s, 3, 'b');
  s.patchWorld(world => { world.bosses = [boss(3)]; });
  s.run('讨伐邪魔1');
  const a = s.player();
  assert.equal(a.hp, 1);
  assert.equal(a.exp, 3001);
  assert.equal(a.money, 7);
  assert.equal(a.bossPoints, 2);
  assert.deepEqual(a.inventory, {});
  assert.equal(s.world().bosses[0].hp, 148500);
  assert.equal(s.world().bosses[0].money, 743);
  s.run('讨伐邪魔 1', 'b');
  assert.equal(s.world().bosses[0].hp, 147000);
  assert.equal(s.world().bosses[0].money, 736);
  assert.equal(s.player('b').money, 7);
  assert.equal(s.player('b').bossPoints, 2);
  assert.equal(a.money + s.player('b').money + s.world().bosses[0].money, 750);
  s.patchPlayer(player => { player.hp = stats(player).maxHp; });
  s.patchWorld(world => { world.bosses[0].hp = 300; });
  const before = s.player();
  s.run('讨伐邪魔1');
  assert.equal(s.world().bosses.length, 0);
  assert.equal(s.player().money, before.money + 736);
  assert.equal(s.player().exp, before.exp + 184);
  assert.equal(s.player().hp, before.hp);
  assert.equal(s.player().bossPoints, before.bossPoints + 2);
  assert.equal(s.player().inventory['1105'], 1);
});

test('高境界讨伐临时按玩家境界缩放，战后还原原Boss尺度与剩余比例而不永久改攻击', t => {
  const s = session(t);
  realm(s, 4);
  const original = boss(1, { hp: 25000 });
  s.patchWorld(world => { world.bosses = [original]; });
  const before = s.player();
  s.run('讨伐邪魔1');
  assert.deepEqual(s.world().bosses[0], { ...original, hp: 24500, money: 245 });
  assert.equal(s.player().hp, 1);
  assert.equal(s.player().money, before.money + 5);
  assert.equal(s.player().exp, before.exp + 1);
  assert.equal(s.player().bossPoints, before.bossPoints + 2);
  s.patchPlayer(player => { player.hp = stats(player).maxHp; });
  s.patchWorld(world => { world.bosses[0].hp = 1; });
  const reward = s.player();
  s.run('讨伐邪魔1');
  assert.equal(s.world().bosses.length, 0);
  assert.equal(s.player().money, reward.money + 245);
  assert.equal(s.player().inventory['1105'], 1);
});

for (const index of [0, 40, data.realms.length - 1]) {
  test(`邪魔境界${index}正确使用低阶或高阶减伤和真实奖励尺度`, t => {
    const s = session(t);
    realm(s, index);
    const original = boss(index);
    s.patchWorld(world => { world.bosses = [original]; });
    const before = s.player();
    const rounds = Math.ceil(before.hp / original.attack);
    const raw = Math.floor(before.exp / 10);
    const damage = Math.floor(raw * (index === 0 ? 1 : 0.65)) * rounds;
    const money = Math.floor(original.money * damage / original.hp);
    s.run('讨伐邪魔1');
    assert.equal(s.world().bosses[0].hp, original.hp - damage);
    assert.equal(s.world().bosses[0].money, original.money - money);
    assert.equal(s.player().money, before.money + money);
    assert.equal(s.player().exp, before.exp + Math.floor(money / 4));
    assert.equal(s.player().hp, 1);
    assert.equal(s.player().bossPoints, Math.max(2, Math.floor(damage / original.maxHp * (30 + 2 * index))));
  });
}

test('完整高阶邪魔击杀奖励实际伤害积分、全部赏金、修为和真实丹药，可立即兑换商品1', t => {
  const s = session(t);
  realm(s, 40);
  s.patchPlayer(player => {
    player.pillTotals['2017'] = 250000;
    player.attackBonus = items.get('2017').buff * player.pillTotals['2017'];
  });
  const original = boss(40);
  s.patchWorld(world => { world.bosses = [original]; });
  const before = s.player();
  s.run('讨伐邪魔1');
  const killed = s.player();
  assert.equal(s.world().bosses.length, 0);
  assert.equal(killed.hp, before.hp);
  assert.equal(killed.mp, before.mp);
  assert.equal(killed.money, before.money + original.money);
  assert.equal(killed.exp, before.exp + Math.floor(original.money / 4));
  assert.equal(killed.bossPoints, 110);
  assert.equal(killed.inventory['1105'], 1);
  s.run('积分兑换1');
  assert.equal(s.player().bossPoints, 10);
  assert.equal(s.player().inventory['1999'], 1);
  assert.equal(s.player().inventory['1105'], 1);
  assert.equal(s.player().money, killed.money);
});

test('积分查询不消耗，唯一商品兑换精确余额且不足或其他商品原子拒绝', t => {
  const s = session(t);
  for (const text of ['我的积分', '积分查询', '积分兑换1', '积分兑换', '积分兑换2', '积分兑换x', '积分兑换1.0']) {
    unchanged(s, () => s.run(text));
  }
  s.patchPlayer(player => { player.bossPoints = 99; });
  unchanged(s, () => s.run('积分兑换1'));
  s.patchPlayer(player => { player.bossPoints = 200; });
  const before = s.player();
  s.run('积分兑换 1');
  assert.deepEqual(s.player(), { ...before, bossPoints: 100, inventory: { ...before.inventory, '1999': 1 } });
  s.run('积分兑换1');
  assert.equal(s.player().bossPoints, 0);
  assert.equal(s.player().inventory['1999'], 2);
  unchanged(s, () => s.run('积分兑换1'));
});

test('秘境三幕立即开放自由行动，严格判定且累计五分由引擎发放宝藏', t => {
  const s = session(t);
  const count = s.world().rift.count;
  const entered = s.run('秘境探索');
  assert.match(entered.message, /第1\/3幕/u);
  assert.equal(s.world().rift.count, count - 1);
  assert.equal(s.player().riftAdventure.status, 'awaiting');
  assert.equal(s.player().activity.kind, 'rift');

  const resources = riftResources(s.player());
  const first = s.answer('贴着石壁观察符纹，再用碎石试探雾中脚步。');
  assert.equal(first.reviewRequest.kind, 'rift');
  assert.equal(JSON.parse(first.reviewRequest.prompt).action, '贴着石壁观察符纹，再用碎石试探雾中脚步。');
  assert.deepEqual(riftResources(s.player()), resources);
  assert.equal(s.player().riftAdventure.status, 'judging');

  const invalid = s.resolve(first.reviewRequest, { ...riftDecision(), money: 999999 });
  assert.equal(invalid.error, 'invalid_review');
  assert.deepEqual(riftResources(s.player()), resources);
  assert.equal(s.player().riftAdventure.status, 'judging');
  assert.match(s.resolve(first.reviewRequest, riftDecision()).message, /第2\/3幕/u);

  const second = s.answer('绕开拖痕，先切断残阵最暗的阵纹。');
  assert.match(s.resolve(second.reviewRequest, riftDecision()).message, /第3\/3幕/u);
  const third = s.answer('借崩裂石柱遮蔽，牵制灵影后触碰宝光。');
  s.random([roll(encounters.rift.treasureWeights, 'money'), 0]);
  const settled = s.resolve(third.reviewRequest, riftDecision('mixed'));
  assert.match(settled.message, /三幕评价5\/6/u);
  assert.match(settled.message, /互动探索结算/u);
  assert.equal(s.player().activity, null);
  assert.equal(s.player().riftAdventure.status, 'settled');
  assert.equal(s.player().riftAdventure.score, 5);
  assert.equal(s.player().journey.at(-1).event, 'agent_treasure');
  assert.ok(s.player().money > resources.money);
  const after = s.player();
  assert.deepEqual(s.resolve(third.reviewRequest, riftDecision('mixed')), settled);
  assert.deepEqual(s.player(), after);
});

test('秘境连续失利走固定损失档，终止后迟到判定不能结算', t => {
  const s = session(t);
  s.run('秘境探索');
  for (let round = 0; round < 3; round++) {
    const request = s.answer(`第${round + 1}幕直接冲过去`).reviewRequest;
    if (round === 2) s.random([roll(encounters.rift.lossWeights, 'money'), 0]);
    s.resolve(request, riftDecision('failure', '你正面撞上禁制，被迫狼狈退开。'));
  }
  assert.equal(s.player().riftAdventure.score, 0);
  assert.equal(s.player().journey.at(-1).event, 'agent_loss');
  assert.equal(s.player().activity, null);

  s.run('秘境探索');
  const pending = s.answer('先观察').reviewRequest;
  const before = s.player();
  s.run('秘境探索终止');
  const cancelled = s.player();
  assert.notDeepEqual(cancelled, before);
  assert.match(s.resolve(pending, riftDecision()).message, /已终止/u);
  assert.deepEqual(s.player(), cancelled);
});
