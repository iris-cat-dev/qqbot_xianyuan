'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data } = require('../src/rules');

const MAX = Number.MAX_SAFE_INTEGER;

function session(t) {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-inventory-'));
  const databasePath = join(directory, 'game.sqlite');
  let now = Date.parse('2026-11-13T01:00:00Z');
  const game = createGame({ databasePath, now: () => now, random: () => 0 });
  const store = openStore(databasePath);
  t.after(() => {
    store.close();
    game.close();
    rmSync(directory, { recursive: true, force: true });
  });
  const s = {
    run(text, userId = 'a', targetId, groupId = 'group') {
      return game.handleCommand({ text, userId, groupId, nickname: userId, targetId });
    },
    player(userId = 'a', groupId = 'group') { return game.getPlayer(groupId, userId); },
    world() { return store.getWorld('group'); },
    snapshot() { return { players: store.list('group'), world: s.world() }; },
    register(userId = 'a', groupId = 'group') { s.run('我要修仙', userId, undefined, groupId); },
    patch(change, userId = 'a') {
      const player = s.player(userId);
      change(player);
      store.save('group', player);
      return player;
    },
    reach(rank, userId = 'a') {
      return s.patch(player => {
        player.realm = 56 - rank;
        player.exp = data.realms[player.realm].exp;
        player.hp = player.exp;
        player.mp = Math.floor(player.exp / 2);
      }, userId);
    },
    patchWorld(change) {
      const world = s.world();
      change(world);
      store.saveWorld('group', world);
    },
    reject(text, userId = 'a', targetId) {
      const before = s.snapshot();
      assert.equal(s.run(text, userId, targetId).handled, true);
      assert.deepEqual(s.snapshot(), before, text);
    },
    setTime(value) { now = Date.parse(value); }
  };
  s.register();
  return s;
}

function bagRows(message) {
  return [...message.matchAll(/^.*\[(\d+)\] ×(\d+)(.*)$/gmu)].map(match => ({
    id: match[1], count: Number(match[2]), equipped: match[3].includes('已装备')
  }));
}

function listingRows(message) {
  return [...message.matchAll(/^(\d+)\. .*\[(\d+)\] ×(\d+) · 整批(\d+)灵石 · .*（([^）]+)）$/gmu)].map(match => ({
    id: Number(match[1]), itemId: match[2], count: Number(match[3]),
    price: Number(match[4]), sellerId: match[5]
  }));
}

test('背包查询显示数量和装备占用，装备切换与卸下不消耗物品', t => {
  const s = session(t);
  assert.deepEqual(bagRows(s.run('我的背包').message), []);
  s.patch(player => { player.inventory = { '7001': 1, '7002': 2, '6001': 1, '6011': 1 }; });
  const inventory = s.player().inventory;
  s.run('装备 精铁符剑');
  assert.equal(s.player().equipment.weapon, '7001');
  s.run('使用7002');
  assert.equal(s.player().equipment.weapon, '7002');
  s.run('装备 6001');
  s.run('使用 化尘道袍');
  assert.equal(s.player().equipment.armor, '6011');
  assert.deepEqual(s.player().inventory, inventory);
  assert.deepEqual(bagRows(s.run('背包').message), [
    { id: '6001', count: 1, equipped: false },
    { id: '6011', count: 1, equipped: true },
    { id: '7001', count: 1, equipped: false },
    { id: '7002', count: 2, equipped: true }
  ]);
  s.reject('卸下7001');
  s.reject('装备 7002');
  s.reject('装备 7002 2');
  s.reject('装备 7003');
  s.run('卸下 桃木符剑');
  s.run('卸下 护具');
  assert.equal(s.player().equipment.weapon, null);
  assert.equal(s.player().equipment.armor, null);
  assert.deepEqual(s.player().inventory, inventory);
  s.reject('卸下 法器');
});

test('唯一已装备法器和防具不能寄售，多余件可售且卸下后可售最后一件', t => {
  const s = session(t);
  s.patch(player => { player.inventory = { '7001': 2, '6001': 1 }; });
  s.run('装备7001');
  s.run('装备6001');
  s.reject('坊市上架7001 10000 2');
  s.reject('坊市上架6001 10000');
  s.run('坊市上架7001 10000');
  assert.equal(s.player().inventory['7001'], 1);
  assert.equal(s.player().equipment.weapon, '7001');
  assert.equal(s.world().market[0].count, 1);
  s.reject('坊市上架7001 10000');
  s.run('卸下武器');
  s.run('坊市上架7001 10000');
  assert.equal(s.player().inventory['7001'], undefined);
  s.run('卸下防具');
  s.run('坊市上架6001 10000');
  assert.equal(s.player().inventory['6001'], undefined);
  assert.equal(s.world().market.length, 3);
});

test('主功法学习消耗一本，重复拒绝，更换不返还且降低上限时钳制气血真元', t => {
  const s = session(t);
  s.patch(player => { player.inventory = { '9001': 2, '9002': 2 }; });
  s.run('功法修炼 冰心诀');
  assert.equal(s.player().equipment.technique, '9002');
  assert.equal(s.player().inventory['9002'], 1);
  s.reject('功法修炼9002');
  s.patch(player => { player.hp = 106; player.mp = 51; });
  s.run('功法修炼9001');
  assert.equal(s.player().equipment.technique, '9001');
  assert.equal(s.player().inventory['9001'], 1);
  assert.equal(s.player().inventory['9002'], 1);
  assert.equal(s.player().hp, 103);
  assert.equal(s.player().mp, 51);
  s.run('卸下功法');
  assert.equal(s.player().equipment.technique, null);
  assert.equal(s.player().hp, 100);
  assert.equal(s.player().mp, 50);
  assert.deepEqual(s.player().inventory, { '9001': 1, '9002': 1 });
  s.reject('卸下主功法');
});

test('四类神通和攻击/减伤增益神通均能学习切换，消耗书籍且重复学习原子拒绝', t => {
  const s = session(t);
  const ids = ['8001', '8003', '8004', '8005', '8906'];
  s.patch(player => { player.inventory = Object.fromEntries(ids.map(id => [id, 2])); });
  for (const [index, id] of ids.entries()) {
    s.run(`功法修炼${id}`);
    assert.equal(s.player().equipment.skill, id);
    assert.deepEqual(s.player().inventory, Object.fromEntries(ids.map((book, i) => [book, i <= index ? 1 : 2])));
    s.reject(`功法修炼${id}`);
  }
  const before = s.player();
  const learned = s.run('我的功法');
  assert.equal(Number(learned.message.match(/\[(\d+)\]/u)[1]), 8906);
  assert.deepEqual(s.player(), before);
  s.run('卸下8906');
  assert.equal(s.player().equipment.skill, null);
  assert.deepEqual(s.player().inventory, before.inventory);
  s.reject('卸下神通');
});

test('物品操作错误类别、缺书、批量学习和空输入均不改变玩家状态', t => {
  const s = session(t);
  s.patch(player => { player.inventory = { '9001': 2, '8001': 2, '1101': 2, '10000001': 1 }; });
  for (const command of [
    '装备9001', '功法修炼1101', '功法修炼9001 2', '功法修炼8001 2',
    '功法修炼9002', '使用9001', '使用8001', '使用10000001',
    '卸下1101', '卸下9001', '卸下 不存在的物品', '物品信息', '物品信息不存在',
    '装备', '功法修炼', '使用', '卸下', '购买'
  ]) s.reject(command);
});

test('恢复气血丹支持名称连写及批量，上限截断且满血不耗药不恢复真元', t => {
  const s = session(t);
  s.reach(55);
  s.patch(player => { player.inventory = { '1101': 5 }; player.hp = 0; player.mp = 7; });
  const exp = s.player().exp;
  s.run('使用生骨丹2');
  assert.equal(s.player().hp, Math.floor(0.49 * exp * 2));
  assert.equal(s.player().mp, 7);
  assert.equal(s.player().inventory['1101'], 3);
  assert.equal(s.player().daily.pillUses['1101'], 2);
  assert.equal(s.player().pillTotals['1101'], 2);
  s.run('使用 1101');
  assert.equal(s.player().hp, exp);
  assert.equal(s.player().mp, 7);
  assert.equal(s.player().daily.pillUses['1101'], 3);
  s.reject('使用 生骨丹');
  s.reject('使用110110');
  s.reject('使用 生骨丹 3');
});

test('全恢复丹使用当前主功法上限，单颗恢复气血真元，批量与全满拒绝', t => {
  const s = session(t);
  s.reach(22);
  s.patch(player => { player.inventory = { '1112': 4, '9001': 1 }; player.hp = 0; player.mp = 0; });
  s.run('功法修炼9001');
  s.reject('使用1112 2');
  s.run('使用 天命血凝丹');
  const player = s.player();
  assert.equal(player.hp, Math.floor(player.exp * 1.03));
  assert.equal(player.mp, Math.floor(Math.floor(player.exp / 2) * 1.02));
  assert.equal(player.inventory['1112'], 3);
  assert.equal(player.pillTotals['1112'], 1);
  s.reject('使用1112');
  s.patch(p => { p.mp = 0; });
  s.run('使用1112');
  assert.equal(s.player().hp, player.hp);
  assert.equal(s.player().mp, player.mp);
  assert.equal(s.player().inventory['1112'], 2);
  s.patch(p => { p.hp = 0; });
  s.run('使用1112');
  assert.equal(s.player().hp, player.hp);
  assert.equal(s.player().mp, player.mp);
  assert.equal(s.player().inventory['1112'], 1);
});

test('普通突破增益丹可批量超过十颗和all_num，跨北京时间午夜仅清每日计数', t => {
  const s = session(t);
  s.reach(40);
  s.patch(player => { player.inventory = { '1500': 103 }; });
  const before = s.player();
  s.run('使用 冰心丹101');
  assert.equal(s.player().pillBonus, 101);
  assert.equal(s.player().inventory['1500'], 2);
  assert.equal(s.player().daily.pillUses['1500'], 101);
  assert.equal(s.player().pillTotals['1500'], 101);
  assert.equal(s.player().realm, before.realm);
  assert.equal(s.player().exp, before.exp);
  assert.equal(s.player().hp, before.hp);
  assert.equal(s.player().mp, before.mp);
  s.setTime('2026-11-13T16:00:00Z');
  s.run('使用1500');
  assert.equal(s.player().daily.pillUses['1500'], 1);
  assert.equal(s.player().pillTotals['1500'], 102);
  assert.equal(s.player().pillBonus, 102);
});

test('丹药rank下界、突破增益18级适用上界及大境界精确rank均正确', t => {
  const s = session(t);
  s.patch(player => { player.inventory = { '1101': 5, '1500': 5, '1400': 5, '1112': 2, '2009': 2 }; });
  s.reach(56);
  s.patch(player => { player.hp = 0; });
  s.reject('使用1101');
  s.reach(54);
  s.patch(player => { player.hp = 0; });
  s.run('使用1101');
  assert.equal(s.player().inventory['1101'], 4);
  s.reach(41);
  s.reject('使用1500');
  s.reach(40);
  s.run('使用1500');
  assert.equal(s.player().pillBonus, 1);
  s.reach(22);
  s.run('使用1500');
  assert.equal(s.player().pillBonus, 2);
  s.reach(21);
  s.reject('使用1500');
  s.reach(54);
  s.reject('使用1400');
  s.reach(52);
  s.reject('使用1400');
  s.reach(23);
  s.patch(player => { player.hp = 0; player.mp = 0; });
  s.reject('使用1112');
  s.reach(47);
  s.reject('使用2009');
});

test('大境界突破丹仅单颗且终身耐药跨日保留，不允许普通服用渡厄丹', t => {
  const s = session(t);
  s.reach(53);
  s.patch(player => { player.inventory = { '1400': 3, '1999': 2 }; });
  s.reject('使用1400 2');
  s.run('使用1400');
  assert.equal(s.player().inventory['1400'], 2);
  assert.equal(s.player().pillBonus, 30);
  assert.equal(s.player().pillTotals['1400'], 1);
  assert.equal(s.player().daily.pillUses['1400'], 1);
  s.reject('使用1400');
  s.setTime('2026-11-13T16:00:00Z');
  s.run('背包');
  assert.deepEqual(s.player().daily.pillUses, {});
  s.reject('使用1400');
  s.reject('使用1999');
});

test('永久攻击丹批量累积基础攻击，再与主功法和法器加成统一计算', t => {
  const s = session(t);
  s.reach(46);
  s.patch(player => { player.inventory = { '2009': 3, '9001': 1, '7001': 1 }; });
  s.run('功法修炼9001');
  s.run('装备7001');
  const before = s.player();
  s.run('使用 摄魂鬼丸 2');
  const after = s.player();
  assert.equal(after.attackBonus, 1440);
  assert.equal(after.inventory['2009'], 1);
  assert.equal(after.daily.pillUses['2009'], 2);
  assert.equal(after.pillTotals['2009'], 2);
  assert.deepEqual([after.hp, after.mp, after.exp, after.realm, after.pillBonus],
    [before.hp, before.mp, before.exp, before.realm, before.pillBonus]);
  const expectedAttack = Math.floor((Math.floor(after.exp / 10) + 1440) * (1 + 0.03 + 0.08));
  assert.equal(Number(s.run('我的状态').message.match(/攻击：(\d+)/u)[1]), expectedAttack);
  s.run('卸下法器');
  assert.equal(s.player().attackBonus, 1440);
});

test('服药数量的零、负零、负数、小数、非数字及安全整数溢出全部原子拒绝', t => {
  const s = session(t);
  s.reach(55);
  s.patch(player => { player.inventory = { '1101': 10 }; player.hp = 0; });
  for (const quantity of ['0', '-0', '-1', '1.5', 'Infinity', 'NaN', '9007199254740992']) {
    s.reject(`使用 1101 ${quantity}`);
  }
  s.reject('使用生骨丹0');
  s.reject('使用生骨丹9007199254740992');
  s.reject('使用1101 11');
});

test('每日计数、终身计数、突破增益和攻击增益溢出均不先扣药', t => {
  const s = session(t);
  s.reach(40);
  s.patch(player => {
    player.inventory = { '1101': 2, '1500': 2, '2009': 2 };
    player.hp = 0;
    player.daily.pillUses['1101'] = MAX;
  });
  s.reject('使用1101');
  s.patch(player => { player.daily.pillUses = {}; player.pillTotals['1101'] = MAX; });
  s.reject('使用1101');
  s.patch(player => { player.pillBonus = MAX; });
  s.reject('使用1500');
  s.patch(player => { player.attackBonus = MAX; });
  s.reject('使用2009');
});

test('安全整数最大批量可消费，但药效乘积溢出拒绝整批且不先更新计数', t => {
  const s = session(t);
  s.reach(40);
  s.patch(player => { player.inventory = { '1500': MAX, '2009': MAX }; });
  s.reject(`使用2009 ${MAX}`);
  s.run(`使用1500 ${MAX}`);
  assert.equal(s.player().inventory['1500'], undefined);
  assert.equal(s.player().inventory['2009'], MAX);
  assert.equal(s.player().pillBonus, MAX);
  assert.equal(s.player().daily.pillUses['1500'], MAX);
  assert.equal(s.player().pillTotals['1500'], MAX);
});

test('物品信息提供实际恢复系数、耐药余量和装备属性，查询不消耗库存', t => {
  const s = session(t);
  s.reach(53);
  s.patch(player => { player.pillTotals['1400'] = 1; });
  const before = s.snapshot();
  const hpInfo = s.run('查询生骨丹').message;
  assert.equal(Number(hpInfo.match(/当前为([\d.]+)%/u)[1]), 48);
  const rateInfo = s.run('物品信息1500').message;
  assert.equal(Number(rateInfo.match(/阈值(\d+)个百分点/u)[1]), 1);
  assert.equal(Number(rateInfo.match(/差≤(\d+)/u)[1]), 18);
  const bigInfo = s.run('物品信息1400').message;
  assert.equal(Number(bigInfo.match(/终身最多(\d+)颗/u)[1]), 1);
  assert.equal(Number(bigInfo.match(/已服(\d+)颗/u)[1]), 1);
  assert.equal(Number(bigInfo.match(/rank相等（(\d+)）/u)[1]), 53);
  assert.equal(Number(s.run('物品信息1112').message.match(/每次(\d+)颗/u)[1]), 1);
  assert.equal(Number(s.run('物品信息2009').message.match(/基础攻击(\d+)点/u)[1]), 720);
  const protectedInfo = s.run('物品信息1999').message;
  assert.equal(Number(protectedInfo.match(/消耗(\d+)颗/u)[1]), 1);
  const weaponInfo = s.run('物品信息7002').message;
  assert.equal(Number(weaponInfo.match(/实际([\d.]+)%/u)[1]), Number((9 / 101 * 100).toFixed(2)));
  assert.equal(Number(s.run('物品信息6001').message.match(/减伤率([\d.]+)%/u)[1]), 8);
  s.run('物品信息10000001');
  assert.deepEqual(s.snapshot(), before);
});

test('商店只列真实开放有价丹药，低境界照常买药且不能购买无价丹或装备', t => {
  const s = session(t);
  s.patch(player => { player.money = 1_000_000; });
  const before = s.snapshot();
  const stock = [...s.run('修仙商店').message.matchAll(/^(\d+)\. .* · 每颗(\d+)灵石$/gmu)]
    .map(match => ({ id: match[1], price: Number(match[2]) }));
  const expected = Object.entries(data.pills)
    .filter(([, item]) => Object.hasOwn(item, 'price') && Number.isSafeInteger(item.price) && item.price > 0 && item.status === 1)
    .map(([id, item]) => ({ id, price: item.price }));
  assert.deepEqual(stock, expected);
  assert.deepEqual(s.snapshot(), before);
  s.run('购买生骨丹2');
  assert.equal(s.player().money, 980_000);
  assert.equal(s.player().inventory['1101'], 2);
  s.run('购买1999');
  assert.equal(s.player().money, 880_000);
  assert.equal(s.player().inventory['1999'], 1);
  s.reject('使用1101');
  for (const id of ['1400', '2000', '2009', '7001', '9001', '10000001']) s.reject(`购买${id}`);
  assert.deepEqual(s.player().inventory, { '1101': 2, '1999': 1 });
});

test('买药余额恰足可清零，余额不足、总价和背包数量溢出不半扣', t => {
  const s = session(t);
  s.patch(player => { player.money = 20_000; });
  s.reject('购买1101 3');
  s.run('购买 1101 2');
  assert.equal(s.player().money, 0);
  assert.equal(s.player().inventory['1101'], 2);
  s.reject('购买1101');
  s.patch(player => { player.money = MAX; player.inventory['1101'] = MAX; });
  s.reject('购买1101');
  s.patch(player => { player.inventory = {}; });
  s.reject(`购买1101 ${Math.floor(MAX / 10_000) + 1}`);
  for (const count of ['0', '-0', '-2', '1.1', '9007199254740992']) s.reject(`购买1101 ${count}`);
});

test('坊市上架查询整批交易，卖方扣税到账且买方收整批物品', t => {
  const s = session(t);
  s.register('b');
  s.patch(player => { player.inventory = { '1101': 5 }; player.money = 100; });
  s.patch(player => { player.money = 20_001; }, 'b');
  assert.deepEqual(listingRows(s.run('坊市').message), []);
  s.run('坊市上架 生骨丹 20001 3');
  assert.equal(s.player().inventory['1101'], 2);
  assert.equal(s.world().nextListingId, 2);
  assert.equal(s.world().market[0].createdAt, Date.parse('2026-11-13T01:00:00Z'));
  const listed = s.snapshot();
  assert.deepEqual(listingRows(s.run('坊市查询', 'b').message), [
    { id: 1, itemId: '1101', count: 3, price: 20_001, sellerId: 'a' }
  ]);
  assert.deepEqual(s.snapshot(), listed);
  s.reject('坊市购买1');
  s.reject('坊市下架1', 'b');
  s.run('坊市购买1', 'b');
  assert.equal(s.player('b').inventory['1101'], 3);
  assert.equal(s.player('b').money, 0);
  assert.equal(s.player().money, 18_101);
  assert.equal(s.player().money + s.player('b').money, 100 + 20_001 - 2000);
  assert.equal(s.player().inventory['1101'] + s.player('b').inventory['1101'], 5);
  assert.deepEqual(s.world().market, []);
  s.reject('坊市购买1', 'b');
  s.reject('坊市下架1');
});

test('坊市下架返还整批，可再次上架且编号不复用', t => {
  const s = session(t);
  s.patch(player => { player.inventory = { '9001': 2 }; });
  s.run('坊市上架9001 10000 2');
  assert.equal(s.player().inventory['9001'], undefined);
  s.run('坊市下架1');
  assert.equal(s.player().inventory['9001'], 2);
  assert.deepEqual(s.world().market, []);
  s.run('坊市上架9001 10000');
  assert.equal(s.world().market[0].id, 2);
  assert.equal(s.world().market[0].count, 1);
  assert.equal(s.world().nextListingId, 3);
});

test('坊市每人最多十单，别人配额独立，下架后自己的配额释放', t => {
  const s = session(t);
  s.register('b');
  s.patch(player => { player.inventory = { '1101': 12 }; });
  s.patch(player => { player.inventory = { '1101': 1 }; }, 'b');
  for (let i = 0; i < 10; i++) s.run('坊市上架1101 10000');
  assert.equal(s.world().market.length, 10);
  assert.equal(s.player().inventory['1101'], 2);
  s.reject('坊市上架1101 10000');
  s.run('坊市上架1101 10000', 'b');
  assert.equal(s.world().market.length, 11);
  s.run('坊市下架1');
  assert.equal(s.player().inventory['1101'], 3);
  s.run('坊市上架1101 10000');
  assert.equal(s.world().market.filter(listing => listing.sellerId === 'a').length, 10);
  assert.equal(s.world().nextListingId, 13);
});

test('坊市非法格式、最低价格、缺库存和安全整数边界上架均不扣物品', t => {
  const s = session(t);
  s.patch(player => { player.inventory = { '1101': 2 }; });
  for (const command of [
    '坊市上架', '坊市上架1101', '坊市上架不存在 10000', '坊市上架1101 9999',
    '坊市上架1101 0', '坊市上架1101 -0', '坊市上架1101 10000 0',
    '坊市上架1101 10000 -0', '坊市上架1101 10000 3',
    '坊市上架1101 9007199254740992', '坊市上架1101 10000 9007199254740992',
    '坊市购买0', '坊市购买-0', '坊市购买9007199254740992', '坊市购买1', '坊市下架1'
  ]) s.reject(command);
  s.patchWorld(world => { world.nextListingId = MAX; });
  s.reject('坊市上架1101 10000');
});

test('坊市缺钱购买不半扣，补足后成交', t => {
  const s = session(t);
  s.register('b');
  s.patch(player => { player.inventory = { '1101': 2 }; player.money = 50; });
  s.patch(player => { player.money = 9999; player.inventory = { '1101': 1 }; }, 'b');
  s.run('坊市上架1101 10000 2');
  s.reject('坊市购买1', 'b');
  s.patch(player => { player.money = 10_000; }, 'b');
  s.run('坊市购买1', 'b');
  assert.equal(s.player('b').money, 0);
  assert.equal(s.player('b').inventory['1101'], 3);
  assert.equal(s.player().money, 9050);
  assert.deepEqual(s.world().market, []);
});

test('坊市买家库存、卖家余额及下架返货溢出保留挂单和所有余额', t => {
  const s = session(t);
  s.register('b');
  s.patch(player => { player.inventory = { '1101': 2 }; player.money = 0; });
  s.patch(player => { player.inventory = { '1101': MAX }; player.money = 10_000; }, 'b');
  s.run('坊市上架1101 10000 2');
  s.reject('坊市购买1', 'b');
  s.patch(player => { player.inventory = {}; }, 'b');
  s.patch(player => { player.money = MAX; });
  s.reject('坊市购买1', 'b');
  s.patch(player => { player.inventory = { '1101': MAX }; });
  s.reject('坊市下架1');
});

test('送灵石按真实用户ID同群转移，守恒且允许转出全部安全整数余额', t => {
  const s = session(t);
  s.register('b');
  s.patch(player => { player.money = 20_000; });
  s.run('送灵石 @显示名不用于定位 12345', 'a', 'b');
  assert.equal(s.player().money, 7655);
  assert.equal(s.player('b').money, 12_345);
  assert.equal(s.player().money + s.player('b').money, 20_000);
  s.patch(player => { player.money = MAX; });
  s.patch(player => { player.money = 0; }, 'b');
  s.run(`送灵石${MAX}`, 'a', 'b');
  assert.equal(s.player().money, 0);
  assert.equal(s.player('b').money, MAX);
  assert.equal(s.player().money + s.player('b').money, MAX);
});

test('送灵石非法数量、缺目标、自转账、目标不存在、跨群目标与余额不足原子拒绝', t => {
  const s = session(t);
  s.register('b');
  s.register('c', 'other');
  s.patch(player => { player.money = 100; });
  for (const value of ['', '0', '-0', '-1', '+1', '1.5', 'Infinity', 'NaN', '9007199254740992']) {
    s.reject(`送灵石 @b ${value}`, 'a', 'b');
  }
  s.reject('送灵石100');
  s.reject('送灵石100', 'a', 'a');
  s.reject('送灵石100', 'a', 'missing');
  s.reject('送灵石100', 'a', 'c');
  assert.equal(s.player('c'), null);
  assert.equal(s.player('c', 'other').money, 0);
  s.reject('送灵石101', 'a', 'b');
  const before = s.snapshot();
  assert.throws(() => s.run('送灵石1', 'a', ''), TypeError);
  assert.deepEqual(s.snapshot(), before);
});

test('转账目标余额溢出时发送方不先扣款，恰好安全上限可完成', t => {
  const s = session(t);
  s.register('b');
  s.patch(player => { player.money = 2; });
  s.patch(player => { player.money = MAX - 1; }, 'b');
  s.reject('送灵石2', 'a', 'b');
  s.run('送灵石1', 'a', 'b');
  assert.equal(s.player().money, 1);
  assert.equal(s.player('b').money, MAX);
  s.reject('送灵石1', 'a', 'b');
});

test('背包、学习、商店、坊市和转账必须先在当前群注册角色', t => {
  const s = session(t);
  for (const command of [
    '背包', '我的功法', '物品信息1101', '商店', '坊市查询',
    '坊市上架1101 10000', '送灵石1', '使用1101', '装备7001', '功法修炼9001', '卸下法器', '购买1101'
  ]) s.reject(command, 'unregistered', 'a');
  assert.equal(s.player('unregistered'), null);
});
