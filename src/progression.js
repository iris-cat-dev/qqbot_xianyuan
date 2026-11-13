'use strict';

const {
  data, GameError, MINUTE, integer, dayKey, drawRoot, stats, clampVitals,
  addExp, addItem, removeItem, requirePlayer, requireIdle, spend,
  remaining, breakthroughRate, trainingBoost
} = require('./rules');
const { recordJourney } = require('./journey');
const fairies = require('../data/fairies.json');
const { recognizesProgression } = require('./input');

function createPlayer(userId, nickname, now, random) {
  const name = nickname?.trim() || userId;
  return {
    userId, name: Array.from(name).slice(0, 10).join(''),
    root: drawRoot(random), realm: 0, exp: 100, money: 0, hp: 100, mp: 50,
    equipment: { weapon: null, armor: null, technique: null, skill: null }, inventory: {},
    activity: null, breakthroughAt: null, breakthroughBonus: 0, pillBonus: 0,
    giftClaims: 0, giftAt: null, board: null,
    daily: { date: dayKey(now), refreshes: 0, pillUses: {}, sectTasks: 0, sectElixirClaimed: false, dualCultivations: 0 }, createdAt: now,
    attackBonus: 0, pillTotals: {}, bossPoints: 0, lastDuelAt: null,
    breakthroughTrial: null, riftAdventure: null, insightReviews: [], journey: [], journeySequence: 0,
    bank: null, estate: null,
    alchemy: { collectionLevel: 0, fireLevel: 0, exp: 0, records: {}, exam: { points: 0, current: null } },
    sectId: null, sectPosition: null, sectContribution: 0, attackPractice: 0,
    sectTask: null, lastSectTaskRefreshAt: null, lastStealAt: null, position: '新手村广场',
    romance: { favor: {}, completedSpecial: {}, task: null, completedDay: null, confessionDates: {}, partnerFairyId: null }
  };
}

function info(player, now) {
  const attributes = stats(player);
  const boost = trainingBoost(player);
  const realm = data.realms[player.realm];
  const next = data.realms[player.realm + 1];
  const activity = player.activity;
  const state = activity ? `${activity.label}（已过${Math.floor((now - activity.startedAt) / MINUTE)}分钟；${activity.finishCommand}结算）` : '空闲';
  const partner = player.romance?.partnerFairyId
    ? fairies.find(fairy => fairy.id === player.romance.partnerFairyId) : null;
  return [
    `${player.name} · ${realm.name}`,
    `灵根：${player.root.name}（${player.root.type}，${player.root.speed}倍）`,
    `修为：${player.exp}${next ? ` / 突破需${next.exp}` : '（最高境界）'}`,
    `灵石：${player.money} · 战力：${attributes.power}`,
    `气血：${player.hp}/${attributes.maxHp} · 真元：${player.mp}/${attributes.maxMp}`,
    `攻击：${attributes.attack} · 会心：${(attributes.crit * 100).toFixed(1)}% · 减伤：${(attributes.defense * 100).toFixed(1)}%`,
    ...(partner ? [`仙缘：与${partner.name}结为道侣`] : []),
    `修炼效率：${attributes.efficiency.toFixed(2)}倍${boost > 1 ? `（前期×${boost}）` : ''} · 闭关${Math.floor(30 * attributes.efficiency * boost)}修为/分钟 · 状态：${state}`
  ].join('\n');
}

function checkBreakthrough(player, now) {
  const next = data.realms[player.realm + 1];
  if (!next) throw new GameError('你已抵达天道之上，无须再突破。');
  if (player.exp < next.exp) throw new GameError(`修为不足，突破到${next.name}还需${next.exp - player.exp}修为。`);
  if (player.breakthroughAt !== null && now < player.breakthroughAt + 60 * MINUTE) {
    throw new GameError(`突破冷却中，还需${remaining(player.breakthroughAt + 60 * MINUTE, now)}分钟。`);
  }
  return next;
}

function probabilityText(player) {
  const threshold = breakthroughRate(player);
  // 保留原版 randint(0, 100) < P；100不是必成，避免向玩家显示虚假的100%。
  const chance = Math.min(101, threshold) / 101 * 100;
  return `突破成功率：${chance.toFixed(2)}%（0～100掷骰，小于${threshold}成功）`;
}

function settleClosing(player, now, useMoney = false) {
  if (player.activity?.kind !== 'closing') throw new GameError('你没有在闭关，先发送“闭关”。');
  const minutes = Math.max(0, Math.round((now - player.activity.startedAt) / MINUTE * 100) / 100);
  const attributes = stats(player);
  const base = Math.floor(minutes * 30 * attributes.efficiency * trainingBoost(player));
  const cost = useMoney ? Math.min(base, player.money) : 0;
  spend(player, cost);
  const total = base + cost;
  const oldHp = player.hp;
  const oldMp = player.mp;
  const speed = data.realms[player.realm].speed;
  player.hp = Math.min(attributes.maxHp, player.hp + Math.floor(total * 20 * speed));
  player.mp = Math.min(attributes.maxMp, player.mp + Math.floor(total * 10 * speed));
  const gain = addExp(player, total);
  player.activity = null;
  recordJourney(player, 'closing', now, { minutes, expGain: gain, hpRecovered: player.hp - oldHp, mpRecovered: player.mp - oldMp });
  return `闭关${minutes}分钟，增加${gain}修为${gain < total ? '（已达下一境界修为的1.5倍上限）' : ''}。\n恢复气血${player.hp - oldHp}、真元${player.mp - oldMp}；消耗${cost}灵石。\n当前修为：${player.exp}。`;
}

function handleProgression(context) {
  const { text, userId, nickname, now, random, store, groupId } = context;
  let player = context.player;
  if (text === '我要修仙') {
    if (player) throw new GameError('你已踏入仙途，发送“我的修仙信息”查看角色。');
    player = context.player = createPlayer(userId, nickname, now, random);
    return `${player.name}，仙途已开启！\n${info(player, now)}\n发送“新手礼包领取”领资源，“闭关”开始修炼，“修仙帮助”查看全部指令。`;
  }
  if (!recognizesProgression(text)) return null;
  requirePlayer(player);

  if (text === '我的修仙信息' || text === '我的状态') return info(player, now);
  if (text === '我的突破概率') return probabilityText(player);

  if (text === '修仙签到') {
    const date = dayKey(now);
    if (player.signDate === date) throw new GameError('今日已经签到，明日北京时间00:00后再来。');
    const realmFactor = player.realm + 1;
    const money = realmFactor * integer(500, 1000, random);
    player.money += money;
    player.signDate = date;
    return `签到成功，按当前境界获得${money}灵石！当前灵石：${player.money}。`;
  }

  if (text === '新手礼包领取' || text === '领取新手礼包') {
    if (player.giftClaims >= data.gifts.length) throw new GameError('新手礼包已全部领取。');
    const wait = player.giftAt === null ? 0 : Math.floor((player.giftAt + 30 * player.giftClaims * MINUTE - now) / MINUTE);
    if (wait > 0) throw new GameError(`下一份新手礼包还需等待${wait}分钟。`);
    const gift = data.gifts[player.giftClaims];
    player.money += gift.money;
    for (const item of gift.items ?? []) addItem(player, String(item.id), item.count);
    player.giftClaims++;
    player.giftAt = now;
    const supplies = gift.items?.length ? '\n龙陵墓穴藏宝图×3、悬赏令×3已放入背包。' : '';
    return `领取第${player.giftClaims}份新手礼包，获得${gift.money}灵石。${supplies}${player.giftClaims < data.gifts.length ? '\n30分钟后可领取下一份。' : '\n新手礼包已全部领取。'}`;
  }

  if (text.startsWith('改名')) {
    const name = text.slice(2).trim();
    if (!name || Array.from(name).length > 10 || name === '伊小咪') throw new GameError('道号须为1～10个字符，且不能使用保留道号“伊小咪”。');
    player.name = name;
    return `您的道号已修改为：${name}。`;
  }

  if (text === '重入仙途') {
    spend(player, 200000);
    player.root = drawRoot(random);
    return `消耗200000灵石，重塑灵根：${player.root.name}（${player.root.type}，${player.root.speed}倍）。\n境界、修为和背包保持不变。`;
  }

  if (text === '闭关') {
    requireIdle(player);
    player.activity = { kind: 'closing', label: '闭关', startedAt: now, finishCommand: '出关' };
    const boost = trainingBoost(player);
    return `已开始闭关${boost > 1 ? `，前期加成×${boost}` : ''}，每分钟修为=${30 * boost}×灵根倍率×境界速度×功法加成。\n发送“出关”结算并疗伤；发送“突破”可结算后直接尝试突破；“灵石出关”可用灵石追加等量修为。`;
  }

  if (text === '出关' || text === '灵石出关') {
    return settleClosing(player, now, text === '灵石出关');
  }


  if (text === '直接突破' || text === '渡厄突破') {
    if (player.activity?.kind === 'rift') throw new GameError('正在秘境探索，请先完成三幕行动、等待结算或终止探索。');
    const next = checkBreakthrough(player, now);
    const protectedAttempt = text === '渡厄突破';
    if (protectedAttempt) removeItem(player, '1999');
    const threshold = breakthroughRate(player);
    const roll = integer(0, 100, random);
    const baseRate = data.realms[player.realm].rate;
    player.breakthroughAt = now;
    player.pillBonus = 0;
    if (roll < threshold) {
      player.realm++;
      player.breakthroughBonus = 0;
      const attributes = stats(player);
      player.hp = attributes.maxHp;
      player.mp = attributes.maxMp;
      return `突破成功！境界提升至${next.name}，修为保留${player.exp}，气血真元恢复。\n掷骰：${roll} < ${threshold}，下次突破需等待60分钟。`;
    }
    const loss = protectedAttempt ? 0 : Math.floor(player.exp * integer(1, 10, random) / 100);
    player.exp -= loss;
    clampVitals(player);
    player.breakthroughBonus += Math.max(1, Math.floor(baseRate * 0.5));
    return `突破失败，${protectedAttempt ? '渡厄丹护持，修为没有损失' : `损失${loss}修为`}。\n掷骰：${roll} ≥ ${threshold}；${probabilityText(player)}\n下次突破需等待60分钟。`;
  }

  const all = store.list(groupId);
  const by = text === '灵石排行榜' ? 'money' : text === '战力排行榜' ? 'power' : 'realm';
  all.sort((a, b) => {
    const order = by === 'money' ? b.money - a.money : by === 'power' ? stats(b).power - stats(a).power : b.realm - a.realm || b.exp - a.exp;
    return order || a.userId.localeCompare(b.userId);
  });
  const title = by === 'money' ? '灵石排行榜' : by === 'power' ? '战力排行榜' : '修仙排行榜';
  return `${title}（本群）\n${all.slice(0, 10).map((entry, i) => `${i + 1}. ${entry.name} · ${data.realms[entry.realm].name} · ${by === 'money' ? `${entry.money}灵石` : by === 'power' ? `${stats(entry).power}战力` : `${entry.exp}修为`}`).join('\n')}`;
}

module.exports = { handleProgression, info, checkBreakthrough, settleClosing };
