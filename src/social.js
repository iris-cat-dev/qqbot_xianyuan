'use strict';

const {
  GameError, MINUTE, addExp, addItem, clampVitals, findItem, integer,
  positiveInteger, refreshDaily, removeItem, requireHealthy, requirePlayer,
  safeAdd, safeMultiply, spend
} = require('./rules');
const { playerFighter, fight } = require('./combat');
const { recognizesSocial } = require('./input');

const STEAL_PENALTY = 100_000;
const STEAL_COOLDOWN = 10 * MINUTE;
const POSITION_EXP_CAPS = [20_000_000, 10_000_000, 7_000_000, 5_000_000, 3_000_000];
const FORBIDDEN_GIFTS = new Set(['pill', 'furnace', 'supply']);

function targetPlayer(ctx, action) {
  if (!ctx.targetId) throw new GameError(`${action}需要明确@一位本群修士。`);
  if (ctx.targetId === ctx.userId) throw new GameError(`不能对自己${action}。`);
  const target = ctx.store.get(ctx.groupId, ctx.targetId);
  if (!target) throw new GameError('目标尚未在本群踏入仙途。');
  return target;
}

function gift(ctx) {
  const target = targetPlayer(ctx, '赠送');
  const match = ctx.text.match(/^赠送\s+(?:@\S+\s+)?(\S+)\s+(\d+)$/u);
  if (!match) throw new GameError('格式：赠送 @对象 物品名/ID 正整数数量。');
  const item = findItem(match[1]);
  const count = positiveInteger(match[2]);
  if (FORBIDDEN_GIFTS.has(item.kind)) throw new GameError(`${item.name}属于不可赠送的特殊物品；可通过坊市交易普通丹药。`);
  if ((ctx.player.inventory[item.id] ?? 0) < count) throw new GameError(`背包中的${item.name}不足，需要${count}件。`);
  const equipped = (item.kind === 'weapon' || item.kind === 'armor') && ctx.player.equipment[item.kind] === item.id;
  if (equipped && ctx.player.inventory[item.id] - count < 1) throw new GameError('正在装备的物品须保留1件，或先卸下。');
  const fee = safeMultiply(500, count, '寄送费用');
  spend(ctx.player, fee);
  addItem(target, item.id, count);
  removeItem(ctx.player, item.id, count);
  ctx.store.save(ctx.groupId, target);
  return `向${target.name}赠送${item.name}×${count}，支付驿站费${fee}灵石。`;
}

function steal(ctx) {
  const target = targetPlayer(ctx, '偷灵石');
  const readyAt = (ctx.player.lastStealAt ?? 0) + STEAL_COOLDOWN;
  if (ctx.now < readyAt) throw new GameError(`偷灵石冷却中，还需${Math.ceil((readyAt - ctx.now) / MINUTE)}分钟。`);
  if (ctx.player.money < STEAL_PENALTY) throw new GameError(`至少准备${STEAL_PENALTY}灵石赔款，盗门才肯出手。`);
  ctx.player.lastStealAt = ctx.now;
  if (integer(0, 100, ctx.random) <= 50) {
    const percent = integer(1, 20, ctx.random);
    const amount = Math.floor(target.money * percent / 100);
    target.money -= amount;
    ctx.player.money = safeAdd(ctx.player.money, amount, '灵石');
    ctx.store.save(ctx.groupId, target);
    return `盗门得手，从${target.name}处偷得${amount}灵石（其钱包的${percent}%）。`;
  }
  spend(ctx.player, STEAL_PENALTY);
  target.money = safeAdd(target.money, STEAL_PENALTY, '目标灵石');
  ctx.store.save(ctx.groupId, target);
  return `偷窃失手，向${target.name}赔偿${STEAL_PENALTY}灵石。`;
}

function robbery(ctx) {
  const target = targetPlayer(ctx, '打劫');
  requireHealthy(ctx.player);
  requireHealthy(target);
  const result = fight(playerFighter(ctx.player), playerFighter(target), ctx.random);
  ctx.player.hp = Math.max(1, result.attacker.hp);
  ctx.player.mp = Math.max(0, result.attacker.mp);
  target.hp = Math.max(1, result.defender.hp);
  target.mp = Math.max(0, result.defender.mp);
  let settlement = '战至力竭仍未分胜负，没有资产与修为转移。';
  if (result.winner === 'attacker') {
    const money = Math.floor(target.money * 0.1);
    target.money -= money;
    ctx.player.money = safeAdd(ctx.player.money, money, '灵石');
    const requested = Math.floor(target.exp * 0.005);
    const gain = addExp(ctx.player, requested);
    const loss = Math.min(target.exp - 1, Math.floor(requested / 2));
    target.exp -= loss;
    settlement = `${ctx.player.name}获胜，夺得${money}灵石、增加${gain}修为；${target.name}损失${loss}修为。`;
  } else if (result.winner === 'defender') {
    const money = Math.floor(ctx.player.money * 0.1);
    ctx.player.money -= money;
    target.money = safeAdd(target.money, money, '目标灵石');
    const loss = Math.min(ctx.player.exp - 1, Math.floor(ctx.player.exp * 0.005));
    ctx.player.exp -= loss;
    const gain = addExp(target, Math.floor(loss / 2));
    settlement = `${target.name}反杀，夺得${money}灵石、增加${gain}修为；${ctx.player.name}损失${loss}修为。`;
  }
  clampVitals(ctx.player);
  clampVitals(target);
  ctx.store.save(ctx.groupId, target);
  return `打劫：${ctx.player.name}先手对阵${target.name}\n${result.report}\n${settlement}`;
}

function dualCultivation(ctx) {
  const target = targetPlayer(ctx, '双修');
  refreshDaily(target, ctx.now);
  if (target.exp > ctx.player.exp) throw new GameError('对方修为高于你，不愿与你双修。');
  if (ctx.player.daily.dualCultivations >= 3) throw new GameError('你今日双修次数已达3次。');
  if (target.daily.dualCultivations >= 3) throw new GameError('对方今日双修次数已达3次。');
  const base = Math.floor((ctx.player.exp + target.exp) * 0.0055);
  const ownCap = POSITION_EXP_CAPS[ctx.player.sectPosition ?? 4];
  const targetCap = POSITION_EXP_CAPS[target.sectPosition ?? 4];
  const ownGain = addExp(ctx.player, Math.min(base, ownCap));
  const targetGain = addExp(target, Math.min(base, targetCap));
  ctx.player.daily.dualCultivations++;
  target.daily.dualCultivations++;
  const lucky = new Set([10, 13, 14, 52, 66]).has(integer(1, 100, ctx.random));
  if (lucky) {
    ctx.player.breakthroughBonus = safeAdd(ctx.player.breakthroughBonus, 2, '突破增益');
    target.breakthroughBonus = safeAdd(target.breakthroughBonus, 2, '目标突破增益');
  }
  ctx.store.save(ctx.groupId, target);
  return `${ctx.player.name}与${target.name}双修，各获修为${ownGain}/${targetGain}。${lucky ? '双方各增加2个百分点永久突破积累。' : ''}今日双方已用次数${ctx.player.daily.dualCultivations}/3、${target.daily.dualCultivations}/3。`;
}

function handleSocial(ctx) {
  if (!recognizesSocial(ctx.text)) return null;
  requirePlayer(ctx.player);
  if (ctx.text === '我的双修次数') return `今日剩余双修次数：${Math.max(0, 3 - ctx.player.daily.dualCultivations)}次。`;
  if (ctx.text.startsWith('赠送')) return gift(ctx);
  if (ctx.text.startsWith('偷灵石')) return steal(ctx);
  if (ctx.text.startsWith('打劫')) return robbery(ctx);
  return dualCultivation(ctx);
}

module.exports = { handleSocial };
