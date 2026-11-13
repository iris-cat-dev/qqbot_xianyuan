'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { fight, playerFighter, MAX_ROUNDS } = require('../src/combat');
const { items } = require('../src/rules');

function fighter(overrides = {}) {
  return {
    name: '同名道友', exp: 1000, hp: 1000, mp: 0, maxHp: 1000, maxMp: 500,
    attack: 100, crit: 0, defense: 0, skill: null, ...overrides
  };
}

function sequence(values, fallback = 0.5) {
  let index = 0;
  return () => index < values.length ? values[index++] : fallback;
}

function skill(id, overrides = {}) { return { ...items.get(id), ...overrides }; }

const steady = () => 0.5;

test('玩家战斗属性包含装备加成、真元气血裁剪且不修改存档', () => {
  const player = {
    name: '甲', realm: 0, exp: 1000, hp: 9000, mp: -1, attackBonus: 10,
    root: { speed: 1 }, equipment: { weapon: '7001', armor: '6001', technique: null, skill: '8001' }
  };
  const before = structuredClone(player);
  const actual = playerFighter(player);
  assert.equal(actual.hp, 1000);
  assert.equal(actual.mp, 0);
  assert.equal(actual.attack, Math.floor(110 * 1.08));
  assert.equal(actual.crit, 1 / 101);
  assert.equal(actual.defense, 0.08);
  assert.equal(actual.skill.id, '8001');
  assert.deepEqual(player, before);
  player.equipment = { weapon: null, armor: null, technique: null, skill: null };
  player.hp = -1;
  player.mp = 9000;
  const naked = playerFighter(player);
  assert.equal(naked.hp, 0);
  assert.equal(naked.mp, 500);
  assert.equal(naked.skill, null);
  assert.equal(naked.crit, 2 / 101);
});

test('普攻也减伤且只记录实际扣血，重名的胜负以位置判定', () => {
  const left = fighter();
  const right = fighter({ hp: 75, attack: 0, defense: 0.5 });
  const original = structuredClone([left, right]);
  const result = fight(left, right, steady);
  assert.equal(result.winner, 'attacker');
  assert.equal(result.rounds, 2);
  assert.equal(result.attacker.damageDealt, 75);
  assert.equal(result.defender.hp, 0);
  assert.equal(result.attacker.hp, 1000);
  assert.deepEqual([left, right], original);
  const reversed = fight(fighter({ attack: 0, hp: 50 }), fighter(), steady);
  assert.equal(reversed.winner, 'defender');
  assert.equal(reversed.defender.damageDealt, 50);
});

test('会心采用严格小于边界，波动与会心取整之后再计算减伤', () => {
  const critical = fight(fighter({ crit: 0.5 }), fighter({ hp: 100, attack: 0 }), sequence([0, 0.499999]));
  assert.equal(critical.rounds, 1);
  assert.equal(critical.attacker.criticals, 1);
  assert.equal(critical.attacker.damageDealt, 100);
  const boundary = fight(fighter({ crit: 0.5 }), fighter({ hp: 100, attack: 0 }), sequence([0, 0.5]));
  assert.equal(boundary.rounds, 2);
  assert.equal(boundary.attacker.criticals, 0);
  const high = fight(fighter({ attack: 101, crit: 1 }), fighter({ hp: 200, attack: 0, defense: 0.333 }), sequence([0.999999, 0]));
  assert.equal(high.attacker.damageDealt, 200);
  assert.equal(high.rounds, 2);
});

test('连击消耗当前气血和修为比例真元，休息完整一轮后恢复普攻', () => {
  const left = fighter({ mp: 300, skill: skill('8001') });
  const right = fighter({ hp: 407, attack: 0 });
  const before = structuredClone([left, right]);
  const result = fight(left, right, steady);
  assert.equal(result.rounds, 4);
  assert.equal(result.attacker.casts, 1);
  assert.equal(result.attacker.hp, 900);
  assert.equal(result.attacker.mp, 0);
  assert.equal(result.attacker.rest, 0);
  assert.equal(result.attacker.damageDealt, 407);
  assert.deepEqual([left, right], before);
});

test('真元不足、支付会致死或释放概率失败均回退普攻且不扣资源', () => {
  for (const overrides of [
    { mp: 299, skill: skill('8001') },
    { hp: 100, mp: 300, skill: skill('8001', { hpcost: 1 }) },
    { mp: 300, skill: skill('8002', { rate: 49 }) }
  ]) {
    const input = fighter(overrides);
    const result = fight(input, fighter({ hp: 100, attack: 0 }), steady);
    assert.equal(result.attacker.casts, 0);
    assert.equal(result.attacker.hp, input.hp);
    assert.equal(result.attacker.mp, input.mp);
    assert.equal(result.rounds, 1);
  }
  const boundary = fight(fighter({ mp: 300, skill: skill('8002') }), fighter({ hp: 240, attack: 0 }), steady);
  assert.equal(boundary.attacker.casts, 1);
  assert.equal(boundary.attacker.mp, 0);
  assert.equal(boundary.rounds, 1);
});

test('DOT首轮不普攻或会心，后续三轮叠加普攻，到期后清除', () => {
  const plain = fight(fighter({ mp: 300, skill: skill('8003') }), fighter({ hp: 741, attack: 0 }), steady);
  assert.equal(plain.rounds, 6);
  assert.equal(plain.attacker.casts, 1);
  assert.equal(plain.attacker.damageDealt, 741);
  assert.equal(plain.attacker.effect, null);
  const critical = fight(fighter({ mp: 300, crit: 1, skill: skill('8003') }), fighter({ hp: 760, attack: 0 }), steady);
  assert.equal(critical.rounds, 4);
  assert.equal(critical.attacker.criticals, 3);
  assert.equal(critical.attacker.damageDealt, 760);
  assert.equal(critical.attacker.effect.remaining, 0);
});

test('攻击增益覆盖施展及后三轮，到期后的普攻不再增幅', () => {
  const result = fight(fighter({ mp: 300, skill: skill('8004') }), fighter({ hp: 533, attack: 0 }), steady);
  assert.equal(result.rounds, 6);
  assert.equal(result.attacker.casts, 1);
  assert.equal(result.attacker.effect, null);
  assert.equal(result.attacker.damageDealt, 533);
});

test('防御增益最后有效轮仍承伤减免，到期恢复原防御并保留最低承伤倍率', () => {
  const result = fight(fighter({ mp: 300, skill: skill('8005') }), fighter({ hp: 650 }), steady);
  assert.equal(result.rounds, 7);
  assert.equal(result.attacker.hp, 432);
  assert.equal(result.defender.damageDealt, 568);
  assert.equal(result.attacker.effect, null);
  const floor = fight(fighter({ mp: 300, defense: 0.32, skill: skill('8905') }), fighter({ hp: 650 }), steady);
  assert.equal(floor.rounds, 7);
  assert.equal(floor.attacker.hp, 882);
  assert.equal(floor.defender.damageDealt, 118);
});

test('封印成功边界阻止四轮行动且解除后对方可以释放神通', () => {
  const result = fight(
    fighter({ mp: 300, skill: skill('8906', { success: 50 }) }),
    fighter({ attack: 0, mp: 300, skill: skill('8001') }), steady
  );
  assert.equal(result.winner, 'attacker');
  assert.equal(result.rounds, 11);
  assert.equal(result.attacker.casts, 1);
  assert.equal(result.defender.casts, 1);
  assert.equal(result.attacker.damageDealt, 940);
  assert.equal(result.defender.sealed, 0);
  assert.equal(result.attacker.effect, null);
});

test('封印失败仍扣真元和使用技能但不阻止对方行动', () => {
  const result = fight(
    fighter({ mp: 300, skill: skill('8906', { success: 50 }) }),
    fighter({ hp: 401, attack: 100 }), sequence([0.5, 51.5 / 101])
  );
  assert.equal(result.rounds, 6);
  assert.equal(result.attacker.mp, 0);
  assert.equal(result.attacker.casts, 1);
  assert.equal(result.attacker.hp, 500);
  assert.equal(result.defender.damageDealt, 500);
  assert.equal(result.defender.sealed, 0);
});

test('封印期间休息与增益计时也推进，解除时不延长已经耗尽的增益', () => {
  const seal = skill('8906', { rate: 100 });
  const resting = fight(fighter({ mp: 300, skill: skill('8001') }), fighter({ hp: 407, mp: 300, skill: seal }), steady);
  assert.equal(resting.rounds, 7);
  assert.equal(resting.attacker.hp, 400);
  assert.equal(resting.attacker.rest, 0);
  assert.equal(resting.attacker.sealed, 0);
  const buffed = fight(fighter({ mp: 300, skill: skill('8004') }), fighter({ hp: 209, mp: 300, skill: seal }), steady);
  assert.equal(buffed.rounds, 7);
  assert.equal(buffed.attacker.damageDealt, 209);
  assert.equal(buffed.attacker.effect, null);
  assert.equal(buffed.attacker.hp, 500);
});

test('300轮无伤害平局和开战前已经倒地都正确终止', () => {
  const draw = fight(fighter({ attack: 0 }), fighter({ attack: 0 }), steady);
  assert.equal(MAX_ROUNDS, 300);
  assert.equal(draw.rounds, 300);
  assert.equal(draw.winner, null);
  assert.equal(draw.attacker.hp, 1000);
  assert.equal(draw.defender.hp, 1000);
  assert.equal(draw.attacker.damageDealt + draw.defender.damageDealt, 0);
  assert.equal(fight(fighter({ hp: 0 }), fighter(), steady).winner, 'defender');
  assert.equal(fight(fighter(), fighter({ hp: 0 }), steady).winner, 'attacker');
  const both = fight(fighter({ hp: 0 }), fighter({ hp: 0 }), steady);
  assert.equal(both.winner, null);
  assert.equal(both.rounds, 0);
});
