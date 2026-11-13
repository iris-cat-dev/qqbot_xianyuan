'use strict';

const { randomUUID } = require('node:crypto');
const { data, GameError, integer, stats, clampVitals, removeItem, requirePlayer } = require('./rules');
const { checkBreakthrough, settleClosing } = require('./progression');
const { buildBreakthroughFacts } = require('./journey');
const { questionFor, makeReviewRequest, validateReview } = require('./breakthrough-review');

const ACTIVE_STATUSES = new Set(['awaiting', 'judging', 'qualified']);

function rememberMessage(trial, message) {
  trial.lastMessage = message;
  return message;
}

function requestReview(context, trial) {
  context.reviewRequest = makeReviewRequest(trial);
  return rememberMessage(trial, '正在判断你的理解……');
}

function cacheKey(trial) {
  return JSON.stringify({
    fromRealm: trial.fromRealm,
    targetRealm: trial.targetRealm,
    facts: trial.facts,
    answers: trial.answers
  });
}

function rememberReview(player, trial, raw) {
  const key = cacheKey(trial);
  const reviews = player.insightReviews ?? [];
  const existing = reviews.findIndex(entry => entry.key === key);
  if (existing !== -1) reviews.splice(existing, 1);
  reviews.push({ key, review: structuredClone(raw) });
  player.insightReviews = reviews.slice(-16);
}

function beginTrial(context) {
  const { player, now } = context;
  checkBreakthrough(player, now);
  const question = questionFor(player);
  const trial = player.breakthroughTrial = {
    id: randomUUID(),
    revision: 0,
    fromRealm: player.realm,
    targetRealm: player.realm + 1,
    question,
    facts: buildBreakthroughFacts(player),
    answers: [],
    status: 'awaiting',
    protectedAttempt: false,
    review: null,
    receipts: [],
    promptMessage: `${question}\n几个字或一句话就行。四项各0～2分：经历、问题、原因、调整；总分≥4且原因≥1通过。\n可发“用丹”选择渡厄丹保护，或“取消突破”。`,
    lastMessage: ''
  };
  return rememberMessage(trial, trial.promptMessage);
}

function attemptBreakthrough(context, trial) {
  const { player, now, random } = context;
  let next;
  try {
    next = checkBreakthrough(player, now);
    if (trial.protectedAttempt) removeItem(player, '1999');
  } catch (error) {
    // 已认可的理解必须提交，资格或库存变化不能使整个事务回滚。
    if (!(error instanceof GameError)) throw error;
    return rememberMessage(trial, `理解已通过。${error.message}`);
  }

  const baseRate = data.realms[player.realm].rate;
  const probability = Math.min(100, Math.max(baseRate, trial.review.probabilityFloor)
    + player.breakthroughBonus + player.pillBonus);
  const success = random() < probability / 100;
  player.breakthroughAt = now;
  player.pillBonus = 0;
  let loss = 0;
  if (success) {
    player.realm++;
    player.breakthroughBonus = 0;
    const attributes = stats(player);
    player.hp = attributes.maxHp;
    player.mp = attributes.maxMp;
    trial.status = 'settled';
  } else {
    loss = trial.protectedAttempt ? 0 : Math.floor(player.exp * integer(1, 10, random) / 100);
    player.exp -= loss;
    clampVitals(player);
    player.breakthroughBonus += Math.max(1, Math.floor(baseRate * 0.5));
    // 概率失败保留已通过的理解，只有后续“突破”才会再尝试。
    trial.status = 'qualified';
  }
  trial.lastAttempt = { at: now, probability, success, loss, protectedAttempt: trial.protectedAttempt };
  const result = success
    ? `突破成功！境界提升至${next.name}，修为保留${player.exp}，气血真元恢复。`
    : `突破失败，${trial.protectedAttempt ? '渡厄丹护持，修为没有损失' : `损失${loss}修为`}。理解已通过，冷却后发送“突破”可直接再试。`;
  return rememberMessage(trial, `${trial.review.feedback}\n${result}\n本次成功率${probability}%，下次突破需等待60分钟。`);
}

function invalidateTrial(trial) {
  trial.status = 'cancelled';
  return rememberMessage(trial, '境界已改变，本轮突破已取消。发送“突破”按当前境界重新开始。');
}

function handleBreakthrough(context) {
  const { text, player } = context;
  const trial = player?.breakthroughTrial;
  if ((trial?.status === 'awaiting' || trial?.status === 'judging') && player.realm !== trial.fromRealm) {
    return invalidateTrial(trial);
  }
  if (context.answer !== true && text === '突破') {
    requirePlayer(player);
    if (player.activity?.kind === 'rift') throw new GameError('正在秘境探索，请先完成三幕行动、等待结算或终止探索。');
    const closingMessage = player.activity?.kind === 'closing' ? settleClosing(player, context.now) : null;
    let message;
    try {
      if (trial?.status === 'awaiting') message = rememberMessage(trial, trial.promptMessage);
      else if (trial?.status === 'judging') message = requestReview(context, trial);
      else if (trial?.status === 'qualified' && trial.fromRealm === player.realm) message = attemptBreakthrough(context, trial);
      else message = beginTrial(context);
    } catch (error) {
      if (!closingMessage || !(error instanceof GameError)) throw error;
      message = error.message;
    }
    return closingMessage ? `${closingMessage}\n${message}` : message;
  }

  if (context.answer !== true && text === '取消突破') {
    requirePlayer(player);
    if (!trial || !ACTIVE_STATUSES.has(trial.status)) return '当前没有进行中的突破。';
    trial.status = 'cancelled';
    return rememberMessage(trial, '已取消突破，资源未消耗。');
  }

  if (context.answer !== true && (text === '用丹' || text === '不用丹')) {
    requirePlayer(player);
    if (!trial || !ACTIVE_STATUSES.has(trial.status)) return '当前没有进行中的突破，请先发送“突破”。';
    const protectedAttempt = text === '用丹';
    if (protectedAttempt && (player.inventory['1999'] ?? 0) < 1) {
      throw new GameError('背包中的渡厄丹不足，保护选择未改变。');
    }
    trial.protectedAttempt = protectedAttempt;
    return rememberMessage(trial, protectedAttempt
      ? '本次将用渡厄丹保护，正式尝试时才消耗；失败不损修为。'
      : '本次不用渡厄丹，正式尝试失败可能损失修为。');
  }
  if (!trial || !ACTIVE_STATUSES.has(trial.status)) return null;
  if (context.answer !== true) return null;
  if (trial.status === 'judging') return requestReview(context, trial);
  if (trial.status !== 'awaiting') return null;

  const answer = text.trim();
  if (!answer) return rememberMessage(trial, '几个字或一句话就行，请回复你的想法。');
  if (Array.from(answer).length > 200) {
    return rememberMessage(trial, '请用几个字或一句话回复（最多200字），答题次数和资源都未消耗。');
  }
  trial.answers.push(answer);
  trial.revision++;
  trial.status = 'judging';
  const cached = player.insightReviews?.find(entry => entry.key === cacheKey(trial));
  if (cached) {
    return resolveBreakthroughReview(context, {
      requestId: trial.id, revision: trial.revision, review: cached.review
    });
  }
  return requestReview(context, trial);
}

function resolveBreakthroughReview(context, { requestId, revision, review }) {
  const player = context.player;
  const trial = player?.breakthroughTrial;
  if (!trial || trial.id !== requestId) return null;
  const receipt = trial.receipts.find(entry => entry.revision === revision);
  if (receipt) return receipt.message;
  if (trial.revision !== revision) return null;
  if (trial.status !== 'judging') return trial.lastMessage;

  if (player.realm !== trial.fromRealm) return invalidateTrial(trial);
  const decision = validateReview(review, trial);
  rememberReview(player, trial, review);
  trial.review = decision;
  let message;
  if (decision.passed) {
    trial.status = 'qualified';
    message = attemptBreakthrough(context, trial);
  } else if (trial.answers.length < 2) {
    trial.status = 'awaiting';
    trial.promptMessage = `${decision.feedback}\n${decision.followUp}\n几个字或一句话就行。`;
    message = rememberMessage(trial, trial.promptMessage);
  } else {
    trial.status = 'rejected';
    message = rememberMessage(trial, `${decision.feedback}\n这轮先到这里；想好后发送“突破”可重新开始。`);
  }
  trial.receipts.push({ revision, message });
  return message;
}

module.exports = { handleBreakthrough, resolveBreakthroughReview };
