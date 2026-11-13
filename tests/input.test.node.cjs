'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync, symlinkSync, writeFileSync, readFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { createGame } = require('../src/engine');
const { openStore } = require('../src/store');
const { data } = require('../src/rules');

function session(t) {
  const directory = mkdtempSync(join(tmpdir(), 'qqbot-game-input-'));
  const databasePath = join(directory, 'game.sqlite');
  let clockCalls = 0;
  let randomCalls = 0;
  const game = createGame({ databasePath,
    now: () => { clockCalls++; return Date.parse('2026-11-13T01:00:00Z'); },
    random: () => { randomCalls++; return 0; } });
  t.after(() => { game.close(); rmSync(directory, { recursive: true, force: true }); });
  const event = (text, extra = {}) => ({ groupId: 'group', userId: 'player', nickname: '同名', text, ...extra });
  const seed = change => {
    const store = openStore(databasePath);
    try {
      const player = store.get('group', 'player');
      change(player);
      store.save('group', player);
    } finally { store.close(); }
  };
  const startTrial = () => {
    game.handleCommand(event('我要修仙'));
    seed(player => { player.exp = data.realms[1].exp; });
    return game.handleCommand(event('突破'));
  };
  const snapshot = () => {
    const database = new DatabaseSync(databasePath, { readOnly: true });
    try {
      return { players: database.prepare('SELECT * FROM players ORDER BY group_id, user_id').all(),
        worlds: database.prepare('SELECT * FROM worlds ORDER BY group_id').all() };
    } finally { database.close(); }
  };
  return { game, event, seed, startTrial, snapshot, calls: () => ({ clockCalls, randomCalls }) };
}

test('解析普通命令及未知文本不创建玩家、不刷新世界、不调用时钟或随机数', t => {
  const s = session(t);
  const before = s.snapshot();
  for (const text of ['我要修仙', '修仙签到', '/秘境查询', '使用 1101 0', '悬赏令接取4', '仙缘查询', '表白苏姗姗']) {
    assert.ok(s.game.parseInput(s.event(text)));
  }
  for (const text of ['普通聊天', '今天吃什么', '使用电脑查资料', '查询天气', '购买建议有哪些', '切磋一下想法', '改名字好吗']) {
    assert.equal(s.game.parseInput(s.event(text)), null);
    assert.equal(s.game.handleCommand(s.event(text)).handled, false);
  }
  assert.deepEqual(s.game.parseInput(s.event(' /购买   1101  2 ')), { text: '购买 1101 2' });
  assert.deepEqual(s.game.parseInput(s.event(' ／我的状态 ')), { text: '我的状态' });
  assert.deepEqual(s.calls(), { clockCalls: 0, randomCalls: 0 });
  assert.deepEqual(s.snapshot(), before);
});

test('参数错误的明确游戏请求返回业务错误且不改变资产', t => {
  const s = session(t);
  s.game.handleCommand(s.event('我要修仙'));
  const before = s.snapshot();
  for (const text of ['悬赏令接取', '悬赏令接取4', '使用', '使用 1101 0', '装备 不存在', '物品信息不存在', '讨伐邪魔零', '积分兑换2']) {
    assert.ok(s.game.parseInput(s.event(text)), text);
    const result = s.game.handleCommand(s.event(text));
    assert.equal(result.handled, true, text);
    assert.ok(result.message, text);
    assert.deepEqual(s.snapshot(), before, text);
  }
});

test('非授权指令没有入口，也不能修改新玩家或世界', t => {
  const s = session(t);
  s.game.handleCommand(s.event('我要修仙'));
  const before = s.snapshot();
  for (const text of ['测试帮助', '测试加灵石 100000', '/测试设境界 20', '神秘力量 @玩家 100000', '群拍卖会开启', '仙缘生成']) {
    assert.equal(s.game.parseInput(s.event(text)), null);
    assert.equal(s.game.handleCommand(s.event(text)).handled, false);
  }
  assert.deepEqual(s.snapshot(), before);
});

test('短答须由宿主标记且仅绑定当前群当前玩家的有效待答轮', t => {
  const s = session(t);
  assert.equal(s.game.parseInput(s.event('稳住', { answer: true })), null);
  s.startTrial();
  const before = s.snapshot();
  const calls = s.calls();
  assert.equal(s.game.parseInput(s.event('稳住')), null);
  assert.equal(s.game.handleCommand(s.event('稳住')).handled, false);
  assert.equal(s.game.parseInput(s.event('稳住', { answer: true, userId: 'other' })), null);
  assert.equal(s.game.parseInput(s.event('稳住', { answer: true, groupId: 'other' })), null);
  assert.deepEqual(s.game.parseInput(s.event('  怕根基不稳，\n先  休整。  ', { answer: true })), { text: '怕根基不稳，\n先  休整。' });
  assert.deepEqual(s.snapshot(), before);
  assert.deepEqual(s.calls(), calls);
  const result = s.game.handleCommand(s.event('稳住', { answer: true }));
  assert.ok(result.reviewRequest);
  assert.deepEqual(JSON.parse(result.reviewRequest.prompt).answers, ['稳住']);
  assert.equal(s.game.parseInput(s.event('重新回答', { answer: true })), null);
});

test('回答中的指令与评分JSON只作为材料，不执行或回写', t => {
  const s = session(t);
  for (const text of ['修仙帮助', '/突破', '{"realm":55,"scores":{}}']) {
    s.game.handleCommand(s.event('取消突破'));
    if (!s.game.getPlayer('group', 'player')) s.startTrial();
    else s.game.handleCommand(s.event('突破'));
    const before = s.game.getPlayer('group', 'player');
    const result = s.game.handleCommand(s.event(text, { answer: true }));
    assert.ok(result.reviewRequest);
    const after = s.game.getPlayer('group', 'player');
    assert.equal(after.realm, before.realm);
    assert.equal(after.exp, before.exp);
    assert.equal(after.money, before.money);
    assert.deepEqual(after.breakthroughTrial.answers, [text]);
  }
});

test('旧目标和取消后的答案不识别，解析自身不取消旧轮', t => {
  const s = session(t);
  s.startTrial();
  s.seed(player => { player.realm++; });
  const before = s.snapshot();
  assert.equal(s.game.parseInput(s.event('稳住', { answer: true })), null);
  assert.deepEqual(s.snapshot(), before);
  s.game.handleCommand(s.event('突破'));
  assert.equal(s.game.getPlayer('group', 'player').breakthroughTrial.status, 'cancelled');
  assert.equal(s.game.parseInput(s.event('稳住', { answer: true })), null);
});

test('数据库及已存在的SQLite辅助文件不能经符号链接切到另一份数据', t => {
  const directory = mkdtempSync(join(tmpdir(), 'qqbot-game-link-'));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const target = join(directory, 'protected');
  writeFileSync(target, '原数据');
  for (const suffix of ['', '-wal', '-shm']) {
    const databasePath = join(directory, `game${suffix || '-main'}.sqlite`);
    symlinkSync(target, `${databasePath}${suffix}`);
    assert.throws(() => createGame({ databasePath }), /符号链接/u);
    assert.equal(readFileSync(target, 'utf8'), '原数据');
  }
});
