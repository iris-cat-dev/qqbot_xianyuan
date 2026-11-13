'use strict';

const {
  items, GameError, addItem, integer, positiveInteger, requirePlayer,
  safeAdd, spend
} = require('./rules');
const { recognizesAuction } = require('./input');
const auctionData = require('../data/auction-data.json');

const DURATION = 120_000;
const EXTENSION = 10_000;
const GOODS = Object.values(auctionData.auctions).map(good => ({ itemId: String(good.id), startPrice: good.start_price }))
  .filter(good => items.has(good.itemId));

function settleExpired(ctx) {
  const auction = ctx.world.auction;
  if (!auction || ctx.now < auction.endsAt) return null;
  ctx.world.auction = null;
  if (!auction.bidderId) return `上一场交友会流拍：${items.get(auction.itemId).name}无人出价。`;
  const winner = auction.bidderId === ctx.userId ? ctx.player : ctx.store.get(ctx.groupId, auction.bidderId);
  if (!winner) throw new Error(`交友会竞得者存档缺失：${auction.bidderId}`);
  addItem(winner, auction.itemId);
  if (winner !== ctx.player) ctx.store.save(ctx.groupId, winner);
  return `上一场交友会结算：${winner.name}以${auction.currentPrice}灵石竞得${items.get(auction.itemId).name}；竞价款已从托管划转。`;
}

function auctionStatus(auction, now) {
  const item = items.get(auction.itemId);
  const remaining = Math.max(0, Math.ceil((auction.endsAt - now) / 1000));
  return `本群交友会：${item.name} [${item.id}]\n当前价：${auction.currentPrice}灵石${auction.bidderId ? `，领先者${auction.bidderName}` : '，尚无人出价'}\n剩余${remaining}秒；每次有效出价延长10秒，最低加价5%。`;
}

function bid(ctx) {
  const auction = ctx.world.auction;
  if (!auction) throw new GameError('本群当前没有交友会，发送“举行交友会”开启。');
  const match = ctx.text.match(/^出价\s*(\d+)$/u);
  if (!match) throw new GameError('格式：出价 正整数总价。');
  const price = positiveInteger(match[1], '出价');
  const minimum = safeAdd(auction.currentPrice, Math.max(1, Math.floor(auction.currentPrice * 0.05)), '最低出价');
  if (price < minimum) throw new GameError(`本次至少出价${minimum}灵石（当前价${auction.currentPrice}，最低加价5%）。`);
  if (auction.bidderId === ctx.userId) {
    spend(ctx.player, price - auction.currentPrice);
  } else {
    spend(ctx.player, price);
    if (auction.bidderId) {
      const previous = ctx.store.get(ctx.groupId, auction.bidderId);
      if (!previous) throw new Error(`交友会上一竞价者存档缺失：${auction.bidderId}`);
      previous.money = safeAdd(previous.money, auction.currentPrice, '退款灵石');
      ctx.store.save(ctx.groupId, previous);
    }
  }
  auction.currentPrice = price;
  auction.bidderId = ctx.userId;
  auction.bidderName = ctx.player.name;
  auction.endsAt = safeAdd(auction.endsAt, EXTENSION, '交友会结束时间');
  return `${ctx.player.name}出价${price}灵石，竞价款已托管；交友会延长10秒。\n${auctionStatus(auction, ctx.now)}`;
}

function handleAuction(ctx) {
  if (!recognizesAuction(ctx.text)) return null;
  requirePlayer(ctx.player);
  const settlement = settleExpired(ctx);
  if (ctx.text === '交友会查询') return settlement ?? (ctx.world.auction ? auctionStatus(ctx.world.auction, ctx.now) : '本群当前没有交友会，发送“举行交友会”开启。');
  if (ctx.text.startsWith('出价')) return settlement ?? bid(ctx);
  if (ctx.world.auction) throw new GameError(`本群已有进行中的交友会。\n${auctionStatus(ctx.world.auction, ctx.now)}`);
  if (!GOODS.length) throw new Error('交友会商品配置为空。');
  const good = GOODS[integer(0, GOODS.length - 1, ctx.random)];
  ctx.world.auction = {
    itemId: good.itemId, currentPrice: good.startPrice, bidderId: null,
    bidderName: null, startedAt: ctx.now, endsAt: ctx.now + DURATION
  };
  return `${settlement ? `${settlement}\n` : ''}交友会开启！\n${auctionStatus(ctx.world.auction, ctx.now)}\n发送“出价 总价”；出价立刻托管，落后时全额退回。`;
}

module.exports = { handleAuction };
