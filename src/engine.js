'use strict';

const { openStore } = require('./store');
const { GameError, refreshDaily } = require('./rules');
const { handleProgression } = require('./progression');
const { handleMission } = require('./mission');
const { handleInventory } = require('./inventory');
const { handleEncounters, resolveRiftReview } = require('./encounters');
const { handleBreakthrough, resolveBreakthroughReview } = require('./breakthrough');
const { handleBank } = require('./bank');
const { handleEstate } = require('./estate');
const { handleAlchemy } = require('./alchemy');
const { handleSocial } = require('./social');
const { handleSect } = require('./sect');
const { handleAuction } = require('./auction');
const { handleMap } = require('./map');
const { handleRomance } = require('./romance');
const { InvalidReviewError } = require('./review');
const { recognizesCommand } = require('./input');

const HELP = [
  '修仙帮助',
  '入门：我要修仙、新手礼包领取、修仙签到、我的修仙信息；闭关、出关、突破、直接突破、渡厄突破。',
  '物品：我的背包、物品信息 名称/ID、修仙商店、购买/使用/装备/卸下、功法修炼、我的功法。',
  '历练：悬赏令、秘境查询/探索、邪魔查询/讨伐、我的积分/积分兑换；切磋 @对象。',
  '交易：坊市查询/上架/购买/下架；送灵石 @对象 数量；赠送 @对象 物品 数量。',
  '灵庄：灵庄帮助、灵庄存入/取出 数量、灵庄结算、灵庄信息、灵庄会员升级。',
  '洞天：洞天福地帮助/购买/改名、我的洞天福地、灵田开垦/收取、灵矿开垦/收取。',
  '炼丹：炼丹帮助、炼丹、配方、我的炼丹信息、升级收取等级/丹药控火、炼丹考核开始/解答。',
  '宗门：宗门帮助（创建、加入、治理、任务、秘籍、攻击修炼、丹房完整指令）。',
  '互动：偷灵石 @对象、打劫 @对象、双修 @对象、我的双修次数；举行交友会、交友会查询、出价 数量。',
  '地图：地图、查看周围、向北走/向南走/向西走/向东走。',
  '仙缘：仙缘帮助、仙缘查询、仙缘任务接取/完成、我的仙缘、我的仙缘任务、表白 仙子名。',
  '排行：修仙排行榜、灵石排行榜、战力排行榜（玩家、宗门、坊市、拍卖均按本群隔离）。'
].join('\n');

function requireId(value, label) {
  if (typeof value !== 'string' || !value.trim()) throw new TypeError(`${label}必须是非空字符串ID。`);
}

function createGame({ databasePath, now = Date.now, random = Math.random, judge }) {
  if (judge !== undefined && typeof judge !== 'function') throw new TypeError('judge必须是宿主模型判定函数。');
  const store = openStore(databasePath);
  const pendingReviews = new Map();
  const game = {
    parseInput(event) {
      requireId(event.groupId, '群');
      requireId(event.userId, '用户');
      if (typeof event.text !== 'string') throw new TypeError('text必须是指令文本。');
      if (event.nickname !== undefined && typeof event.nickname !== 'string') throw new TypeError('nickname必须是字符串。');
      if (event.targetId !== undefined) requireId(event.targetId, '目标用户');
      if (event.answer !== undefined && typeof event.answer !== 'boolean') throw new TypeError('answer必须是布尔值。');
      if (event.answer === true) {
        const player = store.get(event.groupId, event.userId);
        const trial = player?.breakthroughTrial;
        const breakthrough = trial?.status === 'awaiting' && trial.fromRealm === player.realm;
        const rift = player?.activity?.kind === 'rift' && ['awaiting', 'judging'].includes(player.riftAdventure?.status);
        return breakthrough || rift ? { text: event.text.trim() } : null;
      }
      const text = event.text.trim().replace(/^[/／]\s*/u, '').replace(/\s+/gu, ' ');
      return recognizesCommand(text) ? { text } : null;
    },
    handleCommand(event) {
      const parsed = game.parseInput(event);
      if (!parsed) return { handled: false, message: '' };
      const { text } = parsed;
      if (event.answer !== true && text === '修仙帮助') return { handled: true, message: HELP };
      const timestamp = now();
      if (!Number.isFinite(timestamp)) throw new TypeError('游戏时钟必须返回有效毫秒时间戳。');
      try {
        return store.transaction(() => {
          const context = {
            ...event, text, now: timestamp, random, store,
            player: store.get(event.groupId, event.userId),
            world: store.getWorld(event.groupId)
          };
          if (context.player) refreshDaily(context.player, timestamp);
          const message = event.answer === true ? handleEncounters(context) ?? handleBreakthrough(context)
            : handleProgression(context) ?? handleMission(context) ?? handleInventory(context)
              ?? handleEncounters(context) ?? handleBank(context) ?? handleEstate(context)
              ?? handleAlchemy(context) ?? handleSocial(context) ?? handleRomance(context) ?? handleSect(context)
              ?? handleAuction(context) ?? handleMap(context) ?? handleBreakthrough(context);
          if (message === null) return { handled: false, message: '' };
          if (context.player) store.save(event.groupId, context.player);
          store.saveWorld(event.groupId, context.world);
          return { handled: true, message, ...(context.reviewRequest ? { reviewRequest: context.reviewRequest } : {}) };
        });
      } catch (error) {
        if (error instanceof GameError) return { handled: true, message: error.message };
        throw error;
      }
    },
    resolveReview(event) {
      requireId(event.groupId, '群');
      requireId(event.userId, '用户');
      requireId(event.requestId, '判定请求');
      if (event.kind !== 'breakthrough' && event.kind !== 'rift') throw new TypeError('判定类型无效。');
      const timestamp = now();
      if (!Number.isFinite(timestamp)) throw new TypeError('游戏时钟必须返回有效毫秒时间戳。');
      try {
        return store.transaction(() => {
          const context = {
            ...event, now: timestamp, random, store,
            player: store.get(event.groupId, event.userId), world: store.getWorld(event.groupId)
          };
          const message = event.kind === 'breakthrough'
            ? resolveBreakthroughReview(context, event) : resolveRiftReview(context, event);
          if (message === null) return { handled: false, message: '' };
          store.save(event.groupId, context.player);
          store.saveWorld(event.groupId, context.world);
          return { handled: true, message };
        });
      } catch (error) {
        if (error instanceof GameError) return { handled: true, message: error.message };
        if (error instanceof InvalidReviewError) {
          const retry = event.kind === 'breakthrough' ? '发送“突破”重试' : '重新发送本轮行动重试';
          return { handled: true, message: `模型判定格式不正确，未扣资源。${retry}。`, error: 'invalid_review' };
        }
        throw error;
      }
    },
    async handleMessage(event) {
      const { groupId, userId } = event;
      const result = game.handleCommand(event);
      if (!result.reviewRequest || !judge) return result;
      const request = result.reviewRequest;
      const { kind, requestId, revision } = request;
      const key = JSON.stringify([groupId, userId, kind, requestId, revision]);
      if (pendingReviews.has(key)) return pendingReviews.get(key);
      // 模型网络调用发生在事务之外。重复消息共用判定，失败仍可恢复请求。
      const task = Promise.resolve().then(() => judge(request)).then(
        review => game.resolveReview({ groupId, userId, kind, requestId, revision, review }),
        () => ({ handled: true, message: kind === 'breakthrough'
          ? '模型暂不可用，未扣资源。发送“突破”可重试。'
          : '模型暂不可用，未扣资源。重新发送本轮行动可重试。', reviewRequest: request, error: 'judge_failed' })
      ).finally(() => pendingReviews.delete(key));
      pendingReviews.set(key, task);
      return task;
    },
    getPlayer(groupId, userId) {
      requireId(groupId, '群');
      requireId(userId, '用户');
      return store.get(groupId, userId);
    },
    close() {
      store.close();
    }
  };
  return game;
}

module.exports = { createGame };
