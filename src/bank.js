'use strict';

const { GameError, positiveInteger, requirePlayer, safeAdd, spend } = require('./rules');
const { recognizesBank } = require('./input');

const HOUR = 60 * 60 * 1000;
const LEVELS = [
  { name: '普通会员', cap: 1_000_000, upgrade: 200_000, rate: 0.002 },
  { name: '小会员', cap: 2_000_000, upgrade: 400_000, rate: 0.0021 },
  { name: '大会员', cap: 4_000_000, upgrade: 800_000, rate: 0.0022 },
  { name: '优质会员', cap: 8_000_000, upgrade: 1_600_000, rate: 0.0023 },
  { name: '黄金会员', cap: 16_000_000, upgrade: 3_200_000, rate: 0.0024 },
  { name: '钻石会员', cap: 32_000_000, upgrade: 6_400_000, rate: 0.0025 },
  { name: '终极会员', cap: 64_000_000, upgrade: 0, rate: 0.0028 }
];

const HELP = '灵庄：灵庄存入 数量、灵庄取出 数量、灵庄结算、灵庄信息、灵庄会员升级。存款按实际小时和会员利率结息；存取前自动结息。';

function ensureBank(player, now) {
  player.bank ??= { balance: 0, level: 1, lastSettledAt: now };
  return player.bank;
}

function settle(player, now) {
  const bank = ensureBank(player, now);
  const hours = Math.max(0, (now - bank.lastSettledAt) / HOUR);
  const interest = Math.floor(bank.balance * hours * LEVELS[bank.level - 1].rate);
  if (!Number.isSafeInteger(interest)) throw new GameError('本次利息超出安全整数范围。');
  player.money = safeAdd(player.money, interest, '灵石');
  bank.lastSettledAt = now;
  return { hours, interest };
}

function formatSettlement(result) {
  return `本次结息${result.hours.toFixed(2)}小时，获得${result.interest}灵石。`;
}

function handleBank(ctx) {
  if (!recognizesBank(ctx.text)) return null;
  if (ctx.text === '灵庄帮助') return HELP;
  requirePlayer(ctx.player);
  const bank = ensureBank(ctx.player, ctx.now);
  if (ctx.text === '灵庄信息') {
    const level = LEVELS[bank.level - 1];
    return `${ctx.player.name}的灵庄\n存款：${bank.balance}/${level.cap}灵石\n会员：${level.name}（每小时${(level.rate * 100).toFixed(2)}%）\n钱包：${ctx.player.money}灵石\n发送“灵庄结算”领取截至当前的利息。`;
  }
  if (ctx.text === '灵庄结算') return `${formatSettlement(settle(ctx.player, ctx.now))}当前钱包${ctx.player.money}灵石。`;
  if (ctx.text === '灵庄会员升级') {
    if (bank.level >= LEVELS.length) throw new GameError('已经是灵庄最高会员等级。');
    const result = settle(ctx.player, ctx.now);
    const current = LEVELS[bank.level - 1];
    spend(ctx.player, current.upgrade);
    bank.level++;
    const next = LEVELS[bank.level - 1];
    return `${formatSettlement(result)}消耗${current.upgrade}灵石，升级为${next.name}；存款上限${next.cap}，每小时利率${(next.rate * 100).toFixed(2)}%。`;
  }
  const match = ctx.text.match(/^灵庄(存入|取出)\s*(\d+)$/u);
  if (!match) throw new GameError('格式：灵庄存入 正整数数量，或灵庄取出 正整数数量。');
  const amount = positiveInteger(match[2], '金额');
  const result = settle(ctx.player, ctx.now);
  if (match[1] === '存入') {
    const level = LEVELS[bank.level - 1];
    if (bank.balance + amount > level.cap) throw new GameError(`${level.name}最多存${level.cap}灵石；当前已存${bank.balance}，还可存${level.cap - bank.balance}。`);
    spend(ctx.player, amount);
    bank.balance += amount;
    return `${formatSettlement(result)}存入${amount}灵石；存款${bank.balance}，钱包${ctx.player.money}。`;
  }
  if (bank.balance < amount) throw new GameError(`灵庄存款不足；当前${bank.balance}灵石。`);
  bank.balance -= amount;
  ctx.player.money = safeAdd(ctx.player.money, amount, '灵石');
  return `${formatSettlement(result)}取出${amount}灵石；存款${bank.balance}，钱包${ctx.player.money}。`;
}

module.exports = { handleBank, LEVELS };
