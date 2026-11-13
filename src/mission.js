'use strict';

const {
  data, items, GameError, MINUTE, integer, pick, dayKey, addExp, addItem,
  requirePlayer, requireIdle, spend, remaining, realmFamily, playerRank
} = require('./rules');
const { recordJourney } = require('./journey');
const { recognizesMission } = require('./input');

const MAX_REALM = data.realms.findIndex(realm => realm.name === data.missionConfig.max_level);

function generateBoard(player, now, random) {
  const family = realmFamily(player);
  if (player.realm > MAX_REALM) throw new GameError(`任务堂仅开放至${data.missionConfig.max_level}。`);
  const entries = Object.entries(data.missions).map(([kind, families]) => {
    const [name, template] = pick(Object.entries(families[family]), random);
    const reward = data.missionRewards[family][template.level];
    const rate = Math.min(100, Math.floor(player.exp / reward.needexp * 100));
    let multiplier = 1;
    if (rate >= 100) {
      let exp = player.exp;
      let steps = 1;
      while (exp > reward.needexp) {
        exp /= 1.5;
        steps++;
      }
      multiplier = Math.round(Math.max(0.5, 1 - steps * 0.05) * 100) / 100;
    }
    const itemKind = pick(['technique', 'skill', 'pill'], random);
    const rank = playerRank(player);
    const candidates = [...items.values()].filter(item => item.kind === itemKind && Number(item.rank) >= rank && Number(item.rank) - rank <= 6);
    return {
      name, kind, difficulty: template.level, rate,
      minutes: Math.floor(reward.time * multiplier), exp: reward.award,
      itemId: candidates.length ? pick(candidates, random).id : null
    };
  });
  return { date: dayKey(now), entries };
}

function boardText(board) {
  return `悬赏令\n${board.entries.map((entry, i) => `${i + 1}. ${entry.name}（${entry.kind}·${entry.difficulty}）\n   ${entry.minutes}分钟 · 成功率${entry.rate}% · 修为${entry.exp}${entry.rate === 100 ? '（大成功翻倍）' : ''}`).join('\n')}\n发送“悬赏令接取 编号”开始。失败仍得基础修为，成功可获得功法、神通或丹药。`;
}

function handleMission(context) {
  const { player, text, now, random } = context;
  const accept = text.match(/^悬赏令接取\s*([1-3])$/u);
  if (!recognizesMission(text)) return null;
  requirePlayer(player);
  if (text.startsWith('悬赏令接取') && !accept) throw new GameError('格式：悬赏令接取 1/2/3。');
  if (text === '悬赏令帮助') {
    return '悬赏令：查看三项任务；悬赏令接取1：开始；悬赏令结算：到时领奖；悬赏令终止：花50000灵石放弃。\n每天可免费刷新3次，其后每次100000灵石。接取不消耗背包悬赏令，与原版旧任务堂规则一致。';
  }
  const activity = player.activity;
  if (text === '悬赏令结算' || text === '悬赏令终止' || text === '悬赏令放弃') {
    if (activity?.kind !== 'mission') throw new GameError('你当前没有进行中的悬赏任务。');
    if (text !== '悬赏令结算') {
      spend(player, data.missionConfig.give_up_cost);
      player.activity = null;
      return `消耗${data.missionConfig.give_up_cost}灵石，已终止悬赏。`;
    }
    if (now < activity.readyAt) throw new GameError(`悬赏【${activity.task.name}】还需${remaining(activity.readyAt, now)}分钟。`);
    const task = activity.task;
    const success = integer(1, 100, random) <= task.rate;
    const bigSuccess = success && task.rate >= 100;
    const gain = addExp(player, task.exp * (bigSuccess ? 2 : 1));
    let loot = '';
    if (success && task.itemId !== null) {
      addItem(player, task.itemId);
      loot = `，获得${items.get(task.itemId).name}×1`;
    }
    player.activity = null;
    recordJourney(player, 'mission', now, { name: task.name, success, bigSuccess, expGain: gain, itemId: success ? task.itemId : null });
    return `悬赏【${task.name}】${bigSuccess ? '大成功' : success ? '成功' : '失败'}，获得${gain}修为${loot}。`;
  }

  if (text === '悬赏令' && activity?.kind === 'mission') {
    return `悬赏【${activity.task.name}】进行中，还需${remaining(activity.readyAt, now)}分钟；发送“悬赏令结算”领奖。`;
  }
  if (text === '悬赏令刷新') {
    const cost = player.daily.refreshes >= data.missionConfig.free_refresh_count ? data.missionConfig.refresh_cost : 0;
    spend(player, cost);
    player.board = generateBoard(player, now, random);
    player.daily.refreshes++;
    return `已刷新，消耗${cost}灵石；今日剩余免费刷新${Math.max(0, data.missionConfig.free_refresh_count - player.daily.refreshes)}次。\n${boardText(player.board)}`;
  }
  // 跨日仅更新待选列表，绝不取消正在执行的任务。
  if (!player.board || player.board.date !== dayKey(now) || player.board.entries.length === 0) {
    player.board = generateBoard(player, now, random);
  }
  if (accept) {
    requireIdle(player);
    if (player.realm > MAX_REALM) throw new GameError(`任务堂仅开放至${data.missionConfig.max_level}。`);
    const next = data.realms[player.realm + 1];
    if (next && player.exp >= Math.floor(next.exp * 1.5)) throw new GameError('修为已达当前境界上限，请先突破再接取悬赏。');
    const index = Number(accept[1]) - 1;
    if (index >= player.board.entries.length) throw new GameError('没有这个编号，请先发送“悬赏令”查看当前列表。');
    const [task] = player.board.entries.splice(index, 1);
    player.activity = {
      kind: 'mission', label: `悬赏【${task.name}】`, startedAt: now,
      readyAt: now + task.minutes * MINUTE, finishCommand: '悬赏令结算', task
    };
    return `已接取【${task.name}】，${task.minutes}分钟后发送“悬赏令结算”领取奖励。`;
  }
  return boardText(player.board);
}

module.exports = { handleMission };
