'use strict';

const fairies = require('../data/fairies.json');
const {
  GameError, dayKey, integer, items, removeItem, requireHealthy, requirePlayer,
  safeAdd, safeMultiply, spend
} = require('./rules');
const { playerFighter, fight } = require('./combat');
const { recognizesRomance } = require('./input');

const FAIRIES_BY_ID = new Map(fairies.map(fairy => [fairy.id, fairy]));
if (FAIRIES_BY_ID.size !== fairies.length) throw new Error('仙子配置存在重复ID。');

const NORMAL_MISSIONS = [
  {
    id: 'treasures', name: '购置修行奇珍',
    desc: '从坊间购置一批辅助修行的奇珍异宝。',
    kind: 'money', baseCost: 100_000, realmCost: 25_000, favor: 10
  },
  {
    id: 'rival', name: '排解修行仇怨',
    desc: '击退一路纠缠的仇家，解除此次行程的后顾之忧。',
    kind: 'combat', enemyName: '寻仇修士', favor: 12
  },
  {
    id: 'self-defense', name: '提升自保能力',
    desc: '穿戴武器与护具，再为仙子购置一套合用装备。',
    kind: 'equipment', baseCost: 75_000, realmCost: 20_000, favor: 11
  },
  {
    id: 'cultivation', name: '交流修炼心得',
    desc: '修习一门功法，并支付拓印与论道所需灵石。',
    kind: 'technique', baseCost: 60_000, realmCost: 15_000, favor: 10
  }
];

const HELP = [
  '仙缘：每天北京时间00:00后，各群在首次相关查询时随机刷新一位仙子；不会连续刷新同一人。',
  '查询：仙缘查询、我的仙缘、我的仙缘任务。',
  '任务：仙缘任务接取、仙缘任务完成。每人每天可完成一次；每位仙子的首次任务是专属剧情，之后随机获得普通任务。',
  '好感：完成任务增加当前仙子好感；“仙缘查询”显示本群当期好感排行。',
  '表白：表白 仙子名。当前仙子好感达到100后，每天可尝试一次；成功率从50%随好感提升，最高95%。每位修士只能有一位道侣，每位仙子在本群也只能归属一位修士。'
].join('\n');

function defaultRomanceState() {
  return {
    favor: {}, completedSpecial: {}, task: null, completedDay: null,
    confessionDates: {}, partnerFairyId: null
  };
}

function romanceState(player) {
  player.romance ??= defaultRomanceState();
  player.romance.favor ??= {};
  player.romance.completedSpecial ??= {};
  player.romance.task ??= null;
  player.romance.completedDay ??= null;
  player.romance.confessionDates ??= {};
  player.romance.partnerFairyId ??= null;
  return player.romance;
}

function refreshEvent(ctx) {
  const date = dayKey(ctx.now);
  const previousId = ctx.world.romance?.fairyId;
  const current = ctx.world.romance;
  ctx.world.romancePartners ??= {};
  if (current?.date === date && (current.fairyId === null || FAIRIES_BY_ID.has(current.fairyId))) {
    return { date, fairy: current.fairyId === null ? null : FAIRIES_BY_ID.get(current.fairyId), refreshed: false };
  }
  let pool = fairies.filter(fairy => !ctx.world.romancePartners[fairy.id]);
  if (pool.length > 1 && pool.some(fairy => fairy.id === previousId)) {
    pool = pool.filter(fairy => fairy.id !== previousId);
  }
  if (!pool.length) {
    ctx.world.romance = { date, fairyId: null };
    return { date, fairy: null, refreshed: true };
  }
  const fairy = pool[integer(0, pool.length - 1, ctx.random)];
  ctx.world.romance = { date, fairyId: fairy.id };
  return { date, fairy, refreshed: true };
}

function favorFor(player, fairyId) {
  return player ? romanceState(player).favor[fairyId] ?? 0 : 0;
}

function ranking(ctx, fairyId) {
  return ctx.store.list(ctx.groupId).map(player => ({ player, favor: favorFor(player, fairyId) }))
    .filter(entry => entry.favor > 0)
    .sort((a, b) => b.favor - a.favor || a.player.userId.localeCompare(b.player.userId))
    .slice(0, 10);
}

function fairyDescription(ctx, event) {
  const { fairy, refreshed } = event;
  if (!fairy) return '本群十位仙子均已与修士结为道侣，今日暂无新的仙缘。';
  const board = ranking(ctx, fairy.id);
  const own = favorFor(ctx.player, fairy.id);
  const ownerId = ctx.world.romancePartners[fairy.id];
  const owner = ownerId ? ctx.store.get(ctx.groupId, ownerId) : null;
  return [
    `${refreshed ? '今日仙缘已刷新。\n' : ''}仙子：${fairy.name}`,
    `境界：${fairy.level} · 灵根：${fairy.root}`,
    `性格：${fairy.personality}`,
    `背景：${fairy.background}`,
    `缘分状态：${ownerId ? `已与${owner?.name ?? ownerId}结为道侣` : '尚未定缘'}`,
    ctx.player ? `你的好感：${own}` : '踏入仙途后可接取仙缘任务。',
    '☆------本群当期好感排行------☆',
    board.length ? board.map((entry, index) => `${index + 1}. ${entry.player.name} · ${entry.favor}`).join('\n') : '暂无修士获得青睐。',
    '发送“仙缘任务接取”了解她的请求；本轮于北京时间次日00:00后刷新。'
  ].join('\n');
}

function missionCost(mission, realm) {
  if (mission.cost !== undefined) return mission.cost;
  return safeAdd(mission.baseCost, safeMultiply(realm, mission.realmCost, '仙缘任务费用'), '仙缘任务费用');
}

function makeTask(fairy, mission, player, date, now, special) {
  return {
    fairyId: fairy.id, day: date, missionId: mission.id, special,
    cost: ['money', 'equipment', 'technique'].includes(mission.kind) ? missionCost(mission, player.realm) : 0,
    acceptedAt: now
  };
}

function taskMission(fairy, task) {
  if (task.special && fairy.specialMission.id === task.missionId) return fairy.specialMission;
  return NORMAL_MISSIONS.find(mission => mission.id === task.missionId) ?? null;
}

function requirementText(mission, task) {
  if (mission.kind === 'items') {
    return mission.items.map(requirement => `${items.get(requirement.id).name}×${requirement.count}`).join('、');
  }
  if (mission.kind === 'money') return `${task.cost}灵石`;
  if (mission.kind === 'combat') return `保持可战状态并击败${mission.enemyName}`;
  if (mission.kind === 'equipment') return `装备武器与护具，并支付${task.cost}灵石`;
  if (mission.kind === 'technique') return `修习一门功法，并支付${task.cost}灵石`;
  throw new Error(`未知仙缘任务类型：${mission.kind}`);
}

function taskText(fairy, task) {
  const mission = taskMission(fairy, task);
  if (!mission) throw new Error(`未知仙缘任务：${task.missionId}`);
  return `${task.special ? '专属任务' : '普通任务'}：${mission.name}\n${mission.desc}\n完成条件：${requirementText(mission, task)}\n完成后好感+${mission.favor}。`;
}

function expireTask(state, event) {
  if (!state.task) return false;
  if (event.fairy && state.task.day === event.date && state.task.fairyId === event.fairy.id) return false;
  state.task = null;
  return true;
}

function acceptTask(ctx, event, state) {
  expireTask(state, event);
  if (state.completedDay === event.date) throw new GameError('今日已经完成一次仙缘任务，明日再来。');
  if (state.task) return `你已接取任务：\n${taskText(event.fairy, state.task)}`;
  const special = state.completedSpecial[event.fairy.id] !== true;
  const mission = special ? event.fairy.specialMission
    : NORMAL_MISSIONS[integer(0, NORMAL_MISSIONS.length - 1, ctx.random)];
  state.task = makeTask(event.fairy, mission, ctx.player, event.date, ctx.now, special);
  return `已接取${event.fairy.name}的任务：\n${taskText(event.fairy, state.task)}`;
}

function combatMission(ctx, mission) {
  requireHealthy(ctx.player);
  const challenger = playerFighter(ctx.player);
  const maxHp = Math.max(100, Math.floor(challenger.maxHp * 0.75));
  const maxMp = Math.max(0, Math.floor(challenger.maxMp * 0.5));
  const opponent = {
    name: mission.enemyName, exp: 0, hp: maxHp, maxHp, mp: maxMp, maxMp,
    attack: Math.max(1, Math.floor(challenger.attack * 0.8)), crit: 21 / 101,
    defense: 0, skill: null
  };
  const result = fight(challenger, opponent, ctx.random);
  ctx.player.hp = Math.max(1, result.attacker.hp);
  ctx.player.mp = Math.max(0, result.attacker.mp);
  return { won: result.winner === 'attacker', report: result.report };
}

function completeTask(ctx, event, state) {
  const expired = expireTask(state, event);
  if (!state.task) throw new GameError(expired ? '昨日仙缘任务已随仙子离去而失效，请重新接取。' : '尚未接取仙缘任务。');
  if (state.completedDay === event.date) throw new GameError('今日已经完成一次仙缘任务。');
  const task = state.task;
  const mission = taskMission(event.fairy, task);
  if (!mission) throw new Error(`未知仙缘任务：${task.missionId}`);
  let report = '';
  if (mission.kind === 'items') {
    for (const requirement of mission.items) {
      if ((ctx.player.inventory[requirement.id] ?? 0) < requirement.count) {
        throw new GameError(`完成任务需要${items.get(requirement.id).name}×${requirement.count}。`);
      }
    }
    for (const requirement of mission.items) removeItem(ctx.player, requirement.id, requirement.count);
  } else if (mission.kind === 'money') {
    spend(ctx.player, task.cost);
  } else if (mission.kind === 'equipment') {
    if (!ctx.player.equipment.weapon || !ctx.player.equipment.armor) throw new GameError('须先同时装备武器与护具。');
    spend(ctx.player, task.cost);
  } else if (mission.kind === 'technique') {
    if (!ctx.player.equipment.technique) throw new GameError('须先修习并装备一门功法。');
    spend(ctx.player, task.cost);
  } else if (mission.kind === 'combat') {
    const battle = combatMission(ctx, mission);
    report = `${battle.report}\n`;
    if (!battle.won) return `${report}未能击败${mission.enemyName}，任务仍保留；疗伤后可以再次挑战。`;
  } else {
    throw new Error(`未知仙缘任务类型：${mission.kind}`);
  }
  state.favor[event.fairy.id] = safeAdd(state.favor[event.fairy.id] ?? 0, mission.favor, '仙缘好感');
  if (task.special) state.completedSpecial[event.fairy.id] = true;
  state.completedDay = event.date;
  state.task = null;
  return `${report}完成“${mission.name}”，${event.fairy.name}好感+${mission.favor}，当前好感${state.favor[event.fairy.id]}。`;
}

function ownRomance(event, state) {
  const partner = state.partnerFairyId ? FAIRIES_BY_ID.get(state.partnerFairyId) : null;
  const favorRows = fairies.map(fairy => ({ fairy, favor: state.favor[fairy.id] ?? 0 }))
    .filter(entry => entry.favor > 0)
    .sort((a, b) => b.favor - a.favor || a.fairy.name.localeCompare(b.fairy.name));
  expireTask(state, event);
  const current = event.fairy;
  return [
    `道侣：${partner?.name ?? '暂无'}`,
    current ? `今日仙子：${current.name} · 好感${state.favor[current.id] ?? 0}` : '今日仙子：暂无（本群十位仙子均已结缘）',
    `今日任务：${state.completedDay === event.date ? '已完成' : state.task && current ? `进行中（${taskMission(current, state.task).name}）` : '未接取'}`,
    '好感记录：',
    favorRows.length ? favorRows.map(entry => `${entry.fairy.name}：${entry.favor}`).join('\n') : '暂无。'
  ].join('\n');
}

function confess(ctx, event, state) {
  const name = ctx.text.slice('表白'.length).replace(/\s+/gu, '');
  if (!name) throw new GameError('格式：表白 仙子名。');
  if (name !== event.fairy.name) throw new GameError(`今日出现的仙子是${event.fairy.name}，只能向她表白。`);
  if (state.partnerFairyId) {
    const partner = FAIRIES_BY_ID.get(state.partnerFairyId);
    if (state.partnerFairyId === event.fairy.id) return `你与${partner.name}早已结为道侣。`;
    throw new GameError(`你已与${partner?.name ?? '另一位仙子'}结为道侣，不能再向他人表白。`);
  }
  const ownerId = ctx.world.romancePartners[event.fairy.id];
  if (ownerId && ownerId !== ctx.userId) {
    const owner = ctx.store.get(ctx.groupId, ownerId);
    throw new GameError(`${event.fairy.name}已与${owner?.name ?? '本群其他修士'}结为道侣。`);
  }
  const favor = state.favor[event.fairy.id] ?? 0;
  if (favor < 100) throw new GameError(`表白至少需要100好感，当前${favor}。`);
  if (state.confessionDates[event.fairy.id] === event.date) throw new GameError('今日已经向她表白过，明日再试。');
  state.confessionDates[event.fairy.id] = event.date;
  const chance = Math.min(95, 50 + Math.floor((favor - 100) / 2));
  const roll = integer(1, 100, ctx.random);
  if (roll > chance) return `${event.fairy.name}还需要时间确认心意（${roll}>${chance}），今日不可再次表白。`;
  state.partnerFairyId = event.fairy.id;
  ctx.world.romancePartners[event.fairy.id] = ctx.userId;
  return `${event.fairy.name}接受了你的心意（${roll}≤${chance}），你们正式结为道侣；本群其他修士不能再与她结缘。`;
}

function handleRomance(ctx) {
  if (!recognizesRomance(ctx.text)) return null;
  if (ctx.text === '仙缘帮助') return HELP;
  const event = refreshEvent(ctx);
  if (ctx.text === '仙缘查询') return fairyDescription(ctx, event);
  requirePlayer(ctx.player);
  const state = romanceState(ctx.player);
  if (state.partnerFairyId) {
    const ownerId = ctx.world.romancePartners[state.partnerFairyId];
    if (!ownerId) ctx.world.romancePartners[state.partnerFairyId] = ctx.userId;
    else if (ownerId !== ctx.userId) throw new Error(`仙子${state.partnerFairyId}存在重复归属。`);
  }
  if (ctx.text === '我的仙缘') return ownRomance(event, state);
  if (!event.fairy) throw new GameError('本群十位仙子均已结缘，暂无新的仙缘任务。');
  if (ctx.text === '仙缘任务接取') {
    const ownerId = ctx.world.romancePartners[event.fairy.id];
    if (ownerId && ownerId !== ctx.userId) throw new GameError(`${event.fairy.name}已与本群其他修士结为道侣，不再发布新的任务。`);
    return acceptTask(ctx, event, state);
  }
  if (ctx.text === '我的仙缘任务') {
    const expired = expireTask(state, event);
    if (!state.task) return expired ? '昨日仙缘任务已失效，请重新接取。' : '尚未接取仙缘任务。';
    return taskText(event.fairy, state.task);
  }
  if (ctx.text === '仙缘任务完成') return completeTask(ctx, event, state);
  return confess(ctx, event, state);
}

module.exports = { handleRomance };
