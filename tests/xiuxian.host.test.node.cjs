'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data, stats, MINUTE } = require('../src/rules');
const { buildBreakthroughFacts } = require('../src/journey');

const ANSWER = '我修为够了，盲冲会耗气，先稳住气息再凝气。';
function review() {
  return {
    scores: {
      experience: { value: 2, quote: '修为够了', factIds: ['state'] },
      problem: { value: 2, quote: '盲冲', },
      reason: { value: 2, quote: '盲冲会耗气' },
      change: { value: 2, quote: '先稳住气息再凝气' }
    },
    feedback: '能说明问题、原因与调整。', followUp: null
  };
}
function resources(player) {
  const { realm, exp, hp, mp, money, inventory, breakthroughAt, breakthroughBonus, pillBonus } = player;
  return { realm, exp, hp, mp, money, inventory, breakthroughAt, breakthroughBonus, pillBonus };
}
function session(t, judge) {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-host-'));
  const databasePath = join(directory, 'game.sqlite');
  let now = Date.parse('2026-11-13T01:00:00Z');
  let draws = 0;
  const game = createGame({ databasePath, now: () => now, random: () => { draws++; return 0; }, judge });
  const event = (text, answer = text === ANSWER) => ({ groupId: 'host-group-secret', userId: 'host-user-secret', nickname: '私密道号', text, answer });
  const player = () => game.getPlayer(event('').groupId, event('').userId);
  const seed = change => {
    const store = openStore(databasePath);
    try {
      const p = store.get(event('').groupId, event('').userId);
      change(p);
      store.save(event('').groupId, p);
    } finally { store.close(); }
  };
  game.handleCommand(event('我要修仙'));
  seed(p => {
    p.exp = data.realms[1].exp;
    p.hp = stats(p).maxHp;
    p.mp = stats(p).maxMp;
  });
  t.after(() => { game.close(); rmSync(directory, { recursive: true, force: true }); });
  return { game, event, player, seed, directory, databasePath, advance: minutes => { now += minutes * MINUTE; }, draws: () => draws };
}

test('异步宿主单次判定不占写事务，并重新读取并发修改后只结算一次', async t => {
  let release;
  let started;
  let calls = 0;
  const ready = new Promise(resolve => { started = resolve; });
  const waiting = new Promise(resolve => { release = resolve; });
  const s = session(t, async () => {
    calls++;
    const probe = openStore(s.databasePath);
    try {
      probe.transaction(() => {
        const p = probe.get(s.event('').groupId, s.event('').userId);
        assert.equal(p.breakthroughTrial.status, 'judging');
        p.money += 7;
        probe.save(s.event('').groupId, p);
      });
    } finally { probe.close(); }
    started();
    await waiting;
    return review();
  });
  const before = s.player();
  await s.game.handleMessage(s.event('突破'));
  const draws = s.draws();
  const first = s.game.handleMessage(s.event(ANSWER));
  await ready;
  const second = s.game.handleMessage(s.event('突破'));
  release();
  const [a, b] = await Promise.all([first, second]);
  assert.deepEqual(a, b);
  assert.equal(calls, 1);
  assert.equal(s.draws(), draws + 1);
  assert.equal(s.player().realm, before.realm + 1);
  assert.equal(s.player().money, before.money + 7);
});

test('模型异常与非法结果不扣资源，恢复后复用原答案完成判定', async t => {
  let mode = 'offline';
  let calls = 0;
  const s = session(t, async () => {
    calls++;
    if (mode === 'offline') throw new Error('service unavailable');
    const result = review();
    if (mode === 'invalid') result.scores.reason.value = 99;
    return result;
  });
  await s.game.handleMessage(s.event('突破'));
  const before = resources(s.player());
  const failed = await s.game.handleMessage(s.event(ANSWER));
  assert.equal(failed.error, 'judge_failed');
  assert.deepEqual(resources(s.player()), before);
  const { id, revision, answers } = s.player().breakthroughTrial;
  mode = 'invalid';
  const invalid = await s.game.handleMessage(s.event('突破'));
  assert.equal(invalid.error, 'invalid_review');
  assert.deepEqual(resources(s.player()), before);
  assert.equal(s.player().breakthroughTrial.id, id);
  assert.equal(s.player().breakthroughTrial.revision, revision);
  assert.deepEqual(s.player().breakthroughTrial.answers, answers);
  mode = 'online';
  await s.game.handleMessage(s.event('突破'));
  assert.equal(calls, 3);
  assert.equal(s.player().realm, before.realm + 1);
});

test('未配置判定器时返回可恢复模型请求，不伪造评分', async t => {
  const s = session(t);
  await s.game.handleMessage(s.event('突破'));
  const before = resources(s.player());
  const result = await s.game.handleMessage(s.event(ANSWER));
  assert.equal(s.player().breakthroughTrial.status, 'judging');
  assert.equal(s.player().breakthroughTrial.review, null);
  assert.deepEqual(resources(s.player()), before);
  assert.equal(result.reviewRequest.requestId, s.player().breakthroughTrial.id);
});

test('不存在账号的模型回写不创建账号，也不修改其他玩家', t => {
  const s = session(t);
  const before = s.player();
  const result = s.game.resolveReview({ groupId: s.event('').groupId,
    userId: 'missing-user', kind: 'breakthrough', requestId: 'missing-trial', revision: 1, review: review() });
  assert.equal(result.handled, false);
  assert.equal(s.game.getPlayer(s.event('').groupId, 'missing-user'), null);
  assert.deepEqual(s.player(), before);
});

test('选项式短答只作为答题文本，不能触发帮助或判定文件读取', t => {
  const s = session(t);
  const before = resources(s.player());
  for (const text of ['--help', '--review', '--db']) {
    s.game.handleCommand(s.event('取消突破'));
    s.game.handleCommand(s.event('突破'));
    const output = s.game.handleCommand(s.event(text, true));
    assert.equal(s.player().breakthroughTrial.status, 'judging');
    assert.deepEqual(s.player().breakthroughTrial.answers, [text]);
    assert.equal(output.reviewRequest.requestId, s.player().breakthroughTrial.id);
    assert.deepEqual(resources(s.player()), before);
  }
});

test('重建引擎提问、取请求、受信任回写及重复回写只突破一级', t => {
  const s = session(t);
  const invoke = callback => {
    const game = createGame({ databasePath: s.databasePath, now: () => Date.parse('2026-11-13T01:00:00Z'), random: () => 0 });
    try { return callback(game); } finally { game.close(); }
  };
  const before = s.player();
  invoke(game => game.handleCommand(s.event('突破')));
  const { reviewRequest } = invoke(game => game.handleCommand(s.event(ANSWER)));
  const event = { groupId: s.event('').groupId, userId: s.event('').userId,
    kind: reviewRequest.kind, requestId: reviewRequest.requestId, revision: reviewRequest.revision, review: review() };
  const settled = invoke(game => game.resolveReview(event));
  assert.equal(s.player().realm, before.realm + 1);
  const after = s.player();
  assert.deepEqual(invoke(game => game.resolveReview(event)), settled);
  assert.deepEqual(s.player(), after);
});

test('旧存档保留资产，实际闭关经历有界、持久且不含玩家身份', t => {
  const s = session(t);
  s.seed(p => {
    delete p.breakthroughTrial;
    delete p.insightReviews;
    delete p.riftAdventure;
    delete p.journey;
    delete p.journeySequence;
    p.exp = 100;
    p.money = 19777;
    p.inventory['1999'] = 2;
    p.root.speed = 1;
  });
  assert.equal(s.player().riftAdventure, null);
  assert.equal(s.player().money, 19777);
  assert.equal(s.player().inventory['1999'], 2);
  const gains = [];
  for (let i = 0; i < 16; i++) {
    const beforeExp = s.player().exp;
    s.game.handleCommand(s.event('闭关'));
    s.advance(1);
    s.game.handleCommand(s.event('出关'));
    gains.push(s.player().exp - beforeExp);
  }
  const p = s.player();
  assert.equal(p.journey.length, 8);
  assert.equal(p.journeySequence, 16);
  assert.deepEqual(p.journey.map(entry => entry.id), Array.from({ length: 8 }, (_, i) => `journey-${i + 9}`));
  const store = openStore(s.databasePath);
  try { assert.deepEqual(store.get(s.event('').groupId, s.event('').userId).journey, p.journey); }
  finally { store.close(); }
  const facts = buildBreakthroughFacts(p);
  assert.equal(facts.length, 9);
  assert.ok(facts.slice(1).every(fact => fact.type === 'closing'));
  assert.deepEqual(facts.slice(1).map(fact => fact.expGain), gains.slice(-8));
  const serialized = JSON.stringify(facts);
  for (const identity of ['host-group-secret', 'host-user-secret', '私密道号']) assert.equal(serialized.includes(identity), false);
  assert.equal(p.inventory['1999'], 2);
});
