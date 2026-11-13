'use strict';
const { randomUUID } = require('node:crypto');

const {
  data, items, GameError, MINUTE, integer, pick, dayKey, clampVitals,
  addExp, addItem, requirePlayer, requireIdle, requireHealthy, remaining,
  realmFamily, playerRank
} = require('./rules');
const { playerFighter, bossFighter, fight } = require('./combat');
const encounterData = require('../data/encounter-data.json');
const { recordJourney } = require('./journey');
const { recognizesEncounters } = require('./input');
const { makeRiftReviewRequest, validateRiftReview } = require('./rift-review');
const DAY = 24 * 60 * MINUTE;
const BEIJING_OFFSET = 8 * 60 * MINUTE;

const RIFT_SCENES = [
  {
    id: 'threshold', title: '灵雾石门',
    describe: name => `${name}入口灵雾翻涌，半掩石门上爬满暗红符纹。门前散落着断裂法器，雾中还有脚步声逼近。`
  },
  {
    id: 'ward', title: '残阵岔路',
    describe: name => `深入${name}后，前路被一座残缺禁阵截断。左侧石廊传来水声，右侧地面留有新鲜拖痕，阵眼则忽明忽暗。`
  },
  {
    id: 'heart', title: '秘境核心',
    describe: name => `${name}核心悬着一团宝光，守护灵影正在苏醒。四周石柱不断崩裂，退路也被涌动灵气逐渐封住。`
  }
];
const OUTCOME_SCORE = { success: 2, mixed: 1, failure: 0 };
const OUTCOME_LABEL = { success: '破局', mixed: '险过', failure: '受挫' };

function riftScene(snapshot, round) {
  const template = RIFT_SCENES[round];
  return { id: template.id, title: template.title, description: template.describe(snapshot.name) };
}

function adventurePrompt(activity, adventure) {
  const scene = adventure.scene;
  return `【${activity.rift.name}·第${adventure.round + 1}/${adventure.maxRounds}幕·${scene.title}】\n${scene.description}\n你准备怎么做？直接回复行动，几个字或一句话即可。若不想互动，也可在进入${activity.rift.time}分钟后发送“秘境结算”。`;
}

function rememberAdventure(adventure, message) {
  adventure.lastMessage = message;
  return message;
}

function startRiftAdventure(player, activity) {
  const adventure = player.riftAdventure = {
    id: randomUUID(), revision: 0, round: 0, maxRounds: RIFT_SCENES.length,
    status: 'awaiting', score: 0, scene: riftScene(activity.rift, 0), history: [],
    pendingAction: null, receipts: [], promptMessage: '', lastMessage: ''
  };
  adventure.promptMessage = adventurePrompt(activity, adventure);
  return rememberAdventure(adventure, adventure.promptMessage);
}

function requestRiftReview(context, activity, adventure) {
  context.reviewRequest = makeRiftReviewRequest(activity, adventure, context.player);
  return rememberAdventure(adventure, '秘境正在推演你的行动……');
}

function handleRiftAnswer(context) {
  const { player, text } = context;
  const activity = player?.activity;
  const adventure = player?.riftAdventure;
  if (activity?.kind !== 'rift' || !adventure || !['awaiting', 'judging'].includes(adventure.status)) return null;
  if (adventure.status === 'judging') return requestRiftReview(context, activity, adventure);
  const action = text.trim();
  if (!action) return rememberAdventure(adventure, '请直接回复你在当前场景中的行动。');
  if (Array.from(action).length > 200) {
    return rememberAdventure(adventure, '请用200字以内描述本轮行动，秘境进度和资源都未改变。');
  }
  adventure.pendingAction = action;
  adventure.revision++;
  adventure.status = 'judging';
  return requestRiftReview(context, activity, adventure);
}

function settleRiftAdventure(ctx, activity, adventure, decision) {
  const snapshot = activity.rift;
  const before = { exp: ctx.player.exp, money: ctx.player.money, hp: ctx.player.hp, mp: ctx.player.mp };
  let event;
  let settlement;
  if (adventure.score >= 5) {
    event = 'treasure';
    settlement = riftTreasure(ctx, snapshot);
  } else if (adventure.score >= 3) {
    event = 'battle';
    settlement = riftBattle(ctx, snapshot);
  } else {
    event = 'loss';
    settlement = riftLoss(ctx);
  }
  ctx.player.activity = null;
  adventure.status = 'settled';
  adventure.pendingAction = null;
  recordJourney(ctx.player, 'rift', ctx.now, {
    name: snapshot.name, event: `agent_${event}`, score: adventure.score,
    expDelta: ctx.player.exp - before.exp, moneyDelta: ctx.player.money - before.money,
    hpDelta: ctx.player.hp - before.hp, mpDelta: ctx.player.mp - before.mp
  });
  return `${decision.narrative}\n判定：${OUTCOME_LABEL[decision.outcome]}。${decision.reason}\n三幕评价${adventure.score}/${adventure.maxRounds * 2}。\n${snapshot.name}互动探索结算：\n${settlement}`;
}

function resolveRiftReview(context, { requestId, revision, review }) {
  const player = context.player;
  const adventure = player?.riftAdventure;
  if (!adventure || adventure.id !== requestId) return null;
  const receipt = adventure.receipts.find(entry => entry.revision === revision);
  if (receipt) return receipt.message;
  if (adventure.revision !== revision) return null;
  if (adventure.status !== 'judging') return adventure.lastMessage;
  const activity = player.activity;
  if (activity?.kind !== 'rift') {
    adventure.status = 'cancelled';
    return rememberAdventure(adventure, '本轮秘境已经结束，迟到的判定未生效。');
  }

  const decision = validateRiftReview(review);
  adventure.history.push({
    sceneId: adventure.scene.id, action: adventure.pendingAction,
    outcome: decision.outcome, reason: decision.reason, narrative: decision.narrative
  });
  adventure.score += OUTCOME_SCORE[decision.outcome];
  let message;
  if (adventure.history.length >= adventure.maxRounds) {
    message = settleRiftAdventure(context, activity, adventure, decision);
  } else {
    adventure.round++;
    adventure.status = 'awaiting';
    adventure.pendingAction = null;
    adventure.scene = riftScene(activity.rift, adventure.round);
    adventure.promptMessage = adventurePrompt(activity, adventure);
    message = `${decision.narrative}\n判定：${OUTCOME_LABEL[decision.outcome]}。${decision.reason}\n${adventure.promptMessage}`;
  }
  rememberAdventure(adventure, message);
  adventure.receipts.push({ revision, message });
  adventure.receipts = adventure.receipts.slice(-8);
  return message;
}

function weighted(weights, random) {
  const entries = Object.entries(weights);
  let roll = integer(1, entries.reduce((sum, [, weight]) => sum + weight, 0), random);
  return entries.find(([, weight]) => (roll -= weight) <= 0)[0];
}

function riftBoundary(now) {
  // 最近一次已到达的北京时间14:00；新群在14:00前也可补生成昨日批次。
  return Math.floor((now + BEIJING_OFFSET - 14 * 60 * MINUTE) / DAY) * DAY
    + 14 * 60 * MINUTE - BEIJING_OFFSET;
}

function refreshRift(ctx) {
  const boundary = riftBoundary(ctx.now);
  if (ctx.world.riftGeneratedAt !== null && ctx.world.riftGeneratedAt >= boundary) return;
  const weights = {};
  for (const [name, rift] of Object.entries(encounterData.rifts)) weights[name] = rift.type_rate;
  const name = weighted(weights, ctx.random);
  ctx.world.rift = { name, ...encounterData.rifts[name] };
  ctx.world.riftGeneratedAt = boundary;
}

function middleRealm(realm) {
  if (realm === 0 || realm === data.realms.length - 1) return realm;
  return Math.floor((realm - 1) / 3) * 3 + 2;
}

function bossRealm(active, bosses, random) {
  const represented = player => bosses.some(boss => realmFamily({ realm: boss.realm }) === realmFamily(player));
  // 保留原保底：最低境界活跃者的实际小境界；其他玩家按大境界中期生成。
  if (!represented(active[0])) return active[0].realm;
  const uncovered = active.find(player => !represented(player));
  return middleRealm((uncovered ?? pick(active, random)).realm);
}

function refreshBosses(ctx) {
  const config = encounterData.boss;
  const interval = config.intervalMinutes * MINUTE;
  const boundary = Math.floor(ctx.now / interval) * interval;
  const last = ctx.world.bossGeneratedAt;
  if (last !== null && last >= boundary) return;
  const periods = last === null ? 1 : Math.floor((boundary - last) / interval);
  ctx.world.bossGeneratedAt = boundary;
  const date = dayKey(ctx.now);
  const active = ctx.store.list(ctx.groupId).filter(player => player.signDate === date);
  active.sort((left, right) => left.realm - right.realm || left.exp - right.exp || left.userId.localeCompare(right.userId));
  if (active.length === 0) return;
  const count = Math.min(periods, config.limit - ctx.world.bosses.length);
  for (let i = 0; i < count; i++) {
    const realm = bossRealm(active, ctx.world.bosses, ctx.random);
    const exp = data.realms[realm].exp;
    const maxHp = Math.floor(exp * config.multipliers.hp);
    ctx.world.bosses.push({
      name: pick(config.names, ctx.random), realm, hp: maxHp, maxHp,
      mp: Math.floor(exp * config.multipliers.mp),
      attack: Math.floor(exp * config.multipliers.attack),
      money: Math.floor(exp * config.multipliers.money)
    });
  }
}

function itemDrop(kind, player, riftRank, random) {
  const candidates = [];
  const equipment = kind === 'weapon' || kind === 'armor';
  // 原版“功法概率设置.json”缺失：功法/神通改用悬赏相同的0..6 rank差筛选，
  // 不伪造品级概率表；法器/防具仍采用秘境增幅rank与0..30原窗口。
  const rank = playerRank(player) - (equipment ? riftRank : 0);
  const window = equipment ? 30 : 6;
  for (const item of items.values()) {
    const difference = Number(item.rank) - rank;
    if (item.kind === kind && difference >= 0 && difference <= window) candidates.push(item);
  }
  return candidates.length === 0 ? null : pick(candidates, random);
}

function grantMoney(player, amount) {
  player.money += amount;
  return `获得${amount}灵石。`;
}

function riftTreasure(ctx, snapshot) {
  const kind = weighted(encounterData.rift.treasureWeights, ctx.random);
  const labels = { technique: '功法', skill: '神通', weapon: '法器', armor: '防具' };
  if (kind === 'money') {
    const money = (snapshot.rank + integer(1, 10, ctx.random)) * encounterData.rift.moneyBase;
    return `搜寻秘境宝藏，${grantMoney(ctx.player, money)}`;
  }
  const item = itemDrop(kind, ctx.player, snapshot.rank, ctx.random);
  if (!item) return `搜寻${labels[kind]}，当前rank窗口没有可掉落物品，本次未获得物品。`;
  if ((kind === 'technique' || kind === 'skill') && integer(0, 100, ctx.random) > Math.min(100, 60 + 5 * snapshot.rank)) {
    return `争夺${labels[kind]}失败，${grantMoney(ctx.player, encounterData.rift.moneyBase / 2)}`;
  }
  addItem(ctx.player, item.id);
  return `搜寻秘境宝藏，获得${item.level}·${item.name}×1（${labels[kind]}），已收入背包。`;
}

function riftLoss(ctx) {
  const config = encounterData.rift;
  const player = ctx.player;
  const kind = weighted(config.lossWeights, ctx.random);
  const value = pick(config.lossValues[kind], ctx.random);
  let message;
  if (kind === 'exp') {
    const loss = Math.floor(player.exp * value);
    player.exp -= loss;
    player.hp = Math.max(1, player.hp - Math.floor(loss / 2));
    player.mp = Math.max(1, player.mp - loss);
    clampVitals(player);
    message = `遭遇秘境毒瘴，损失${loss}修为，气血真元随之受损。`;
  } else if (kind === 'hp') {
    const oldHp = player.hp;
    player.hp = Math.max(1, player.hp - Math.floor(player.exp / 2 * value));
    message = `遭遇秘境毒瘴，损失${oldHp - player.hp}气血。`;
  } else {
    // 修复旧代码把“灵石损失”误入掉血分支：按原表金额扣钱，不允许负余额。
    const loss = Math.min(player.money, value);
    player.money -= loss;
    message = `遭遇秘境劫掠，损失${loss}灵石。`;
  }
  return `${message}\n${grantMoney(player, config.moneyBase / 2)}`;
}

function writeBattleVitals(player, result) {
  player.hp = Math.max(1, result.attacker.hp);
  player.mp = result.attacker.mp;
  clampVitals(player);
}

function riftBattle(ctx, snapshot) {
  const config = encounterData.rift.boss;
  const exp = ctx.player.exp;
  const maxHp = Math.floor(exp * pick(config.hp, ctx.random));
  const boss = {
    name: pick(config.names, ctx.random), hp: maxHp, maxHp,
    mp: exp * config.mp, attack: Math.floor(exp * pick(config.attack, ctx.random))
  };
  const result = fight(playerFighter(ctx.player), bossFighter(boss), ctx.random);
  writeBattleVitals(ctx.player, result);
  let reward;
  if (result.winner === 'attacker') {
    const gain = addExp(ctx.player, Math.floor(exp * pick(config.expRewards, ctx.random)));
    // 保留原(riftRank+50-playerRank)倍率；修复低境界胜利奖励为负的缺陷。
    const money = Math.max(0, snapshot.rank + 50 - playerRank(ctx.player)) * config.moneyRewardBase;
    reward = `击败${boss.name}，获得${gain}修为，${grantMoney(ctx.player, money)}`;
  } else {
    reward = `${result.winner === null ? '久战未决，退出秘境' : `不敌${boss.name}，重伤逃遁`}，${grantMoney(ctx.player, encounterData.rift.moneyBase / 2)}`;
  }
  return `${result.report}\n${reward}\n当前气血${ctx.player.hp}、真元${ctx.player.mp}。`;
}

function settleRift(ctx) {
  const activity = ctx.player.activity;
  if (activity?.kind !== 'rift') throw new GameError('你没有正在探索的秘境，请先发送“秘境探索”。');
  const adventure = ctx.player.riftAdventure;
  if (adventure?.status === 'judging') throw new GameError('本轮秘境行动仍在判定中，请稍后重试。');
  const until = activity.startedAt + activity.rift.time * MINUTE;
  if (ctx.now < until) throw new GameError(`${activity.rift.name}探索还需${remaining(until, ctx.now)}分钟；也可以直接回复当前场景行动。`);
  const snapshot = activity.rift;
  const before = { exp: ctx.player.exp, money: ctx.player.money, hp: ctx.player.hp, mp: ctx.player.mp };
  const event = weighted(encounterData.rift.eventWeights, ctx.random);
  let message;
  if (event === 'nothing') message = `未寻得奇遇，${grantMoney(ctx.player, encounterData.rift.moneyBase / 2)}`;
  else if (event === 'treasure') message = riftTreasure(ctx, snapshot);
  else message = weighted(encounterData.rift.battleWeights, ctx.random) === 'boss'
    ? riftBattle(ctx, snapshot) : riftLoss(ctx);
  ctx.player.activity = null;
  recordJourney(ctx.player, 'rift', ctx.now, {
    name: snapshot.name, event, expDelta: ctx.player.exp - before.exp,
    moneyDelta: ctx.player.money - before.money, hpDelta: ctx.player.hp - before.hp, mpDelta: ctx.player.mp - before.mp
  });
  const result = `${snapshot.name}探索结算：\n${message}`;
  if (adventure && ['awaiting', 'judging'].includes(adventure.status)) {
    adventure.status = 'settled';
    adventure.pendingAction = null;
    rememberAdventure(adventure, result);
  }
  return result;
}

function evilBossDefense(boss, random) {
  // 原版高境界邪魔承伤倍率为0.40..0.90；低阶及秘境妖兽无减伤。
  if (boss.realm === data.realms.length - 1 || playerRank({ realm: middleRealm(boss.realm) }) <= 19) {
    return 1 - integer(40, 90, random) / 100;
  }
  return 0;
}

function fightEvilBoss(ctx, index) {
  const boss = ctx.world.bosses[index];
  if (!boss) throw new GameError('邪魔编号无效，请先发送“邪魔查询”。');
  requireHealthy(ctx.player);
  const player = ctx.player;
  const beforeHp = boss.hp;
  const battleBoss = { ...boss };
  let scaling = '';
  if (middleRealm(player.realm) > middleRealm(boss.realm)) {
    const exp = data.realms[player.realm].exp;
    const maxHp = Math.floor(exp * encounterData.boss.multipliers.hp);
    battleBoss.hp = Math.floor(boss.hp / boss.maxHp * maxHp);
    battleBoss.maxHp = maxHp;
    battleBoss.attack = Math.floor(exp * encounterData.boss.multipliers.attack);
    scaling = `境界高于邪魔，按${data.realms[player.realm].name}临时提升其气血攻击，剩余气血比例保留。\n`;
  }
  const result = fight(playerFighter(player), bossFighter(battleBoss, evilBossDefense(boss, ctx.random)), ctx.random);
  writeBattleVitals(player, result);
  const killed = result.winner === 'attacker';
  const damage = result.attacker.damageDealt;
  const money = killed ? boss.money : Math.floor(boss.money * damage / battleBoss.hp);
  boss.money -= money;
  // 高阶玩家战后还原原Boss尺度；非击杀时至少留1HP，不把取整误当击杀。
  boss.hp = killed ? 0 : Math.max(1, Math.floor(result.defender.hp / battleBoss.maxHp * boss.maxHp));
  const points = Math.max(2, Math.floor(damage / battleBoss.maxHp * (30 + 2 * boss.realm)));
  player.bossPoints += points;
  player.money += money;
  const gain = addExp(player, Math.floor(money / 4));
  let drop = '无';
  if (killed) {
    ctx.world.bosses.splice(index, 1);
    const id = pick(encounterData.boss.recoveryPills, ctx.random);
    addItem(player, id);
    drop = `${items.get(id).name}×1`;
  }
  recordJourney(player, 'boss', ctx.now, { name: boss.name, killed, damage, expGain: gain, moneyGain: money, hpRemaining: player.hp });
  return `${scaling}${result.report}\n${killed ? `击杀邪魔${boss.name}` : result.winner === null ? '久战平局，邪魔继续留在本群' : '不敌邪魔，重伤逃遁'}。\n实际伤害${damage}${scaling ? '（临时提升后的尺度）' : ''}；邪魔气血${beforeHp}→${boss.hp}/${boss.maxHp}。\n获得${money}灵石、${gain}修为、${points}积分；物品：${drop}。\n当前气血${player.hp}、真元${player.mp}；个人积分${player.bossPoints}。`;
}

function duel(ctx) {
  if (typeof ctx.targetId !== 'string' || !ctx.targetId.trim()) throw new GameError('切磋需要明确@对象，由调用方传入其稳定用户ID targetId；不按昵称寻找。');
  if (ctx.targetId === ctx.userId) throw new GameError('不能与自己切磋。');
  const target = ctx.store.get(ctx.groupId, ctx.targetId);
  if (!target) throw new GameError('切磋对象尚未在本群踏入仙途。');
  const until = ctx.player.lastDuelAt === null ? 0 : ctx.player.lastDuelAt + MINUTE;
  if (ctx.now < until) throw new GameError(`切磋冷却中，还需${Math.ceil((until - ctx.now) / 1000)}秒。`);
  const result = fight(playerFighter(ctx.player), playerFighter(target), ctx.random);
  ctx.player.lastDuelAt = ctx.now;
  return `切磋：${ctx.player.name}先手对阵${target.name}\n${result.report}\n切磋不写回气血真元、无奖励；发起者60秒后可再次切磋。`;
}

function pointsMenu(player) {
  const rows = encounterData.pointShop.map((good, index) => `${index + 1}. ${items.get(good.id).name}×1：${good.cost}积分`);
  return `个人邪魔积分：${player.bossPoints}\n${rows.join('\n')}\n发送“积分兑换 编号”兑换；炼丹炉用于洞天炼丹。`;
}

function handleEncounters(ctx) {
  if (ctx.answer === true) return handleRiftAnswer(ctx);
  if (!recognizesEncounters(ctx.text)) return null;
  requirePlayer(ctx.player);
  refreshRift(ctx);
  refreshBosses(ctx);
  if (ctx.text.startsWith('切磋')) return duel(ctx);
  if (ctx.text === '秘境查询') {
    const rift = ctx.world.rift;
    const activity = ctx.player.activity;
    const adventure = ctx.player.riftAdventure;
    const current = activity?.kind === 'rift'
      ? adventure && ['awaiting', 'judging'].includes(adventure.status)
        ? `\n正在探索${activity.rift.name}：互动进度${adventure.history.length}/${adventure.maxRounds}幕，${adventure.status === 'judging' ? '行动判定中' : '直接回复当前行动'}；${remaining(activity.startedAt + activity.rift.time * MINUTE, ctx.now)}分钟后仍可“秘境结算”。`
        : `\n正在探索${activity.rift.name}：${remaining(activity.startedAt + activity.rift.time * MINUTE, ctx.now)}分钟后可“秘境结算”（以进入快照为准）。`
      : '';
    return `本群秘境：${rift.name}（rank增幅${rift.rank}）\n群共享剩余${rift.count}次，传统结算需${rift.time}分钟；每日北京时间14:00刷新。\n发送“秘境探索”进入三幕互动冒险；可重复参与，无个人每日次数限制。${current}`;
  }
  if (ctx.text === '秘境探索') {
    requireIdle(ctx.player);
    const trial = ctx.player.breakthroughTrial;
    if (trial && ['awaiting', 'judging', 'qualified'].includes(trial.status)) {
      throw new GameError('当前突破尚未结束，请先完成或发送“取消突破”。');
    }
    const rift = ctx.world.rift;
    if (rift.count <= 0) throw new GameError('本群秘境共享次数已耗尽，等待下一次北京时间14:00刷新。');
    rift.count--;
    ctx.player.activity = {
      kind: 'rift', label: '秘境探索', startedAt: ctx.now, finishCommand: '秘境探索终止',
      rift: { name: rift.name, rank: rift.rank, time: rift.time }
    };
    const prompt = startRiftAdventure(ctx.player, ctx.player.activity);
    return `进入${rift.name}，本群共享剩余${rift.count}次。\n${prompt}\n可用“秘境探索终止”退出，次数不返还、无奖励。`;
  }
  if (ctx.text === '秘境结算') return settleRift(ctx);
  if (ctx.text === '秘境探索终止') {
    if (ctx.player.activity?.kind !== 'rift') throw new GameError('你没有正在探索的秘境。');
    const name = ctx.player.activity.rift.name;
    const adventure = ctx.player.riftAdventure;
    ctx.player.activity = null;
    if (adventure && ['awaiting', 'judging'].includes(adventure.status)) {
      adventure.status = 'cancelled';
      adventure.pendingAction = null;
      rememberAdventure(adventure, `已终止${name}探索，无奖励，群共享次数不返还。`);
    }
    return `已终止${name}探索，无奖励，群共享次数不返还。`;
  }
  if (ctx.text === '邪魔查询') {
    const bosses = ctx.world.bosses;
    const description = bosses.length ? bosses.map((boss, index) =>
      `${index + 1}. ${boss.name} · ${data.realms[boss.realm].name} · 气血${boss.hp}/${boss.maxHp} · 攻击${boss.attack} · 剩余灵石${boss.money}`
    ).join('\n') : '暂无邪魔；本群今日签到玩家活跃后，下一30分钟批次生成。';
    return `本群邪魔（${bosses.length}/${encounterData.boss.limit}）\n${description}\n每30分钟惰性生成，优先照顾签到活跃玩家境界；发送“讨伐邪魔1”讨伐。`;
  }
  if (ctx.text.startsWith('讨伐邪魔')) {
    const match = ctx.text.match(/^讨伐邪魔\s*(\d+)$/u);
    if (!match || !Number.isSafeInteger(Number(match[1])) || Number(match[1]) < 1) throw new GameError('格式：讨伐邪魔1（或“讨伐邪魔 1”）。');
    return fightEvilBoss(ctx, Number(match[1]) - 1);
  }
  if (ctx.text === '我的积分' || ctx.text === '积分查询') return pointsMenu(ctx.player);
  const match = ctx.text.match(/^积分兑换\s*(\d+)$/u);
  const index = match ? Number(match[1]) - 1 : -1;
  const good = encounterData.pointShop[index];
  if (!good) throw new GameError(`商品编号无效，请发送“我的积分”查看1～${encounterData.pointShop.length}号商品。`);
  if (ctx.player.bossPoints < good.cost) throw new GameError(`积分不足，兑换${items.get(good.id).name}需${good.cost}积分，当前${ctx.player.bossPoints}。`);
  ctx.player.bossPoints -= good.cost;
  addItem(ctx.player, good.id);
  return `消耗${good.cost}积分，兑换${items.get(good.id).name}×1，剩余${ctx.player.bossPoints}积分。`;
}

module.exports = { handleEncounters, resolveRiftReview };
