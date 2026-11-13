'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const fairies = require('../data/fairies.json');

function session(t) {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-romance-'));
  const databasePath = join(directory, 'game.sqlite');
  let now = Date.parse('2026-11-13T01:00:00Z');
  let random = 0;
  const game = createGame({ databasePath, now: () => now, random: () => random });
  const store = openStore(databasePath);
  t.after(() => { store.close(); game.close(); rmSync(directory, { recursive: true, force: true }); });
  return {
    run(text, userId = 'a', groupId = 'group') {
      return game.handleCommand({ text, userId, groupId, nickname: userId });
    },
    register(userId = 'a', groupId = 'group') { return this.run('我要修仙', userId, groupId); },
    player(userId = 'a', groupId = 'group') { return game.getPlayer(groupId, userId); },
    patch(change, userId = 'a', groupId = 'group') {
      const player = game.getPlayer(groupId, userId);
      change(player);
      store.save(groupId, player);
    },
    world(groupId = 'group') { return store.getWorld(groupId); },
    patchWorld(change, groupId = 'group') {
      const world = store.getWorld(groupId);
      change(world);
      store.saveWorld(groupId, world);
    },
    advanceDays(days) { now += days * 24 * 60 * 60_000; },
    setRandom(value) { random = value; }
  };
}

test('仙子按北京时间日期在各群惰性随机刷新且不连续重复', t => {
  const s = session(t);
  assert.match(s.run('仙缘查询').message, /苏姗姗/u);
  assert.equal(s.player(), null);
  assert.equal(s.world().romance.fairyId, 'su-shanshan');

  s.advanceDays(1);
  assert.match(s.run('仙缘查询').message, /今日仙缘已刷新[\s\S]*江晚月/u);
  assert.equal(s.world().romance.fairyId, 'jiang-wanyue');

  assert.match(s.run('仙缘查询', 'a', 'other-group').message, /苏姗姗/u);
  assert.equal(s.world('other-group').romance.fairyId, 'su-shanshan');
});

test('专属任务原子消耗物品并限制每日一次', t => {
  const s = session(t);
  s.register();
  s.run('仙缘查询');
  assert.match(s.run('仙缘任务接取').message, /帮助苏姗姗突破金丹境/u);

  const before = s.player();
  assert.match(s.run('仙缘任务完成').message, /需要聚顶丹/u);
  assert.deepEqual(s.player(), before);

  s.patch(player => { player.inventory['1401'] = 1; player.inventory['1402'] = 1; });
  assert.match(s.run('仙缘任务完成').message, /好感\+30，当前好感30/u);
  const completed = s.player();
  assert.equal(completed.inventory['1401'], undefined);
  assert.equal(completed.inventory['1402'], undefined);
  assert.equal(completed.romance.completedSpecial['su-shanshan'], true);
  assert.equal(completed.romance.task, null);
  assert.match(s.run('仙缘任务接取').message, /今日已经完成一次/u);
});

test('普通战斗任务使用固定战斗引擎并保留真实战损', t => {
  const s = session(t);
  s.register();
  s.run('仙缘查询');
  s.patch(player => { player.romance.completedSpecial['su-shanshan'] = true; });
  s.setRandom(0.25);
  assert.match(s.run('仙缘任务接取').message, /排解修行仇怨/u);
  const result = s.run('仙缘任务完成');
  assert.match(result.message, /寻仇修士[\s\S]*获胜[\s\S]*好感\+12/u);
  const player = s.player();
  assert.equal(player.romance.favor['su-shanshan'], 12);
  assert.ok(player.hp > 0 && player.hp < 100);
});

test('表白原子绑定唯一仙子并拒绝本群第二位玩家', t => {
  const s = session(t);
  s.register('a'); s.register('b'); s.register('c');
  s.run('仙缘查询', 'a');
  s.patch(player => { player.romance.favor['su-shanshan'] = 120; }, 'a');
  s.patch(player => { player.romance.favor['su-shanshan'] = 150; }, 'b');
  s.patch(player => { player.romance.favor['su-shanshan'] = 200; }, 'c');
  const board = s.run('仙缘查询', 'a').message;
  assert.match(board, /1\. c · 200[\s\S]*2\. b · 150[\s\S]*3\. a · 120/u);

  s.setRandom(0.99);
  assert.match(s.run('表白 苏姗姗', 'b').message, /还需要时间确认心意/u);
  assert.match(s.run('表白 苏姗姗', 'b').message, /今日已经向她表白过/u);

  s.setRandom(0);
  assert.match(s.run('表白苏姗姗', 'a').message, /正式结为道侣[\s\S]*不能再与她结缘/u);
  assert.equal(s.player('a').romance.partnerFairyId, 'su-shanshan');
  assert.equal(s.world().romancePartners['su-shanshan'], 'a');
  assert.match(s.run('我的修仙信息', 'a').message, /仙缘：与苏姗姗结为道侣/u);

  assert.match(s.run('表白 苏姗姗', 'c').message, /已与a结为道侣/u);
  assert.equal(s.player('c').romance.partnerFairyId, null);
  assert.equal(s.world().romancePartners['su-shanshan'], 'a');
});

test('跨日后旧任务失效并切换到新仙子的专属剧情', t => {
  const s = session(t);
  s.register();
  s.run('仙缘查询');
  s.run('仙缘任务接取');
  s.advanceDays(1);
  assert.match(s.run('我的仙缘任务').message, /昨日仙缘任务已失效/u);
  assert.equal(s.player().romance.task, null);
  assert.match(s.run('仙缘任务接取').message, /赎回月魄玉/u);
});

test('十位仙子均已结缘后不再刷新可认领仙子', t => {
  const s = session(t);
  s.register();
  s.patchWorld(world => {
    world.romance = null;
    world.romancePartners = Object.fromEntries(fairies.map((fairy, index) => [fairy.id, `owner-${index}`]));
  });
  assert.match(s.run('仙缘查询').message, /十位仙子均已与修士结为道侣/u);
  assert.match(s.run('我的仙缘').message, /今日仙子：暂无/u);
  assert.match(s.run('仙缘任务接取').message, /暂无新的仙缘任务/u);
});
