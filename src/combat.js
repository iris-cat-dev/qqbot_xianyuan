'use strict';

// 原版 common/player_fight.py：普攻波动、会心、技能消耗及四类神通。
const { items, stats, integer } = require('./rules');
const MAX_ROUNDS = 300;

function playerFighter(player) {
  const attributes = stats(player);
  return {
    name: player.name, exp: player.exp,
    hp: Math.max(0, Math.min(player.hp, attributes.maxHp)),
    mp: Math.max(0, Math.min(player.mp, attributes.maxMp)),
    maxHp: attributes.maxHp, maxMp: attributes.maxMp,
    attack: attributes.attack, crit: attributes.crit, defense: attributes.defense,
    skill: player.equipment.skill ? items.get(player.equipment.skill) : null
  };
}

function bossFighter(boss, defense = 0) {
  return {
    name: boss.name, exp: 0, hp: boss.hp, mp: boss.mp,
    maxHp: boss.maxHp, maxMp: boss.mp,
    attack: boss.attack, crit: 31 / 101, defense, skill: null
  };
}

function ordinaryAttack(actor, bonus, random) {
  const variation = Math.round((0.95 + random() * 0.1) * 100) / 100;
  let damage = Math.floor(variation * actor.attack * (1 + bonus));
  const critical = random() < actor.crit;
  if (critical) {
    damage = Math.floor(damage * 1.5);
    actor.criticals++;
  }
  return { damage, critical };
}

function dealDamage(actor, target, raw) {
  const base = Math.round((1 - target.defense) * 100) / 100;
  const multiplier = target.effect?.kind === 'defense'
    ? Math.max(0.1, base - target.effect.value) : base;
  // 无神通的普攻也减伤；奖励只统计实际扣血，不计过量伤害。
  const damage = Math.min(target.hp, Math.max(0, Math.floor(raw * multiplier)));
  target.hp -= damage;
  actor.damageDealt += damage;
  return damage;
}

function attackMessage(actor, target, attack, prefix = '') {
  const damage = dealDamage(actor, target, attack.damage);
  return `${actor.name}${prefix}${attack.critical ? '会心' : '普攻'}${damage}`;
}

function takeTurn(actor, target, random) {
  // 增益在最后一个有效回合的对手行动后才失效。
  if (actor.effect?.remaining === 0) actor.effect = null;
  if (actor.sealed > 0) {
    actor.sealed--;
    if (actor.rest > 0) actor.rest--;
    if (actor.effect) actor.effect.remaining--;
    return `${actor.name}被封印（剩${actor.sealed}回合）`;
  }
  if (actor.rest > 0) {
    actor.rest--;
    return `${actor.name}休息（剩${actor.rest}回合）`;
  }

  if (actor.effect) {
    const effect = actor.effect;
    effect.remaining--;
    const attack = ordinaryAttack(actor, effect.kind === 'attack' ? effect.value : 0, random);
    if (effect.kind === 'dot') {
      const damage = dealDamage(actor, target, effect.damage + attack.damage);
      return `${actor.name}持续${effect.name}+${attack.critical ? '会心' : '普攻'}${damage}`;
    }
    return attackMessage(actor, target, attack, effect.kind === 'seal' ? '' : `${effect.name}·`);
  }

  const skill = actor.skill;
  if (skill) {
    const hpCost = Math.floor(skill.hpcost * actor.hp);
    const mpCost = Math.floor(skill.mpcost * actor.exp);
    if (actor.hp > hpCost && actor.mp >= mpCost && integer(0, 100, random) <= skill.rate) {
      actor.hp -= hpCost;
      actor.mp -= mpCost;
      actor.casts++;
      const prefix = `${actor.name}施展${skill.name}（耗血${hpCost}/元${mpCost}）`;
      switch (skill.skill_type) {
        case 1: {
          const attack = ordinaryAttack(actor, 0, random);
          let raw = 0;
          for (const value of skill.atkvalue) raw += Math.floor(value * attack.damage);
          actor.rest = skill.turncost;
          const damage = dealDamage(actor, target, raw);
          return `${prefix}${attack.critical ? '会心' : ''}${skill.atkvalue.length}连击${damage}${actor.rest ? `，休息${actor.rest}回合` : ''}`;
        }
        case 2: {
          const raw = Math.floor(skill.atkvalue * actor.attack);
          // 原版首轮只DOT，随后turncost轮DOT+普攻；DOT本身不暴击。
          actor.effect = { kind: 'dot', name: skill.name, damage: raw, remaining: skill.turncost };
          return `${prefix}持续伤害${dealDamage(actor, target, raw)}`;
        }
        case 3: {
          const kind = skill.bufftype === 1 ? 'attack' : 'defense';
          actor.effect = { kind, name: skill.name, value: skill.buffvalue, remaining: skill.turncost };
          const attack = ordinaryAttack(actor, kind === 'attack' ? skill.buffvalue : 0, random);
          const damage = dealDamage(actor, target, attack.damage);
          return `${prefix}${kind === 'attack' ? '增攻' : '减伤'}${Math.round(skill.buffvalue * 100)}%，${attack.critical ? '会心' : '普攻'}${damage}`;
        }
        case 4: {
          const success = integer(0, 100, random) <= skill.success;
          actor.effect = { kind: 'seal', remaining: skill.turncost };
          if (success) target.sealed = skill.turncost;
          return `${prefix}${success ? `封印${target.name}${skill.turncost}回合` : '封印被躲开'}`;
        }
        default:
          throw new Error(`未知神通类型：${skill.skill_type}`);
      }
    }
  }
  return attackMessage(actor, target, ordinaryAttack(actor, 0, random));
}

// 输入为独立属性快照；函数不修改玩家、Boss或传入快照。winner以位置表示，重名不会误判。
function fight(attacker, defender, random) {
  const left = { ...attacker, effect: null, rest: 0, sealed: 0, damageDealt: 0, casts: 0, criticals: 0 };
  const right = { ...defender, effect: null, rest: 0, sealed: 0, damageDealt: 0, casts: 0, criticals: 0 };
  const first = [];
  const last = [];
  let rounds = 0;
  while (left.hp > 0 && right.hp > 0 && rounds < MAX_ROUNDS) {
    rounds++;
    let action = takeTurn(left, right, random);
    if (right.hp > 0) action += `；${takeTurn(right, left, random)}`;
    const line = `第${rounds}回合 ${action}｜血${left.hp}/${right.hp}`;
    if (rounds <= 3) first.push(line);
    else {
      last.push(line);
      if (last.length > 3) last.shift();
    }
  }
  const winner = left.hp <= 0 && right.hp <= 0 ? null : left.hp <= 0 ? 'defender' : right.hp <= 0 ? 'attacker' : null;
  const lines = [...first];
  if (rounds > 6) lines.push(`……省略${rounds - 6}个实际回合……`);
  lines.push(...last);
  lines.push(winner === null ? `${rounds}回合未分胜负，平局。` : `${winner === 'attacker' ? left.name : right.name}获胜，共${rounds}回合。`);
  lines.push(`${left.name}：气血${left.hp}、真元${left.mp}、实际伤害${left.damageDealt}、施法${left.casts}次；${right.name}：气血${right.hp}、真元${right.mp}、实际伤害${right.damageDealt}、施法${right.casts}次。`);
  return { winner, rounds, attacker: left, defender: right, report: lines.join('\n') };
}

module.exports = { playerFighter, bossFighter, fight, MAX_ROUNDS };
