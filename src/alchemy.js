'use strict';

const {
  data, items, GameError, addItem, integer, positiveInteger, removeItem,
  requirePlayer, safeAdd
} = require('./rules');
const { recognizesAlchemy } = require('./input');

const COLLECTION_COSTS = [500, 1_000, 2_000];
const FIRE_COSTS = [1_000, 2_000];
const PILLS = Object.entries(data.pills).filter(([, pill]) => pill.elixir_config);
const HELP = '炼丹：先从灵田取得药材，并从邪魔积分商店兑换炼丹炉。发送“炼丹”检测可用丹方；按返回的“配方 主药…药引…辅药…丹炉…”炼制。我的炼丹信息、升级收取等级、升级丹药控火、炼丹考核开始、炼丹考核解答 药材1数量 药材2数量 药材3数量。';

function herbRole(item, role) {
  if (item.kind !== 'herb') throw new GameError(`${item.name}不是药材，不能作为${role}。`);
  return item[role];
}

function formulaFor(main, mainCount, auxiliary, auxiliaryCount) {
  const values = {};
  const mainRule = herbRole(main, '主药');
  const auxiliaryRule = herbRole(auxiliary, '辅药');
  values[String(mainRule.type)] = mainRule.power * mainCount;
  values[String(auxiliaryRule.type)] = auxiliaryRule.power * auxiliaryCount;
  const keys = Object.keys(values).sort();
  const matches = PILLS.filter(([, pill]) => {
    const formulaKeys = Object.keys(pill.elixir_config).sort();
    return keys.length === formulaKeys.length && keys.every((key, index) => key === formulaKeys[index])
      && keys.every(key => values[key] >= pill.elixir_config[key]);
  });
  matches.sort((left, right) => Math.max(...Object.values(right[1].elixir_config)) - Math.max(...Object.values(left[1].elixir_config)));
  return matches[0] ?? null;
}

function isBalanced(main, mainCount, catalyst, catalystCount) {
  const left = herbRole(main, '主药').h_a_c;
  const right = herbRole(catalyst, '药引').h_a_c;
  return left.type * left.power * mainCount + right.type * right.power * catalystCount === 0;
}

function recommendations(player) {
  const herbs = Object.entries(player.inventory)
    .filter(([id, count]) => count > 0 && items.get(id)?.kind === 'herb')
    .slice(0, 25).map(([id, count]) => ({ item: items.get(id), count }));
  const furnace = Object.entries(player.inventory).map(([id, count]) => count > 0 ? items.get(id) : null)
    .filter(item => item?.kind === 'furnace').sort((a, b) => a.id.localeCompare(b.id))[0];
  if (!herbs.length) throw new GameError('背包中没有药材，先经营灵田。');
  if (!furnace) throw new GameError('背包中没有炼丹炉，可在邪魔积分商店兑换。');
  const best = new Map();
  for (const main of herbs) {
    for (let mainCount = 1; mainCount <= Math.min(5, main.count); mainCount++) {
      const heat = herbRole(main.item, '主药').h_a_c;
      const mainHeat = heat.type * heat.power * mainCount;
      for (const catalyst of herbs) {
        if (catalyst.item.id === main.item.id) continue;
        const cold = herbRole(catalyst.item, '药引').h_a_c;
        const coefficient = cold.type * cold.power;
        const catalystCount = coefficient === 0 ? (mainHeat === 0 ? 1 : 0) : -mainHeat / coefficient;
        if (!Number.isInteger(catalystCount) || catalystCount < 1 || catalystCount > Math.min(5, catalyst.count)) continue;
        for (const auxiliary of herbs) {
          for (let auxiliaryCount = 1; auxiliaryCount <= Math.min(5, auxiliary.count); auxiliaryCount++) {
            const match = formulaFor(main.item, mainCount, auxiliary.item, auxiliaryCount);
            if (!match) continue;
            const [pillId, pill] = match;
            const counts = new Map();
            for (const [id, amount] of [[main.item.id, mainCount], [catalyst.item.id, catalystCount], [auxiliary.item.id, auxiliaryCount]]) {
              counts.set(id, (counts.get(id) ?? 0) + amount);
            }
            if ([...counts].some(([id, amount]) => (player.inventory[id] ?? 0) < amount)) continue;
            const total = mainCount + catalystCount + auxiliaryCount;
            if (!best.has(pillId) || total < best.get(pillId).total) {
              best.set(pillId, { pill, total, text: `配方 主药${main.item.name}${mainCount} 药引${catalyst.item.name}${catalystCount} 辅药${auxiliary.item.name}${auxiliaryCount} 丹炉${furnace.name}` });
            }
          }
        }
      }
    }
  }
  return [...best.values()].sort((a, b) => a.pill.rank - b.pill.rank || a.total - b.total).slice(0, 12);
}

function parseRecipe(text) {
  const match = text.match(/^配方\s*主药\s*(\S+?)\s*(\d+)\s*药引\s*(\S+?)\s*(\d+)\s*辅药\s*(\S+?)\s*(\d+)\s*丹炉\s*(\S+)$/u);
  if (!match) throw new GameError('格式：配方 主药恒心草3 药引罗犀草3 辅药红绫草3 丹炉陨铁炉。');
  const main = items.get(match[1]) ?? [...items.values()].find(item => item.name === match[1]);
  const catalyst = items.get(match[3]) ?? [...items.values()].find(item => item.name === match[3]);
  const auxiliary = items.get(match[5]) ?? [...items.values()].find(item => item.name === match[5]);
  const furnace = items.get(match[7]) ?? [...items.values()].find(item => item.name === match[7]);
  if (!main || !catalyst || !auxiliary || !furnace) throw new GameError('配方中存在未知药材或炼丹炉。');
  if (furnace.kind !== 'furnace') throw new GameError(`${furnace.name}不是炼丹炉。`);
  return {
    main, mainCount: positiveInteger(match[2]), catalyst, catalystCount: positiveInteger(match[4]),
    auxiliary, auxiliaryCount: positiveInteger(match[6]), furnace
  };
}

function makePill(player, recipe) {
  herbRole(recipe.main, '主药');
  herbRole(recipe.catalyst, '药引');
  herbRole(recipe.auxiliary, '辅药');
  if ((player.inventory[recipe.furnace.id] ?? 0) < 1) throw new GameError(`背包中没有${recipe.furnace.name}。`);
  if (!isBalanced(recipe.main, recipe.mainCount, recipe.catalyst, recipe.catalystCount)) throw new GameError('主药与药引冷热失衡，炼丹失败；未扣药材。');
  const match = formulaFor(recipe.main, recipe.mainCount, recipe.auxiliary, recipe.auxiliaryCount);
  if (!match) throw new GameError('药力与药性不满足任何丹方；未扣药材。');
  const required = new Map();
  for (const [item, count] of [[recipe.main, recipe.mainCount], [recipe.catalyst, recipe.catalystCount], [recipe.auxiliary, recipe.auxiliaryCount]]) {
    required.set(item.id, (required.get(item.id) ?? 0) + count);
  }
  for (const [id, count] of required) if ((player.inventory[id] ?? 0) < count) throw new GameError(`背包中的${items.get(id).name}不足，需要${count}株。`);
  const [pillId, pill] = match;
  const amount = 1 + recipe.furnace.buff + player.alchemy.fireLevel;
  for (const [id, count] of required) removeItem(player, id, count);
  addItem(player, pillId, amount);
  const record = player.alchemy.records[pillId] ??= { name: pill.name, count: 0 };
  const experienced = Math.min(amount, Math.max(0, pill.mix_all - record.count));
  const gained = pill.mix_exp * experienced;
  player.alchemy.exp = safeAdd(player.alchemy.exp, gained, '炼丹经验');
  record.count = safeAdd(record.count, amount, '炼丹记录');
  return `炼成${pill.name}×${amount}，消耗药材${[...required].map(([id, count]) => `${items.get(id).name}×${count}`).join('、')}；获得${gained}炼丹经验。`;
}

function createExam(random) {
  const pool = Object.keys(data.herbs);
  const selected = [];
  for (let i = 0; i < 3; i++) selected.push(pool.splice(integer(0, pool.length - 1, random), 1)[0]);
  for (let attempt = 0; attempt < 100; attempt++) {
    const nature = [integer(2, 9, random), integer(2, 9, random), integer(2, 9, random)];
    const power = [integer(2, 9, random), integer(2, 9, random), integer(2, 9, random)];
    const solutions = [];
    for (let a = 1; a <= 9; a++) for (let b = 1; b <= 9; b++) for (let c = 1; c <= 9; c++) {
      if (nature[0] * a - nature[1] * b + nature[2] * c === 0) solutions.push([a, b, c]);
    }
    if (!solutions.length) continue;
    const total = Math.max(...solutions.map(solution => solution.reduce((sum, count, index) => sum + count * power[index], 0)));
    return { herbs: selected.map((id, index) => ({ id, name: items.get(id).name, nature: nature[index], power: power[index] })), total };
  }
  throw new Error('无法生成可解炼丹考核题。');
}

function examText(problem) {
  const [main, catalyst, auxiliary] = problem.herbs;
  return `炼丹考核：主药${main.name}（热${main.nature}、药力${main.power}），药引${catalyst.name}（寒${catalyst.nature}、药力${catalyst.power}），辅药${auxiliary.name}（热${auxiliary.nature}、药力${auxiliary.power}）。每种1～9株，药性平衡且总药力至少${problem.total}。\n发送“炼丹考核解答 ${main.name}数量 ${catalyst.name}数量 ${auxiliary.name}数量”。`;
}

function answerExam(player, text, random) {
  const problem = player.alchemy.exam.current;
  if (!problem) throw new GameError('当前没有炼丹考核题，请先发送“炼丹考核开始”。');
  const match = text.match(/^炼丹考核解答\s+(\S+?)(\d+)\s+(\S+?)(\d+)\s+(\S+?)(\d+)$/u);
  if (!match) throw new GameError('按题目顺序填写，例如：炼丹考核解答 恒心草1 红绫草2 罗犀草3。');
  const names = [match[1], match[3], match[5]];
  const counts = [match[2], match[4], match[6]].map(value => positiveInteger(value));
  if (counts.some(count => count > 9)) throw new GameError('每种药材只能使用1～9株。');
  if (names.some((name, index) => name !== problem.herbs[index].name)) throw new GameError('请按题目中的主药、药引、辅药顺序作答。');
  const balance = counts[0] * problem.herbs[0].nature - counts[1] * problem.herbs[1].nature + counts[2] * problem.herbs[2].nature;
  const power = counts.reduce((sum, count, index) => sum + count * problem.herbs[index].power, 0);
  if (balance !== 0 || power < problem.total) return `回答错误：当前药性差${balance}，总药力${power}/${problem.total}。题目保留，可继续作答。`;
  const reward = problem.herbs[integer(0, problem.herbs.length - 1, random)];
  addItem(player, reward.id);
  player.alchemy.exam.points = safeAdd(player.alchemy.exam.points, 10, '炼丹考核积分');
  player.alchemy.exam.current = null;
  return `回答正确，炼丹考核积分+10，获得${reward.name}×1；当前积分${player.alchemy.exam.points}。`;
}

function handleAlchemy(ctx) {
  if (!recognizesAlchemy(ctx.text)) return null;
  if (ctx.text === '炼丹帮助' || ctx.text === '炼丹配方帮助') return HELP;
  requirePlayer(ctx.player);
  if (ctx.text === '我的炼丹信息') {
    const records = Object.values(ctx.player.alchemy.records);
    return `${ctx.player.name}的炼丹信息\n药材收取等级：${ctx.player.alchemy.collectionLevel}/3\n丹药控火等级：${ctx.player.alchemy.fireLevel}/2\n炼丹经验：${ctx.player.alchemy.exp}\n考核积分：${ctx.player.alchemy.exam.points}\n${records.length ? records.map(record => `${record.name}：炼成${record.count}枚`).join('\n') : '尚无炼丹记录。'}`;
  }
  if (ctx.text === '升级收取等级' || ctx.text === '升级丹药控火') {
    if (ctx.text === '升级收取等级' && !ctx.player.estate) throw new GameError('尚无洞天福地，不能升级药材收取等级。');
    const key = ctx.text === '升级收取等级' ? 'collectionLevel' : 'fireLevel';
    const costs = key === 'collectionLevel' ? COLLECTION_COSTS : FIRE_COSTS;
    const current = ctx.player.alchemy[key];
    if (current >= costs.length) throw new GameError('该炼丹能力已经达到最高等级。');
    const cost = costs[current];
    if (ctx.player.alchemy.exp < cost) throw new GameError(`升级需要${cost}炼丹经验，当前${ctx.player.alchemy.exp}。`);
    ctx.player.alchemy.exp -= cost;
    ctx.player.alchemy[key]++;
    return `${key === 'collectionLevel' ? '药材收取' : '丹药控火'}升至${ctx.player.alchemy[key]}级，消耗${cost}炼丹经验。`;
  }
  if (ctx.text === '炼丹') {
    const rows = recommendations(ctx.player);
    if (!rows.length) throw new GameError('当前药材无法组成丹方；继续收取不同药材后再试。');
    return `检测到可用丹方（最多显示12种）：\n${rows.map(row => `${row.pill.name}：${row.text}`).join('\n')}`;
  }
  if (ctx.text.startsWith('配方')) return makePill(ctx.player, parseRecipe(ctx.text));
  if (ctx.text === '炼丹考核开始') {
    ctx.player.alchemy.exam.current ??= createExam(ctx.random);
    return examText(ctx.player.alchemy.exam.current);
  }
  return answerExam(ctx.player, ctx.text, ctx.random);
}

module.exports = { handleAlchemy, formulaFor, isBalanced };
