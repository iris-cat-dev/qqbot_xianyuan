'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data, stats } = require('../src/rules');

function session(t) {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-expansion-'));
  const databasePath = join(directory, 'game.sqlite');
  let now = Date.parse('2026-11-13T01:00:00Z');
  let random = 0;
  const game = createGame({ databasePath, now: () => now, random: () => random });
  const store = openStore(databasePath);
  t.after(() => { store.close(); game.close(); rmSync(directory, { recursive: true, force: true }); });
  return {
    run(text, userId = 'a', targetId, groupId = 'group') {
      return game.handleCommand({ text, userId, targetId, groupId, nickname: userId });
    },
    register(userId = 'a') { return this.run('我要修仙', userId); },
    player(userId = 'a') { return game.getPlayer('group', userId); },
    patch(change, userId = 'a') {
      const player = game.getPlayer('group', userId);
      change(player);
      store.save('group', player);
    },
    world() { return store.getWorld('group'); },
    patchWorld(change) { const world = store.getWorld('group'); change(world); store.saveWorld('group', world); },
    advanceMinutes(minutes) { now += minutes * 60_000; },
    advanceSeconds(seconds) { now += seconds * 1_000; },
    setRandom(value) { random = value; }
  };
}

function seedMoney(s, amount, userId = 'a') {
  s.patch(player => { player.money = amount; }, userId);
}

test('旧存档惰性补齐新增玩家和世界字段', t => {
  const s = session(t);
  s.register();
  s.patch(player => {
    for (const key of ['bank', 'estate', 'alchemy', 'sectId', 'sectPosition', 'sectContribution', 'attackPractice', 'sectTask', 'lastSectTaskRefreshAt', 'lastStealAt', 'position', 'romance']) delete player[key];
    player.daily = { date: player.daily.date, refreshes: 0, pillUses: {} };
  });
  s.patchWorld(world => { for (const key of ['sects', 'nextSectId', 'auction', 'romance', 'romancePartners']) delete world[key]; });
  const player = s.player();
  assert.equal(player.bank, null);
  assert.equal(player.position, '新手村广场');
  assert.deepEqual(player.alchemy.records, {});
  assert.equal(player.daily.dualCultivations, 0);
  assert.deepEqual(player.romance.favor, {});
  assert.deepEqual(s.world().sects, {});
  assert.equal(s.world().nextSectId, 1);
  assert.equal(s.world().romance, null);
  assert.deepEqual(s.world().romancePartners, {});
});

test('灵庄按实际小时结息，存款上限错误不会留下部分结息', t => {
  const s = session(t);
  s.register();
  seedMoney(s, 1_000_000);
  s.run('灵庄存入 500000');
  s.advanceMinutes(60);
  assert.match(s.run('灵庄结算').message, /获得1000灵石/u);
  assert.equal(s.player().money, 501_000);
  const before = s.player();
  s.advanceMinutes(60);
  assert.match(s.run('灵庄存入 600000').message, /最多存1000000灵石/u);
  assert.deepEqual(s.player(), before);
  s.run('灵庄会员升级');
  assert.equal(s.player().bank.level, 2);
  assert.equal(s.player().money, 302_000);
});

test('洞天生产药材与灵石，炼丹配方原子消耗并按炉具产出', t => {
  const s = session(t);
  s.register();
  seedMoney(s, 2_000_000);
  s.run('洞天福地购买');
  s.advanceMinutes(240);
  assert.match(s.run('灵田收取').message, /收获1株药材/u);
  s.run('灵矿开垦');
  s.advanceMinutes(57);
  assert.match(s.run('灵矿收取').message, /收获20000灵石/u);
  s.patch(player => {
    player.inventory['3001'] = 3;
    player.inventory['3002'] = 4;
    player.inventory['4003'] = 1;
  });
  const result = s.run('配方 主药恒心草3 药引红绫草1 辅药红绫草3 丹炉陨铁炉');
  assert.match(result.message, /炼成洗髓丹×1/u);
  assert.equal(s.player().inventory['2000'], 1);
  assert.equal(s.player().inventory['3001'], undefined);
  assert.equal(s.player().inventory['3002'], undefined);
  assert.equal(s.player().alchemy.exp, 10);
  const settled = s.player();
  s.run('配方 主药恒心草3 药引红绫草1 辅药红绫草3 丹炉陨铁炉');
  assert.deepEqual(s.player(), settled);
});

test('赠送、偷窃、双修和打劫均在同群跨玩家事务内结算', t => {
  const s = session(t);
  s.register('a'); s.register('b');
  s.patch(player => { player.money = 300_000; player.inventory['7001'] = 2; player.realm = 1; player.exp = data.realms[1].exp; player.hp = player.exp; player.mp = Math.floor(player.exp / 2); }, 'a');
  s.patch(player => { player.money = 100_000; player.exp = 500; player.hp = 500; player.mp = 250; }, 'b');
  s.run('赠送 @b 精铁符剑 1', 'a', 'b');
  assert.equal(s.player('a').inventory['7001'], 1);
  assert.equal(s.player('b').inventory['7001'], 1);
  assert.equal(s.player('a').money, 299_500);
  s.setRandom(0);
  s.run('偷灵石 @b', 'a', 'b');
  assert.equal(s.player('a').money, 300_500);
  assert.equal(s.player('b').money, 99_000);
  const totalExp = s.player('a').exp + s.player('b').exp;
  s.run('双修 @b', 'a', 'b');
  assert.ok(s.player('a').exp + s.player('b').exp > totalExp);
  const totalMoney = s.player('a').money + s.player('b').money;
  s.run('打劫 @b', 'a', 'b');
  assert.equal(s.player('a').money + s.player('b').money, totalMoney);
  assert.ok(s.player('a').hp >= 1);
  assert.ok(s.player('b').hp >= 1);
});

test('宗门治理、定时资材、任务与攻击修炼形成完整循环', t => {
  const s = session(t);
  s.register('owner'); s.register('member');
  const realm = data.realms.findIndex(entry => entry.name === '元婴境圆满');
  s.patch(player => { player.realm = realm; player.exp = data.realms[realm].exp; player.hp = player.exp; player.mp = Math.floor(player.exp / 2); player.money = 10_000_000; }, 'owner');
  s.run('创建宗门 青云宗', 'owner');
  s.run('加入宗门 1', 'member');
  s.run('宗门职位变更 @member 3', 'owner', 'member');
  assert.equal(s.player('member').sectPosition, 3);
  s.run('宗门捐献 5000000', 'owner');
  s.advanceMinutes(120);
  s.run('我的宗门', 'owner');
  assert.equal(s.world().sects['1'].materials, 5_000_000);
  const attackBefore = stats(s.player('owner')).attack;
  s.run('升级攻击修炼', 'owner');
  assert.equal(s.player('owner').attackPractice, 1);
  assert.ok(stats(s.player('owner')).attack > attackBefore);
  assert.match(s.run('宗门功法搜寻', 'owner').message, /搜寻到/u);
  assert.equal(s.world().sects['1'].techniques.length, 1);
  s.run('宗门任务接取', 'owner');
  s.advanceMinutes(15);
  assert.match(s.run('宗门任务完成', 'owner').message, /完成狩猎邪修/u);
  assert.equal(s.player('owner').daily.sectTasks, 1);
  assert.ok(s.player('owner').sectContribution > 0);
});

test('交友会竞价托管、落后退款并只向赢家发一次物品', t => {
  const s = session(t);
  s.register('a'); s.register('b');
  seedMoney(s, 500_000, 'a'); seedMoney(s, 500_000, 'b');
  s.setRandom(0);
  assert.match(s.run('举行交友会', 'a').message, /渡厄丹/u);
  s.run('出价 105000', 'a');
  assert.equal(s.player('a').money, 395_000);
  s.run('出价 110250', 'b');
  assert.equal(s.player('a').money, 500_000);
  assert.equal(s.player('b').money, 389_750);
  s.advanceSeconds(140);
  assert.match(s.run('交友会查询', 'b').message, /竞得渡厄丹/u);
  assert.equal(s.player('b').inventory['1999'], 1);
  assert.equal(s.world().auction, null);
  const winner = s.player('b');
  s.run('交友会查询', 'b');
  assert.deepEqual(s.player('b'), winner);
});

test('地图移动保存位置，断路不改变状态', t => {
  const s = session(t);
  s.register();
  assert.match(s.run('地图').message, /新手村广场/u);
  assert.match(s.run('向北走').message, /杂货铺/u);
  assert.equal(s.player().position, '杂货铺');
  const before = s.player();
  assert.match(s.run('向北走').message, /没有路/u);
  assert.deepEqual(s.player(), before);
});
