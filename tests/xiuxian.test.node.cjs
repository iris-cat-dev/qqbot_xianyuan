'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data, MINUTE } = require('../src/rules');

function session(t, start = '2026-11-13T01:00:00Z', databasePath = ':memory:') {
  const directory = databasePath === ':memory:' ? mkdtempSync(join(tmpdir(), 'xiuxian-core-')) : null;
  if (directory) databasePath = join(directory, 'game.sqlite');
  let now = Date.parse(start);
  let random = 0;
  const game = createGame({ databasePath, now: () => now, random: () => random });
  t.after(() => {
    game.close();
    if (directory) rmSync(directory, { recursive: true, force: true });
  });
  return {
    game,
    run(text, userId = 'a', groupId = 'group', targetId) {
      return game.handleCommand({ text, userId, groupId, targetId, nickname: userId });
    },
    player(userId = 'a', groupId = 'group') { return game.getPlayer(groupId, userId); },
    seed(change, userId = 'a', groupId = 'group') {
      const player = game.getPlayer(groupId, userId);
      change(player);
      const store = openStore(databasePath);
      store.save(groupId, player);
      store.close();
    },
    advance(minutes) { now += minutes * MINUTE; },
    setTime(value) { now = Date.parse(value); },
    setRandom(value) { random = value; }
  };
}

test('签到以北京时间跨日、按境界发放且同ID不同群独立', t => {
  const s = session(t, '2026-11-12T23:59:00Z');
  s.run('我要修仙');
  s.run('修仙签到');
  assert.equal(s.player().money, 500);
  s.advance(2);
  s.run('修仙签到');
  assert.equal(s.player().money, 500);
  s.setTime('2026-11-13T16:00:00Z');
  s.run('修仙签到');
  assert.equal(s.player().money, 1000);
  s.run('我要修仙', 'a', 'other');
  assert.equal(s.player('a', 'other').money, 0);
  s.seed(player => { player.realm = 6; player.exp = data.realms[6].exp; }, 'a', 'other');
  s.run('修仙签到', 'a', 'other');
  assert.equal(s.player('a', 'other').money, 3500);
});

test('跨午夜悬赏保留进行中快照，奖励只能结算一次', t => {
  const s = session(t, '2026-11-13T15:50:00Z');
  s.run('我要修仙');
  s.run('悬赏令');
  s.run('悬赏令接取1');
  const task = s.player().activity.task;
  s.advance(task.minutes);
  s.run('悬赏令结算');
  assert.equal(s.player().activity, null);
  assert.equal(s.player().exp, 100 + task.exp * 2);
  const settled = s.player();
  s.run('悬赏令结算');
  assert.deepEqual(s.player(), settled);
});

test('突破首问不耗资源，快捷保护失败耗一丹不损修为，冷却拒绝不再耗丹', t => {
  const s = session(t);
  s.run('我要修仙');
  s.seed(p => { p.inventory['1999'] = 2; });
  s.setRandom(0);
  s.run('闭关');
  s.advance(15);
  s.run('出关');
  assert.equal(s.player().exp, 1500);
  const before = s.player();
  s.run('突破');
  const asked = s.player();
  assert.equal(asked.breakthroughTrial.status, 'awaiting');
  assert.equal(asked.exp, before.exp);
  assert.equal(asked.realm, before.realm);
  assert.equal(asked.money, before.money);
  assert.deepEqual(asked.inventory, before.inventory);
  assert.equal(asked.breakthroughAt, before.breakthroughAt);
  s.setRandom(0.999999);
  s.run('渡厄突破');
  const failed = s.player();
  assert.equal(failed.realm, 0);
  assert.equal(failed.exp, 1500);
  assert.equal(failed.inventory['1999'], 1);
  assert.equal(failed.breakthroughBonus, 50);
  assert.notEqual(failed.breakthroughAt, null);
  s.run('渡厄突破');
  assert.deepEqual(s.player(), failed);
});

test('转账守恒，余额不足和不存在的跨群目标不产生部分写入', t => {
  const s = session(t);
  s.run('我要修仙');
  s.run('新手礼包领取');
  s.run('我要修仙', 'b');
  s.run('送灵石 @b 10000', 'a', 'group', 'b');
  assert.equal(s.player().money, 10000);
  assert.equal(s.player('b').money, 10000);
  const sender = s.player();
  const recipient = s.player('b');
  s.run('送灵石 @b 10001', 'a', 'group', 'b');
  assert.deepEqual(s.player(), sender);
  assert.deepEqual(s.player('b'), recipient);
  s.run('我要修仙', 'c', 'other');
  s.run('送灵石 @c 1', 'a', 'group', 'c');
  assert.deepEqual(s.player(), sender);
  assert.equal(s.player('c'), null);
});

test('最高境界闭关继续增长，不因缺下一境界而归零', t => {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-boundary-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const databasePath = join(directory, 'game.sqlite');
  const s = session(t, undefined, databasePath);
  s.run('我要修仙');
  const player = s.player();
  player.realm = data.realms.length - 1;
  player.exp = data.realms[player.realm].exp;
  player.hp = player.exp;
  player.mp = Math.floor(player.exp / 2);
  const store = openStore(databasePath);
  store.save('group', player);
  store.close();
  s.run('闭关');
  s.advance(1);
  s.run('出关');
  assert.equal(s.player().exp, player.exp + 30 * player.root.speed * data.realms[player.realm].speed);
  assert.equal(s.player().realm, player.realm);
});

test('重复注册和未注册操作不创建或覆盖角色，未知文本交回调用方', t => {
  const s = session(t);
  s.run('我的修仙信息');
  assert.equal(s.player(), null);
  s.run('我要修仙');
  s.run('新手礼包领取');
  const player = s.player();
  s.run('我要修仙');
  assert.deepEqual(s.player(), player);
  assert.equal(s.run('普通聊天').handled, false);
  assert.deepEqual(s.player(), player);
});

test('道号按Unicode字符限制，洗灵根只改根和钱包', t => {
  const s = session(t);
  s.run('我要修仙');
  s.run('改名 灵猫');
  assert.equal(s.player().name, '灵猫');
  for (const name of ['', '伊小咪', '一二三四五六七八九十甲']) {
    s.run(`改名 ${name}`);
    assert.equal(s.player().name, '灵猫');
  }
  s.run('改名 🐱🐱🐱🐱🐱🐱🐱🐱🐱🐱');
  assert.equal(Array.from(s.player().name).length, 10);
  const poor = s.player();
  s.run('重入仙途');
  assert.deepEqual(s.player(), poor);
  s.seed(p => { p.money = 200000; });
  s.setRandom(0.999999);
  const before = s.player();
  s.run('重入仙途');
  const after = s.player();
  assert.notDeepEqual(after.root, before.root);
  assert.equal(after.money, before.money - 200000);
  after.root = before.root;
  after.money = before.money;
  assert.deepEqual(after, before);
});

test('礼包逐份领取且冷却和次数持久化', t => {
  const s = session(t);
  s.run('我要修仙');
  s.run('领取新手礼包');
  const first = s.player();
  assert.equal(first.money, 20000);
  assert.equal(first.inventory['10000001'], 3);
  assert.equal(first.inventory['10010001'], 3);
  s.run('新手礼包领取');
  assert.deepEqual(s.player(), first);
  s.advance(30);
  s.run('新手礼包领取');
  assert.equal(s.player().money, 60000);
  assert.equal(s.player().giftClaims, 2);
  const final = s.player();
  s.run('新手礼包领取');
  assert.deepEqual(s.player(), final);
});

test('闭关互斥，付费出关按原结算顺序扣钱并受修为上限约束', t => {
  const s = session(t);
  s.run('我要修仙');
  const idle = s.player();
  s.run('出关');
  assert.deepEqual(s.player(), idle);
  s.run('新手礼包领取');
  s.run('闭关');
  const closing = s.player();
  s.advance(25);
  s.run('闭关');
  assert.deepEqual(s.player(), closing);
  s.run('灵石出关');
  assert.equal(s.player().money, 14000);
  assert.equal(s.player().exp, 1500);
  assert.equal(s.player().activity, null);
  assert.equal(s.player().hp, 100);
  assert.equal(s.player().mp, 50);
});

test('突破门槛、失败惩罚、冷却和保底提升遵循状态变化', t => {
  const s = session(t);
  s.run('我要修仙');
  const starter = s.player();
  s.run('直接突破');
  assert.deepEqual(s.player(), starter);
  s.run('闭关');
  s.advance(15);
  s.run('出关');
  const noPill = s.player();
  s.run('渡厄突破');
  assert.deepEqual(s.player(), noPill);
  s.setRandom(0.999999);
  s.run('直接突破');
  assert.equal(s.player().exp, 1350);
  assert.equal(s.player().breakthroughBonus, 50);
  s.run('闭关');
  s.advance(15);
  s.run('出关');
  const recovering = s.player();
  s.run('直接突破');
  assert.deepEqual(s.player(), recovering);
  s.advance(45);
  s.run('直接突破');
  assert.equal(s.player().realm, 1);
  assert.equal(s.player().exp, 1500);
  assert.equal(s.player().hp, 1500);
  assert.equal(s.player().mp, 750);
  assert.equal(s.player().breakthroughBonus, 0);
});

test('突破失败气血真元限制到剩余修为上限而非写成损失数', t => {
  const s = session(t);
  s.run('我要修仙');
  s.seed(p => { p.realm = 1; p.exp = 3000; p.hp = 3000; p.mp = 1500; });
  s.setRandom(0.999999);
  s.run('直接突破');
  assert.equal(s.player().exp, 2700);
  assert.equal(s.player().hp, 2700);
  assert.equal(s.player().mp, 1350);
});

test('丹药突破加成在实际尝试后消耗，成功不扣门槛修为', t => {
  const s = session(t);
  s.run('我要修仙');
  s.seed(p => { p.exp = 1200; p.pillBonus = 1; });
  s.setRandom(0.999999);
  s.run('直接突破');
  assert.equal(s.player().realm, 1);
  assert.equal(s.player().exp, 1200);
  assert.equal(s.player().pillBonus, 0);
  s.seed(p => { p.realm = data.realms.length - 1; });
  const top = s.player();
  s.run('突破');
  s.run('直接突破');
  assert.deepEqual(s.player(), top);
});

test('排行榜按数值境界、钱包和即时战力排序，限制本群', t => {
  const s = session(t);
  for (const user of ['高阶', '富豪', '强者']) s.run('我要修仙', user);
  s.seed(p => { p.realm = 10; p.exp = 300000; p.money = 1; }, '高阶');
  s.seed(p => { p.realm = 9; p.exp = 500000; p.money = 900000; }, '富豪');
  s.seed(p => { p.realm = 9; p.exp = 600000; p.root.speed = 2; }, '强者');
  s.run('我要修仙', '外群', 'other');
  for (const [command, first] of [['排行榜', '高阶'], ['修仙排行榜', '高阶'], ['灵石排行榜', '富豪'], ['战力排行榜', '强者']]) {
    const message = s.run(command, '高阶').message;
    for (const other of ['高阶', '富豪', '强者'].filter(name => name !== first)) assert.ok(message.indexOf(first) < message.indexOf(other));
    assert.equal(message.includes('外群'), false);
  }
});

test('悬赏成功掉落、失败保底和耗时缩短是实际资源变化', t => {
  const s = session(t);
  s.run('我要修仙');
  s.seed(p => { p.realm = 3; p.exp = 3000; p.hp = 3000; p.mp = 1500; });
  s.run('悬赏令');
  const entry = s.player().board.entries[0];
  assert.equal(entry.rate, 100);
  assert.ok(entry.minutes < 60);
  assert.notEqual(entry.itemId, null);
  s.run('悬赏令接取 1');
  const pending = s.player();
  s.run('悬赏令结算');
  assert.deepEqual(s.player(), pending);
  s.advance(entry.minutes);
  s.run('悬赏令结算');
  assert.equal(s.player().exp, 3000 + entry.exp * 2);
  assert.equal(s.player().inventory[entry.itemId], 1);
  s.seed(p => { p.board = null; p.exp = 1000; });
  s.setRandom(0.999999);
  s.run('悬赏令');
  const hard = s.player().board.entries[0];
  assert.ok(hard.rate < 100);
  s.run('悬赏令接取1');
  s.advance(hard.minutes);
  const before = s.player();
  s.run('悬赏令结算');
  assert.equal(s.player().exp, before.exp + hard.exp);
  assert.deepEqual(s.player().inventory, before.inventory);
});

test('悬赏免费刷新恰为三次，付费失败不修改候选和次数，跨日恢复免费额', t => {
  const s = session(t);
  s.run('我要修仙');
  for (let i = 0; i < 3; i++) s.run('悬赏令刷新');
  const exhausted = s.player();
  assert.equal(exhausted.daily.refreshes, 3);
  s.run('悬赏令刷新');
  assert.deepEqual(s.player(), exhausted);
  s.seed(p => { p.money = data.missionConfig.refresh_cost * 2; });
  s.run('悬赏令刷新');
  assert.equal(s.player().daily.refreshes, 4);
  assert.equal(s.player().money, 100000);
  s.setTime('2026-11-13T16:00:00Z');
  s.run('悬赏令刷新');
  assert.equal(s.player().daily.refreshes, 1);
  assert.equal(s.player().money, 100000);
});

test('悬赏放弃需足额扣款，不存在任务、活动互斥和上限拒绝均不损状态', t => {
  const s = session(t);
  s.run('我要修仙');
  const idle = s.player();
  s.run('悬赏令结算');
  s.run('悬赏令终止');
  assert.deepEqual(s.player(), idle);
  s.run('闭关');
  const closing = s.player();
  s.run('悬赏令接取1');
  assert.deepEqual(s.player(), closing);
  s.run('出关');
  s.run('悬赏令接取1');
  const active = s.player();
  s.run('悬赏令');
  s.run('悬赏令放弃');
  assert.deepEqual(s.player(), active);
  s.seed(p => { p.money = data.missionConfig.give_up_cost * 4; });
  s.run('悬赏令终止');
  assert.equal(s.player().activity, null);
  assert.equal(s.player().money, data.missionConfig.give_up_cost * 3);
  s.seed(p => { p.exp = 1500; });
  const capped = s.player();
  s.run('悬赏令接取1');
  assert.deepEqual(s.player(), capped);
  s.seed(p => { p.realm = 55; p.board = null; });
  const above = s.player();
  s.run('悬赏令');
  assert.deepEqual(s.player(), above);
});

test('悬赏最后一项到时仍结算，下轮重新生成且编号越界不改状态', t => {
  const s = session(t);
  s.run('我要修仙');
  for (let i = 0; i < 3; i++) {
    s.run('悬赏令接取1');
    s.advance(s.player().activity.task.minutes);
    s.run('悬赏令结算');
  }
  assert.equal(s.player().exp, 700);
  assert.equal(s.player().board.entries.length, 0);
  s.run('悬赏令');
  assert.equal(s.player().board.entries.length, 3);
  s.run('悬赏令接取3');
  s.advance(s.player().activity.task.minutes);
  s.run('悬赏令结算');
  const before = s.player();
  s.run('悬赏令接取3');
  assert.deepEqual(s.player(), before);
});

test('输入边界错误和事务异常不留半份存档', t => {
  const s = session(t);
  for (const event of [
    { groupId: '', userId: 'a', text: '我要修仙' },
    { groupId: 'group', userId: 123, text: '我要修仙' },
    { groupId: 'group', userId: 'a', text: 123 },
    { groupId: 'group', userId: 'a', text: '我要修仙', nickname: 123 },
    { groupId: 'group', userId: 'a', text: '切磋', targetId: '' }
  ]) assert.throws(() => s.game.handleCommand(event), TypeError);
  assert.equal(s.player(), null);
  const store = openStore(':memory:');
  t.after(() => store.close());
  assert.throws(() => store.transaction(() => { store.save('g', { userId: 'u', money: 100 }); throw new Error('interrupted'); }), /interrupted/u);
  assert.equal(store.get('g', 'u'), null);
});

test('灵根权重90点完整覆盖，真灵根属性无放回', () => {
  const { drawRoot } = require('../src/rules');
  const counts = {};
  for (let weight = 1; weight <= 90; weight++) {
    const root = drawRoot(() => (weight - 0.5) / 90);
    counts[root.type] = (counts[root.type] ?? 0) + 1;
    if (root.type === '真灵根') {
      const attributes = root.name.replace('属性灵根', '').split('、');
      assert.ok(attributes.length === 2 || attributes.length === 3);
      assert.equal(new Set(attributes).size, attributes.length);
    }
  }
  assert.deepEqual(counts, { 混沌灵根: 1, 融合灵根: 3, 超灵根: 5, 龙灵根: 10, 天灵根: 15, 变异灵根: 20, 真灵根: 30, 伪灵根: 5, 无灵根: 1 });
});

