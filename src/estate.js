'use strict';

const {
  data, items, GameError, MINUTE, addItem, integer, playerRank,
  requirePlayer, safeAdd, spend
} = require('./rules');
const { recognizesEstate } = require('./input');

const ESTATE_PRICE = 500_000;
const GARDEN_COSTS = [1_000_000, 2_000_000, 4_000_000, 8_000_000, 16_000_000, 32_000_000, 64_000_000, 128_000_000, 256_000_000];
const MINE_COSTS = [500_000, 1_000_000, 2_000_000, 4_000_000, 8_000_000, 16_000_000];
const GARDEN_INTERVAL = 4 * 60 * MINUTE;
const MINE_INTERVAL = 57 * MINUTE;
const HELP = '洞天福地：洞天福地购买、我的洞天福地、洞天福地改名 名字；灵田开垦/灵田收取（4小时）；灵矿开垦/灵矿收取（57分钟）。灵田产药材，灵矿每块产20000灵石。';

function requireEstate(player) {
  if (!player.estate) throw new GameError('尚无洞天福地，请先发送“洞天福地购买”。');
  return player.estate;
}

function remainingMinutes(at, now) {
  return Math.max(0, Math.ceil((at - now) / MINUTE));
}

function handleEstate(ctx) {
  if (!recognizesEstate(ctx.text)) return null;
  if (ctx.text === '洞天福地帮助' || ctx.text === '灵田帮助' || ctx.text === '灵矿帮助') return HELP;
  requirePlayer(ctx.player);
  if (ctx.text === '洞天福地购买') {
    if (ctx.player.estate) throw new GameError('已经拥有洞天福地。');
    spend(ctx.player, ESTATE_PRICE);
    ctx.player.estate = { name: null, gardenPlots: 1, gardenAt: ctx.now, minePlots: 0, mineAt: ctx.now };
    return `消耗${ESTATE_PRICE}灵石购得洞天福地，初始拥有1块灵田。4小时后可“灵田收取”；可继续开垦灵田和灵矿。`;
  }
  const estate = requireEstate(ctx.player);
  if (ctx.text === '我的洞天福地') {
    const gardenReady = Math.max(0, remainingMinutes(estate.gardenAt + GARDEN_INTERVAL, ctx.now));
    const mineReady = estate.minePlots ? Math.max(0, remainingMinutes(estate.mineAt + MINE_INTERVAL, ctx.now)) : null;
    return `${ctx.player.name}的洞天福地：${estate.name ?? '尚未命名'}\n灵田：${estate.gardenPlots}/10块，${gardenReady ? `${gardenReady}分钟后可收取` : '现在可收取'}\n灵矿：${estate.minePlots}/6块，${mineReady === null ? '尚未开垦' : mineReady ? `${mineReady}分钟后可收取` : '现在可收取'}\n药材收取等级：${ctx.player.alchemy.collectionLevel}。`;
  }
  if (ctx.text.startsWith('洞天福地改名')) {
    const name = ctx.text.slice('洞天福地改名'.length).trim();
    if (!name || Array.from(name).length > 9) throw new GameError('洞天福地名字须为1～9个字符。');
    estate.name = name;
    return `洞天福地已改名为：${name}。`;
  }
  if (ctx.text === '灵田开垦') {
    if (estate.gardenPlots >= 10) throw new GameError('十块灵田已全部开垦。');
    const cost = GARDEN_COSTS[estate.gardenPlots - 1];
    spend(ctx.player, cost);
    estate.gardenPlots++;
    return `消耗${cost}灵石，开垦第${estate.gardenPlots}块灵田。`;
  }
  if (ctx.text === '灵田收取') {
    const readyAt = estate.gardenAt + GARDEN_INTERVAL;
    if (ctx.now < readyAt) throw new GameError(`灵田还需${remainingMinutes(readyAt, ctx.now)}分钟成熟。`);
    const rank = playerRank(ctx.player);
    let pool = Object.entries(data.herbs).filter(([, herb]) => herb.rank >= rank && herb.rank - rank <= 6).map(([id]) => id);
    if (!pool.length) pool = ['3001'];
    const count = estate.gardenPlots + ctx.player.alchemy.collectionLevel;
    const harvest = {};
    for (let i = 0; i < count; i++) {
      const id = pool[integer(0, pool.length - 1, ctx.random)];
      addItem(ctx.player, id);
      harvest[id] = (harvest[id] ?? 0) + 1;
    }
    estate.gardenAt = ctx.now;
    return `灵田收获${count}株药材：${Object.entries(harvest).map(([id, amount]) => `${items.get(id).name}×${amount}`).join('、')}。`;
  }
  if (ctx.text === '灵矿开垦') {
    if (estate.minePlots >= MINE_COSTS.length) throw new GameError('六块灵矿已全部开垦。');
    const cost = MINE_COSTS[estate.minePlots];
    spend(ctx.player, cost);
    estate.minePlots++;
    if (estate.minePlots === 1) estate.mineAt = ctx.now;
    return `消耗${cost}灵石，开垦第${estate.minePlots}块灵矿；57分钟后可收取。`;
  }
  if (estate.minePlots < 1) throw new GameError('尚未开垦灵矿，请先发送“灵矿开垦”。');
  const readyAt = estate.mineAt + MINE_INTERVAL;
  if (ctx.now < readyAt) throw new GameError(`采矿队伍还需${remainingMinutes(readyAt, ctx.now)}分钟归来。`);
  const amount = estate.minePlots * 20_000;
  ctx.player.money = safeAdd(ctx.player.money, amount, '灵石');
  estate.mineAt = ctx.now;
  return `灵矿收获${amount}灵石（${estate.minePlots}块×20000），当前钱包${ctx.player.money}。`;
}

module.exports = { handleEstate, ESTATE_PRICE, GARDEN_COSTS, MINE_COSTS };
