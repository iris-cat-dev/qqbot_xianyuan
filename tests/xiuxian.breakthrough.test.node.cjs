'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data, MINUTE, stats } = require('../src/rules');

function session(t) {
  const directory = mkdtempSync(join(tmpdir(), 'xiuxian-breakthrough-'));
  const databasePath = join(directory, 'game.sqlite');
  let now = Date.parse('2026-11-13T01:00:00Z');
  let values = [0];
  let calls = 0;
  const game = createGame({
    databasePath, now: () => now,
    random: () => values[Math.min(calls++, values.length - 1)]
  });
  t.after(() => {
    game.close();
    rmSync(directory, { recursive: true, force: true });
  });
  const s = {
    game,
    run(text, userId = 'a', groupId = 'group') {
      const event = { text, userId, groupId, nickname: userId };
      return game.handleCommand({ ...event, answer: game.parseInput(event) === null });
    },
    resolve(request, review, userId = 'a', groupId = 'group') {
      return game.resolveReview({
        groupId, userId, kind: request.kind, requestId: request.requestId, revision: request.revision, review
      });
    },
    player(userId = 'a', groupId = 'group') { return game.getPlayer(groupId, userId); },
    seed(change, userId = 'a', groupId = 'group') {
      const player = s.player(userId, groupId);
      change(player);
      const store = openStore(databasePath);
      try { store.save(groupId, player); } finally { store.close(); }
    },
    ready(realm = 1, userId = 'a', groupId = 'group') {
      s.run('我要修仙', userId, groupId);
      s.seed(player => {
        player.realm = realm;
        player.exp = Math.floor(data.realms[realm + 1].exp * 1.2);
        player.hp = player.exp;
        player.mp = Math.floor(player.exp / 2);
        player.money = 1000;
        player.inventory['1999'] = 2;
      }, userId, groupId);
      s.setRandom(0);
    },
    advance(minutes) { now += minutes * MINUTE; },
    setRandom(...next) { values = next; calls = 0; },
    randomCalls() { return calls; },
    now() { return now; }
  };
  s.ready();
  return s;
}

function resources(player) {
  const { realm, exp, money, hp, mp, inventory, breakthroughAt, breakthroughBonus, pillBonus, activity } = player;
  return { realm, exp, money, hp, mp, inventory, breakthroughAt, breakthroughBonus, pillBonus, activity };
}

function decision(answer = '慢', values = [0, 1, 1, 2]) {
  const [experience, problem, reason, change] = values;
  const total = values.reduce((sum, value) => sum + value, 0);
  const passed = total >= 4 && reason >= 1;
  return {
    scores: {
      experience: { value: experience, quote: experience ? answer : '', factIds: experience ? ['state'] : [] },
      problem: { value: problem, quote: problem ? answer : '' },
      reason: { value: reason, quote: reason ? answer : '' },
      change: { value: change, quote: change ? answer : '' }
    },
    feedback: passed ? '你找到了原因，也说出了改变。' : '还需要说清原因和下一步。',
    followUp: passed ? null : '为什么这样做，下次怎么改？'
  };
}

function submit(s, answer = '慢') {
  s.run('突破');
  return s.run(answer).reviewRequest;
}

test('闭关中发送突破会先结算闭关并直接开始突破', t => {
  const s = session(t);
  s.seed(player => { player.exp = data.realms[player.realm + 1].exp - 1; });
  s.run('闭关');
  s.advance(1);

  const result = s.run('突破');
  const player = s.player();
  assert.match(result.message, /闭关1分钟，增加\d+修为[\s\S]*几个字或一句话/u);
  assert.equal(player.activity, null);
  assert.equal(player.breakthroughTrial.status, 'awaiting');
  assert.ok(player.exp >= data.realms[player.realm + 1].exp);
  assert.equal(player.journey.at(-1).type, 'closing');
});

test('首问和重复突破不扣资源、不掷骰，自然短答直接进入判断', t => {
  const s = session(t);
  const before = resources(s.player());
  const first = s.run('突破');
  const trial = s.player().breakthroughTrial;
  assert.equal(trial.status, 'awaiting');
  assert.match(first.message, /几个字或一句话/u);
  assert.equal(Array.from(trial.question).length <= 40, true);
  assert.deepEqual(resources(s.player()), before);
  assert.equal(s.run('突破').message, first.message);
  assert.equal(s.player().breakthroughTrial.id, trial.id);
  assert.equal(s.randomCalls(), 0);

  const response = s.run('慢');
  assert.ok(response.reviewRequest);
  assert.equal(s.player().breakthroughTrial.status, 'judging');
  assert.deepEqual(s.player().breakthroughTrial.answers, ['慢']);
  assert.deepEqual(resources(s.player()), before);
  const result = s.resolve(response.reviewRequest, decision());
  assert.match(result.message, /突破成功/u);
  const player = s.player();
  assert.equal(player.realm, before.realm + 1);
  assert.equal(player.exp, before.exp);
  assert.equal(player.inventory['1999'], 2);
  assert.equal(player.breakthroughTrial.status, 'settled');
  assert.equal(player.breakthroughTrial.review.total, 4);
  assert.equal(player.breakthroughAt, s.now());
  assert.equal(player.hp, stats(player).maxHp);
  assert.equal(player.mp, stats(player).maxMp);
  assert.equal(s.randomCalls(), 1);
});

test('空答和超过200个Unicode字符的答复不占次数，边界短答允许', t => {
  const s = session(t);
  s.run('突破');
  const before = resources(s.player());
  s.run('   ');
  s.run('🐱'.repeat(201));
  assert.equal(s.player().breakthroughTrial.revision, 0);
  assert.deepEqual(s.player().breakthroughTrial.answers, []);
  assert.deepEqual(resources(s.player()), before);
  assert.ok(s.run('🐱'.repeat(200)).reviewRequest);
  assert.equal(s.player().breakthroughTrial.answers[0], '🐱'.repeat(200));
  assert.equal(s.randomCalls(), 0);
});

test('判断中重复突破恢复同一request，新答复不覆盖进行中答案', t => {
  const s = session(t);
  const request = submit(s);
  assert.deepEqual(s.run('突破').reviewRequest, request);
  assert.equal(s.run('重新回答').handled, false);
  assert.deepEqual(s.player().breakthroughTrial.answers, ['慢']);
  assert.equal(s.player().breakthroughTrial.revision, request.revision);
  assert.equal(s.randomCalls(), 0);
});

test('只追问一次，两次不通过不扣资源，并允许新一轮', t => {
  const s = session(t);
  const before = resources(s.player());
  const first = submit(s);
  const response = s.resolve(first, decision('慢', [0, 1, 0, 1]));
  assert.match(response.message, /为什么这样做/u);
  assert.equal(s.player().breakthroughTrial.status, 'awaiting');
  assert.equal(s.resolve(first, decision()).message, response.message);
  const second = s.run('再慢点').reviewRequest;
  assert.equal(second.revision, first.revision + 1);
  assert.deepEqual(s.player().breakthroughTrial.answers, ['慢', '再慢点']);
  s.resolve(second, decision('再慢点', [0, 1, 0, 1]));
  const rejected = s.player().breakthroughTrial;
  assert.equal(rejected.status, 'rejected');
  assert.equal(s.run('第三个回答').handled, false);
  assert.deepEqual(resources(s.player()), before);
  assert.equal(s.randomCalls(), 0);
  s.run('突破');
  assert.equal(s.player().breakthroughTrial.status, 'awaiting');
  assert.notEqual(s.player().breakthroughTrial.id, rejected.id);
});

test('第二个自然短答可通过并自动结算，第一份旧回写不会覆盖新答', t => {
  const s = session(t);
  const first = submit(s);
  const firstResponse = s.resolve(first, decision('慢', [0, 1, 0, 1]));
  const second = s.run('先恢复').reviewRequest;
  const pending = s.player();
  assert.equal(s.resolve(first, decision()).message, firstResponse.message);
  assert.deepEqual(s.player(), pending);
  s.resolve(second, decision('先恢复'));
  assert.equal(s.player().realm, 2);
  assert.equal(s.player().breakthroughTrial.answers.length, 2);
});

test('相同目标、事实和完整回答复用两次未通过缓存，不重新请求模型', t => {
  const s = session(t);
  const first = submit(s);
  s.resolve(first, decision('慢', [0, 1, 0, 1]));
  const second = s.run('再慢点').reviewRequest;
  s.resolve(second, decision('再慢点', [0, 1, 0, 1]));
  assert.equal(s.player().insightReviews.length, 2);
  const oldId = s.player().breakthroughTrial.id;
  s.run('突破');
  assert.notEqual(s.player().breakthroughTrial.id, oldId);
  assert.equal(s.run('慢').reviewRequest, undefined);
  assert.equal(s.player().breakthroughTrial.status, 'awaiting');
  assert.equal(s.run('再慢点').reviewRequest, undefined);
  assert.equal(s.player().breakthroughTrial.status, 'rejected');
  assert.equal(s.player().insightReviews.length, 2);
  assert.equal(s.randomCalls(), 0);
});

test('事实或目标变化不得复用旧评分，理解缓存仅保留最近16份', t => {
  const s = session(t);
  for (let i = 0; i < 18; i++) {
    const answer = `慢${i}`;
    const request = submit(s, answer);
    s.resolve(request, decision(answer, [0, 1, 0, 1]));
    s.run('取消突破');
  }
  assert.equal(s.player().insightReviews.length, 16);
  assert.ok(submit(s, '慢0'));
  s.run('取消突破');
  s.seed(player => { player.hp--; });
  assert.ok(submit(s, '慢17'));
  s.run('取消突破');
  s.seed(player => {
    player.realm = 2;
    player.exp = data.realms[3].exp;
  });
  assert.ok(submit(s, '慢17'));
});

test('取消后相同材料复用已经通过的理解，缓存通过仍必须正式结算', t => {
  const s = session(t);
  const request = submit(s);
  s.seed(player => { player.breakthroughAt = s.now(); });
  s.resolve(request, decision());
  assert.equal(s.player().breakthroughTrial.status, 'qualified');
  assert.equal(s.randomCalls(), 0);
  s.run('取消突破');
  s.seed(player => { player.breakthroughAt = null; });
  s.run('突破');
  s.setRandom(0);
  const response = s.run('慢');
  assert.equal(response.reviewRequest, undefined);
  assert.match(response.message, /突破成功/u);
  assert.equal(s.player().realm, 2);
  assert.equal(s.player().insightReviews.length, 1);
  assert.equal(s.randomCalls(), 1);
});

test('模型异常和错误格式均保留原答可重试，不默认满分、不作为玩家失败', t => {
  const s = session(t);
  const request = submit(s);
  const before = resources(s.player());
  const invalid = [undefined, null, 'not JSON', decision(), decision(), decision()];
  invalid[3].scores.reason.quote = '未出现的原因';
  invalid[4].scores.problem.value = 3;
  invalid[5].realm = 55;
  for (const raw of invalid) {
    const response = s.resolve(request, raw);
    assert.equal(response.error, 'invalid_review');
    assert.deepEqual(resources(s.player()), before);
    assert.equal(s.player().breakthroughTrial.status, 'judging');
    assert.equal(s.player().breakthroughTrial.review, null);
    assert.equal(s.player().insightReviews.length, 0);
    assert.deepEqual(s.run('突破').reviewRequest, request);
  }
  s.resolve(request, decision());
  assert.equal(s.player().realm, 2);
  assert.equal(s.randomCalls(), 1);
});

test('取消判断中的突破使旧判定失效，重新开始的trial不接收旧结果', t => {
  const s = session(t);
  const request = submit(s);
  s.run('用丹');
  const before = resources(s.player());
  s.run('取消突破');
  assert.equal(s.player().breakthroughTrial.status, 'cancelled');
  s.resolve(request, decision());
  assert.deepEqual(resources(s.player()), before);
  assert.equal(s.player().breakthroughTrial.review, null);
  s.run('突破');
  const next = s.player();
  s.resolve(request, decision());
  assert.deepEqual(s.player(), next);
  assert.equal(s.randomCalls(), 0);
});

test('资格复核：修为降低后通过的理解仍提交，恢复资格才可再次尝试', t => {
  const s = session(t);
  const request = submit(s);
  s.seed(player => { player.exp = data.realms[2].exp - 1; });
  const before = resources(s.player());
  const response = s.resolve(request, decision());
  assert.match(response.message, /修为不足/u);
  assert.deepEqual(resources(s.player()), before);
  assert.equal(s.player().breakthroughTrial.status, 'qualified');
  assert.equal(s.player().breakthroughTrial.review.passed, true);
  assert.equal(s.player().insightReviews.length, 1);
  s.seed(player => { player.exp = data.realms[2].exp; });
  assert.equal(s.run('突破').reviewRequest, undefined);
  assert.equal(s.player().realm, 2);
  assert.equal(s.randomCalls(), 1);
});

test('快捷升境界后第二答旧判定失效，不增加评分缓存或再次结算', t => {
  const s = session(t);
  const first = submit(s);
  const firstResponse = s.resolve(first, decision('慢', [0, 1, 0, 1]));
  const second = s.run('先恢复').reviewRequest;
  s.run('直接突破');
  const before = s.player();
  s.setRandom(0);
  const response = s.resolve(second, decision('先恢复'));
  assert.equal(typeof response.message, 'string');
  assert.deepEqual(resources(s.player()), resources(before));
  assert.equal(s.player().breakthroughTrial.status, 'cancelled');
  assert.deepEqual(s.player().breakthroughTrial.review, before.breakthroughTrial.review);
  assert.deepEqual(s.player().insightReviews, before.insightReviews);
  assert.equal(s.resolve(first, decision()).message, firstResponse.message);
  assert.equal(s.randomCalls(), 0);
  s.advance(60);
  s.seed(player => { player.exp = data.realms[3].exp; });
  const oldId = s.player().breakthroughTrial.id;
  s.run('突破');
  assert.notEqual(s.player().breakthroughTrial.id, oldId);
  assert.equal(s.player().breakthroughTrial.status, 'awaiting');
  assert.equal(s.player().breakthroughTrial.fromRealm, 2);
  assert.equal(s.player().realm, 2);
  assert.equal(s.randomCalls(), 0);
});

test('快捷升境界后旧目标不接受自然答，重复突破明确取消旧轮', t => {
  for (const status of ['awaiting', 'judging']) {
    for (const text of ['突破', '先恢复']) {
      const s = session(t);
      s.run('突破');
      if (status === 'judging') s.run('慢');
      const oldTrial = s.player().breakthroughTrial;
      s.run('直接突破');
      const before = resources(s.player());
      s.setRandom(0);
      const response = s.run(text);
      assert.equal(response.reviewRequest, undefined);
      if (text !== '突破') {
        assert.equal(response.handled, false);
        assert.equal(s.player().breakthroughTrial.status, status);
        s.run('突破');
      }
      assert.equal(s.player().breakthroughTrial.id, oldTrial.id);
      assert.equal(s.player().breakthroughTrial.status, 'cancelled');
      assert.deepEqual(s.player().breakthroughTrial.answers, oldTrial.answers);
      assert.equal(s.player().breakthroughTrial.review, null);
      assert.equal(s.player().insightReviews.length, 0);
      assert.deepEqual(resources(s.player()), before);
      assert.equal(s.randomCalls(), 0);
    }
  }
});

test('用丹只选择不消耗，库存消失时保留通过资格，取消保护才结算', t => {
  const s = session(t);
  const request = submit(s);
  s.run('用丹');
  assert.equal(s.player().inventory['1999'], 2);
  s.seed(player => { delete player.inventory['1999']; });
  assert.match(s.resolve(request, decision()).message, /渡厄丹不足/u);
  assert.equal(s.player().breakthroughTrial.status, 'qualified');
  assert.equal(s.player().breakthroughAt, null);
  assert.equal(s.randomCalls(), 0);
  s.run('不用丹');
  s.run('突破');
  assert.equal(s.player().realm, 2);
  assert.equal(s.randomCalls(), 1);
});

test('没有渡厄丹不能选择保护，库存存在也不自动使用', t => {
  const s = session(t);
  s.run('突破');
  s.seed(player => { delete player.inventory['1999']; });
  assert.match(s.run('用丹').message, /渡厄丹不足/u);
  assert.equal(s.player().breakthroughTrial.protectedAttempt, false);
  s.seed(player => { player.inventory['1999'] = 2; });
  const request = s.run('慢').reviewRequest;
  s.setRandom(0.99, 0.99);
  s.resolve(request, decision());
  assert.equal(s.player().inventory['1999'], 2);
  assert.equal(s.player().exp, 2160);
  assert.equal(s.player().breakthroughTrial.status, 'qualified');
});

test('概率失败保留理解和旧保底，重复回写不再骰，60分钟后直接重试', t => {
  const s = session(t);
  const request = submit(s);
  s.setRandom(0.6, 0.99);
  const failedResponse = s.resolve(request, decision());
  const failed = s.player();
  assert.equal(failed.realm, 1);
  assert.equal(failed.exp, 2160);
  assert.equal(failed.hp, 2160);
  assert.equal(failed.mp, 1080);
  assert.equal(failed.breakthroughBonus, Math.max(1, Math.floor(data.realms[1].rate * 0.5)));
  assert.equal(failed.breakthroughTrial.status, 'qualified');
  assert.equal(failed.breakthroughTrial.review.passed, true);
  assert.equal(failed.breakthroughTrial.lastAttempt.probability, 60);
  assert.equal(s.randomCalls(), 2);
  s.setRandom(0);
  assert.equal(s.resolve(request, decision()).message, failedResponse.message);
  assert.deepEqual(s.player(), failed);
  assert.match(s.run('突破').message, /冷却/u);
  assert.equal(s.randomCalls(), 0);
  s.advance(59);
  assert.match(s.run('突破').message, /冷却/u);
  assert.equal(s.randomCalls(), 0);
  s.advance(1);
  assert.equal(s.run('突破').reviewRequest, undefined);
  const succeeded = s.player();
  assert.equal(succeeded.realm, 2);
  assert.equal(succeeded.breakthroughBonus, 0);
  assert.equal(succeeded.breakthroughTrial.lastAttempt.probability, 80);
  assert.equal(s.randomCalls(), 1);
  assert.equal(s.resolve(request, decision()).message, failedResponse.message);
  assert.deepEqual(s.player(), succeeded);
});

test('保护概率失败只耗一丹，不损修为，冷却和幂等均不再耗丹', t => {
  const s = session(t);
  const request = submit(s);
  s.run('用丹');
  s.setRandom(0.99);
  const result = s.resolve(request, decision());
  const failed = s.player();
  assert.equal(failed.inventory['1999'], 1);
  assert.equal(failed.exp, 2400);
  assert.equal(failed.pillBonus, 0);
  assert.equal(s.randomCalls(), 1);
  assert.equal(s.resolve(request, decision()).message, result.message);
  s.run('突破');
  assert.equal(s.player().inventory['1999'], 1);
  assert.equal(s.randomCalls(), 1);
  s.advance(60);
  s.setRandom(0);
  s.run('突破');
  const succeeded = s.player();
  assert.equal(succeeded.inventory['1999'], undefined);
  assert.equal(succeeded.realm, 2);
  assert.equal(s.randomCalls(), 1);
  s.resolve(request, decision());
  assert.deepEqual(s.player(), succeeded);
});

test('通过成功只消耗正式保护丹一次，清丹药概率与保底', t => {
  const s = session(t);
  s.seed(player => { player.breakthroughBonus = 4; player.pillBonus = 8; });
  const request = submit(s);
  s.run('用丹');
  s.setRandom(0.71);
  const result = s.resolve(request, decision());
  const settled = s.player();
  assert.equal(settled.realm, 2);
  assert.equal(settled.inventory['1999'], 1);
  assert.equal(settled.breakthroughBonus, 0);
  assert.equal(settled.pillBonus, 0);
  assert.equal(settled.breakthroughTrial.lastAttempt.probability, 72);
  assert.equal(s.resolve(request, decision()).message, result.message);
  assert.deepEqual(s.player(), settled);
  assert.equal(s.randomCalls(), 1);
});

test('通过的评分档位决定60/75/90底线，基础概率与加成封顶100', t => {
  const s = session(t);
  for (const [values, floor] of [
    [[0, 1, 1, 2], 60], [[1, 1, 1, 2], 60],
    [[1, 2, 1, 2], 75], [[2, 2, 1, 2], 75], [[2, 2, 2, 2], 90]
  ]) {
    s.seed(player => {
      player.realm = 1;
      player.exp = 2400;
      player.breakthroughAt = null;
      player.breakthroughBonus = 0;
      player.pillBonus = 0;
    });
    const answer = `慢${values.join('')}`;
    const request = submit(s, answer);
    s.setRandom(floor / 100 - 0.000001);
    s.resolve(request, decision(answer, values));
    assert.equal(s.player().realm, 2);
    assert.equal(s.player().breakthroughTrial.lastAttempt.probability, floor);
  }
  s.seed(player => {
    player.realm = 0;
    player.exp = 1200;
    player.breakthroughAt = null;
    player.breakthroughBonus = 30;
    player.pillBonus = 30;
  });
  const request = submit(s);
  s.setRandom(0.999999);
  s.resolve(request, decision());
  assert.equal(s.player().realm, 1);
  assert.equal(s.player().breakthroughTrial.lastAttempt.probability, 100);
});

test('总分足够但原因零分不通过，不掷骰也不扣保护丹', t => {
  const s = session(t);
  const request = submit(s);
  s.run('用丹');
  s.resolve(request, decision('慢', [2, 2, 0, 2]));
  assert.equal(s.player().breakthroughTrial.status, 'awaiting');
  assert.equal(s.player().breakthroughTrial.review.total, 6);
  assert.equal(s.player().breakthroughTrial.review.passed, false);
  assert.equal(s.player().inventory['1999'], 2);
  assert.equal(s.player().breakthroughAt, null);
  assert.equal(s.randomCalls(), 0);
});

test('所有可突破境界都能首问与短答结算，最高境界不能开题', t => {
  const s = session(t);
  for (let realm = 0; realm < data.realms.length - 1; realm++) {
    s.seed(player => {
      player.realm = realm;
      player.exp = data.realms[realm + 1].exp;
      player.hp = player.exp;
      player.mp = Math.floor(player.exp / 2);
      player.breakthroughAt = null;
      player.breakthroughBonus = 0;
      player.pillBonus = 0;
    });
    const question = s.run('突破');
    assert.equal(question.handled, true);
    assert.equal(s.player().breakthroughTrial.fromRealm, realm);
    assert.equal(s.player().breakthroughTrial.targetRealm, realm + 1);
    assert.equal(Array.from(s.player().breakthroughTrial.question).length <= 40, true);
    const request = s.run('慢').reviewRequest;
    assert.ok(request);
    s.setRandom(0);
    s.resolve(request, decision());
    assert.equal(s.player().realm, realm + 1);
  }
  const before = s.player();
  assert.match(s.run('突破').message, /无须再突破/u);
  assert.deepEqual(s.player(), before);
});

test('同群不同玩家及同ID不同群隔离，已知命令不被当成心得', t => {
  const s = session(t);
  s.ready(1, 'b');
  s.ready(1, 'a', 'other');
  s.run('突破');
  s.run('我的状态');
  s.run('闭关');
  assert.deepEqual(s.player().breakthroughTrial.answers, []);
  assert.equal(s.player().activity.kind, 'closing');
  assert.equal(s.run('慢', 'b').handled, false);
  assert.equal(s.run('慢', 'a', 'other').handled, false);
  const request = s.run('慢').reviewRequest;
  s.resolve(request, decision(), 'b');
  s.resolve(request, decision(), 'a', 'other');
  assert.equal(s.player().breakthroughTrial.status, 'judging');
  assert.equal(s.player('b').realm, 1);
  assert.equal(s.player('a', 'other').realm, 1);
  s.resolve(request, decision());
  assert.equal(s.player().realm, 2);
  assert.equal(s.player().activity.kind, 'closing');
  assert.equal(s.player('b').realm, 1);
  assert.equal(s.player('a', 'other').realm, 1);
});
