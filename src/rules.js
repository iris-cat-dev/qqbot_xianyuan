'use strict';

// 原版数据及规则：Copyright (c) 2023 Iris，授权见项目根目录 LICENSE。
const data = require('../data/data.json');
const herbs = require('../data/herbs.json');
const furnaces = require('../data/furnaces.json');
data.herbs = herbs;
data.furnaces = furnaces;

class GameError extends Error {}
function positiveInteger(input, label = '数量') {
  if (!/^\d+$/u.test(input)) throw new GameError(`${label}必须为正安全整数。`);
  const value = Number(input);
  if (!Number.isSafeInteger(value) || value < 1) throw new GameError(`${label}必须为正安全整数。`);
  return value;
}

function safeAdd(value, amount, label) {
  const sum = value + amount;
  if (!Number.isSafeInteger(sum) || sum < 0) throw new GameError(`${label}超出安全整数范围。`);
  return sum;
}

function safeMultiply(value, amount, label) {
  const product = value * amount;
  if (!Number.isSafeInteger(product) || product < 0) throw new GameError(`${label}超出安全整数范围。`);
  return product;
}


const MINUTE = 60_000;
const items = new Map();
for (const [collection, kind] of [
  [data.pills, 'pill'], [data.weapons, 'weapon'],
  [data.armor, 'armor'], [data.techniques, 'technique'], [data.skills, 'skill'],
  [data.supplies, 'supply'], [data.herbs, 'herb'], [data.furnaces, 'furnace']
]) {
  for (const [id, item] of Object.entries(collection)) items.set(id, { ...item, id, kind });
}

function integer(min, max, random) {
  return min + Math.floor(random() * (max - min + 1));
}

function pick(values, random) {
  return values[integer(0, values.length - 1, random)];
}

function dayKey(now) {
  return new Date(now).toLocaleDateString('en-CA', { timeZone: 'Asia/Shanghai' });
}
function refreshDaily(player, now) {
  const date = dayKey(now);
  if (player.daily?.date !== date) {
    player.daily = { date, refreshes: 0, pillUses: {}, sectTasks: 0, sectElixirClaimed: false, dualCultivations: 0 };
  } else {
    player.daily.refreshes ??= 0;
    player.daily.pillUses ??= {};
    player.daily.sectTasks ??= 0;
    player.daily.sectElixirClaimed ??= false;
    player.daily.dualCultivations ??= 0;
  }
  return player.daily;
}


function drawRoot(random) {
  let weight = integer(1, data.roots.reduce((sum, root) => sum + root.type_rate, 0), random);
  const root = data.roots.find(root => (weight -= root.type_rate) <= 0);
  let name;
  if (root.type_flag.length) {
    const pool = [...root.type_list];
    const attributes = [];
    const count = pick(root.type_flag, random);
    for (let i = 0; i < count; i++) attributes.push(pool.splice(integer(0, pool.length - 1, random), 1)[0]);
    name = `${attributes.join('、')}属性灵根`;
  } else {
    name = pick(root.type_list, random);
  }
  return { type: root.name, name, speed: root.type_speeds };
}

function stats(player) {
  const technique = items.get(player.equipment.technique);
  const weapon = items.get(player.equipment.weapon);
  const armor = items.get(player.equipment.armor);
  return {
    maxHp: Math.floor(player.exp * (1 + (technique?.hpbuff ?? 0))),
    maxMp: Math.floor(Math.floor(player.exp / 2) * (1 + (technique?.mpbuff ?? 0))),
    attack: Math.floor((Math.floor(player.exp / 10) + player.attackBonus) * (1 + (technique?.atkbuff ?? 0) + (weapon?.atk_buff ?? 0) + (player.attackPractice ?? 0) * 0.04)),
    crit: Math.min(101, Math.floor((weapon ? weapon.crit_buff : 0.01) * 100) + 1) / 101,
    defense: armor?.def_buff ?? 0,
    efficiency: player.root.speed * data.realms[player.realm].speed * (1 + (technique?.ratebuff ?? 0)),
    power: Math.floor(player.exp * player.root.speed * data.realms[player.realm].speed)
  };
}

function clampVitals(player) {
  const attributes = stats(player);
  player.hp = Math.min(player.hp, attributes.maxHp);
  player.mp = Math.min(player.mp, attributes.maxMp);
}

function addExp(player, amount) {
  const next = data.realms[player.realm + 1];
  const gain = next ? Math.min(amount, Math.max(0, Math.floor(next.exp * 1.5) - player.exp)) : amount;
  player.exp += gain;
  return gain;
}

function addItem(player, id, count = 1) {
  if (!items.has(id)) throw new Error(`未知内部物品：${id}`);
  player.inventory[id] = safeAdd(player.inventory[id] ?? 0, count, '物品数量');
}

function removeItem(player, id, count = 1) {
  if ((player.inventory[id] ?? 0) < count) throw new GameError(`背包中的${items.get(id).name}不足。`);
  player.inventory[id] -= count;
  if (player.inventory[id] === 0) delete player.inventory[id];
}

function findItem(input) {
  const item = items.get(input) ?? [...items.values()].find(item => item.name === input);
  if (!item) throw new GameError('没有这个物品，请使用背包或商店中的物品名 / ID。');
  return item;
}

function parseItemCount(input) {
  const match = input.trim().match(/^(\S+?)(?:\s+(\d+))?$/u);
  if (!match) throw new GameError('格式：物品名或ID [正整数数量]');
  const count = match[2] ? Number(match[2]) : 1;
  if (!Number.isSafeInteger(count) || count < 1) throw new GameError('数量必须为正整数。');
  return { item: findItem(match[1]), count };
}

function requirePlayer(player) {
  if (!player) throw new GameError('尚未踏入仙途，请先发送“我要修仙”。');
}

function requireIdle(player) {
  if (player.activity) throw new GameError(`当前正在${player.activity.label}，请先${player.activity.finishCommand}。`);
}

function requireHealthy(player) {
  if (player.hp <= player.exp / 10) throw new GameError('你已重伤，先闭关疗伤、出关或使用恢复丹药。');
}

function spend(player, amount) {
  if (player.money < amount) throw new GameError(`灵石不足，需要${amount}，现有${player.money}。`);
  player.money -= amount;
}

function remaining(until, now) {
  return Math.max(0, Math.ceil((until - now) / MINUTE));
}

function breakthroughRate(player) {
  return data.realms[player.realm].rate + Math.floor(player.breakthroughBonus + player.pillBonus);
}

// 前期时间压缩：只加快闭关修为，不影响战斗、悬赏、秘境等其他收益。
// 0～6：江湖好手～筑基圆满；7～12：结丹～元婴；13 起恢复原速。
function trainingBoost(player) {
  if (player.realm <= 6) return 4;
  if (player.realm <= 12) return 2;
  return 1;
}

function realmFamily(player) {
  return data.realms[player.realm].name.replace(/(?:初期|中期|圆满)$/u, '');
}

function playerRank(player) {
  return data.realms.length - player.realm;
}

module.exports = {
  data, items, GameError, MINUTE, positiveInteger, safeAdd, safeMultiply,
  integer, pick, dayKey, refreshDaily, drawRoot, stats, clampVitals, addExp,
  addItem, removeItem, findItem, parseItemCount, requirePlayer, requireIdle,
  requireHealthy, spend, remaining, breakthroughRate, trainingBoost,
  realmFamily, playerRank
};
