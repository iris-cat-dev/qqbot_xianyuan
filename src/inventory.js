'use strict';

const {
  data, items, GameError, positiveInteger, safeAdd, stats, clampVitals,
  addItem, removeItem, findItem, parseItemCount, requirePlayer, spend, playerRank
} = require('./rules');
const { matchInventory } = require('./input');

const SLOT_NAMES = { weapon: '法器', armor: '防具', technique: '主功法', skill: '神通' };
const SLOT_ALIASES = {
  法器: 'weapon', 武器: 'weapon', 防具: 'armor', 护具: 'armor', 防具装备: 'armor',
  功法: 'technique', 主功法: 'technique', 神通: 'skill'
};
const PILL_EFFECTS = new Set(['hp', 'all', 'level_up_rate', 'level_up_big', 'atk_buff', 'level_up']);
const MARKET_HELP = '坊市上架 物品名/ID 整批总价 [数量]（默认1件，最低10000灵石，每人最多10单）；坊市查询；坊市购买 编号；坊市下架 编号。买家买下整批，卖家收款扣10%税。';


function checkStock(player, item, count) {
  if ((player.inventory[item.id] ?? 0) < count) throw new GameError(`背包中的${item.name}不足，需要${count}件。`);
}

function checkIncoming(player, item, count) {
  safeAdd(player.inventory[item.id] ?? 0, count, '物品数量');
}

// 完整ID优先；连写数量只接受物品名，避免把110110等数字猜成ID+数量。
function parseUse(input) {
  const value = input.trim();
  if (items.has(value) || [...items.values()].some(item => item.name === value)) {
    return parseItemCount(value);
  }
  if (/\s/u.test(value)) return parseItemCount(value);
  const candidates = [...items.values()].filter(item => value.startsWith(item.name));
  candidates.sort((a, b) => b.name.length - a.name.length);
  for (const item of candidates) {
    const suffix = value.slice(item.name.length);
    if (/^\d+$/u.test(suffix)) return { item, count: positiveInteger(suffix, '数量') };
  }
  return parseItemCount(value);
}

function percent(value) {
  return Number((value * 100).toFixed(2));
}

function pillInfo(item, player) {
  const rank = Number(item.rank);
  const boundary = item['境界'] ?? item.level;
  switch (item.buff_type) {
    case 'level_up':
      return '不能普通服用；发送“渡厄突破”消耗1颗，突破失败不损失修为。无额外丹药境界前置。';
    case 'level_up_rate':
      return `每颗增加下一次突破判定阈值${item.buff}个百分点；可批量服用。要求丹药rank≥玩家rank且差≤18（丹药rank ${rank}，玩家rank ${playerRank(player)}）。`;
    case 'level_up_big':
      return `每颗增加下一次突破判定阈值${item.buff}个百分点；每次1颗，终身最多${item.all_num}颗。仅限${boundary}，必须rank相等（${rank}）。已服${player.pillTotals[item.id] ?? 0}颗。`;
    case 'hp': {
      const coefficient = Number(((0.016 * playerRank(player) + 0.104) * item.buff).toFixed(2));
      return `仅恢复气血，不恢复真元；每颗按round((0.016×玩家rank+0.104)×${item.buff},2)×最大气血计算，当前为${percent(coefficient)}%。可批量服用；要求丹药rank≥玩家rank（${boundary}起）。`;
    }
    case 'all':
      return `每次1颗，气血和真元恢复至当前功法计算的上限；要求丹药rank≥玩家rank（${boundary}起）。`;
    case 'atk_buff':
      return `每颗永久增加基础攻击${item.buff}点，再统一计算功法和武器加成。可批量服用；要求丹药rank≥玩家rank（${boundary}起）。`;
    default:
      return '该丹药没有本次可用的服药效果。';
  }
}

function skillInfo(item) {
  let effect;
  switch (item.skill_type) {
    case 1:
      effect = `连击各段倍率：${item.atkvalue.join('、')}；休息${item.turncost}回合`;
      break;
    case 2:
      effect = `持续伤害：每回合${item.atkvalue}×攻击，持续${item.turncost}回合`;
      break;
    case 3:
      effect = `${item.bufftype === 1 ? '攻击增益' : '减伤增益'}：${percent(item.buffvalue)}%，持续${item.turncost}回合`;
      break;
    case 4:
      effect = `封印${item.turncost}回合；命中判定randint(0,100)≤${item.success}`;
      break;
    default:
      throw new Error(`未知神通类型：${item.id}`);
  }
  return `${effect}；气血消耗为当前气血的${percent(item.hpcost)}%，真元消耗为修为的${percent(item.mpcost)}%；释放判定randint(0,100)≤${item.rate}。`;
}

function itemInfo(item, player) {
  const header = `${item.name} [${item.id}] · ${SLOT_NAMES[item.kind] ?? item.type ?? '物品'}`;
  let effect;
  if (item.kind === 'pill') effect = pillInfo(item, player);
  else if (item.kind === 'technique') {
    effect = `最大气血+${percent(item.hpbuff)}%，最大真元+${percent(item.mpbuff)}%，攻击加成+${percent(item.atkbuff)}%，修炼效率+${percent(item.ratebuff)}%。`;
  } else if (item.kind === 'skill') effect = skillInfo(item);
  else if (item.kind === 'weapon') {
    const crit = Math.min(101, Math.floor(item.crit_buff * 100) + 1) / 101 * 100;
    effect = `攻击加成+${percent(item.atk_buff)}%；会心判定randint(0,100)≤${Math.floor(item.crit_buff * 100)}，实际${crit.toFixed(2)}%。`;
  } else if (item.kind === 'armor') effect = `减伤率${percent(item.def_buff)}%。`;
  else if (item.kind === 'herb') effect = `药材；主药属性${item['主药'].type}/${item['主药'].power}，药引冷热${item['药引'].h_a_c.type * item['药引'].h_a_c.power}，辅药属性${item['辅药'].type}/${item['辅药'].power}。用于“炼丹”与“配方”。`;
  else if (item.kind === 'furnace') effect = `${item.desc}；炼丹额外产出${item.buff}枚。`;
  else effect = `${item.desc ?? '特殊物品'}\n本次秘境和悬赏不消耗此物品；不能用“使用”服用或装备。`;
  return `${header}${item.kind !== 'pill' && item.level ? ` · ${item.level}` : ''}\n${effect}`;
}

function equip(player, item, count) {
  if (item.kind !== 'weapon' && item.kind !== 'armor') throw new GameError('装备只接受法器或防具；功法和神通请发送“功法修炼 物品名/ID”。');
  if (count !== 1) throw new GameError('一次只能装备1件，装备不会消耗背包物品。');
  checkStock(player, item, 1);
  const previous = player.equipment[item.kind];
  if (previous === item.id) throw new GameError(`${item.name}已经装备。`);
  player.equipment[item.kind] = item.id;
  return `已装备${SLOT_NAMES[item.kind]}：${item.name}。${previous ? `原装备${items.get(previous).name}已自动卸下。` : ''}装备保留在背包，不消耗。`;
}

function learn(player, item, count) {
  if (item.kind !== 'technique' && item.kind !== 'skill') throw new GameError('功法修炼只接受主功法或神通。');
  if (count !== 1) throw new GameError('功法或神通每次学习1本。');
  checkStock(player, item, 1);
  const previous = player.equipment[item.kind];
  if (previous === item.id) throw new GameError(`已学会${item.name}，不能重复学习。`);
  removeItem(player, item.id, 1);
  player.equipment[item.kind] = item.id;
  clampVitals(player);
  return `已学会${SLOT_NAMES[item.kind]}：${item.name}，消耗1本。${previous ? `替换${items.get(previous).name}，旧技能不返还。` : ''}\n${itemInfo(item, player)}`;
}

function usePill(player, item, count) {
  if (item.buff_type === 'level_up') throw new GameError('渡厄丹不能普通服用，请发送“渡厄突破”，突破时消耗1颗以保护修为。');
  if (!PILL_EFFECTS.has(item.buff_type)) throw new GameError('此丹药没有本次可用的服药效果。');
  checkStock(player, item, count);
  const rank = Number(item.rank);
  const userRank = playerRank(player);
  if (item.buff_type === 'level_up_big') {
    if (rank !== userRank) throw new GameError(`${item.name}仅限${item['境界'] ?? item.level}服用，丹药与玩家rank必须相等。`);
    if (count !== 1) throw new GameError(`${item.name}每次只能服用1颗。`);
    if ((player.pillTotals[item.id] ?? 0) >= item.all_num) throw new GameError(`${item.name}已达到终身${item.all_num}颗的耐药上限。`);
  } else {
    if (rank < userRank) throw new GameError(`${item.name}至少需要${item['境界'] ?? item.level}，当前境界不足。`);
    if (item.buff_type === 'level_up_rate' && rank - userRank > 18) throw new GameError(`${item.name}已不适合当前境界，丹药rank与玩家rank之差不能超过18。`);
    if (item.buff_type === 'all' && count !== 1) throw new GameError('全恢复丹药每次只服用1颗。');
  }
  const dailyUses = safeAdd(player.daily.pillUses[item.id] ?? 0, count, '每日服药计数');
  const totalUses = safeAdd(player.pillTotals[item.id] ?? 0, count, '累计服药计数');
  let message;
  let hp = player.hp;
  let mp = player.mp;
  let pillBonus = player.pillBonus;
  let attackBonus = player.attackBonus;
  switch (item.buff_type) {
    case 'hp': {
      const { maxHp } = stats(player);
      if (hp >= maxHp) throw new GameError('气血已满；此丹药只恢复气血，不能恢复真元。');
      const coefficient = Number(((0.016 * userRank + 0.104) * item.buff).toFixed(2));
      hp = Math.min(maxHp, hp + Math.floor(coefficient * maxHp * count));
      message = `气血恢复${hp - player.hp}点（${hp}/${maxHp}），真元不变。`;
      break;
    }
    case 'all': {
      const { maxHp, maxMp } = stats(player);
      if (hp >= maxHp && mp >= maxMp) throw new GameError('气血和真元已满，无须服药。');
      hp = maxHp;
      mp = maxMp;
      message = `气血和真元已恢复至${maxHp}/${maxMp}。`;
      break;
    }
    case 'level_up_rate':
    case 'level_up_big':
      pillBonus = safeAdd(pillBonus, item.buff * count, '丹药突破增益');
      message = `下一次突破判定阈值增加${item.buff * count}个百分点。`;
      break;
    case 'atk_buff':
      attackBonus = safeAdd(attackBonus, item.buff * count, '永久攻击增益');
      message = `基础攻击永久增加${item.buff * count}点（再计算装备、功法加成）。`;
      break;
  }
  removeItem(player, item.id, count);
  player.hp = hp;
  player.mp = mp;
  player.pillBonus = pillBonus;
  player.attackBonus = attackBonus;
  player.daily.pillUses[item.id] = dailyUses;
  player.pillTotals[item.id] = totalUses;
  return `服用${item.name}×${count}，${message}今日已服此丹${dailyUses}颗。`;
}

function shopItems() {
  return [...items.values()].filter(item => item.kind === 'pill' &&
    Object.hasOwn(data.pills[item.id], 'price') && Number.isSafeInteger(item.price) && item.price > 0 &&
    data.pills[item.id].status === 1 && PILL_EFFECTS.has(item.buff_type));
}

function handleMarket(ctx, action, input) {
  const { player, world, store, groupId, userId, now } = ctx;
  if (action === '查询' || !action) {
    const rows = world.market.map(listing => {
      const item = items.get(listing.itemId);
      return `${listing.id}. ${item.name} [${item.id}] ×${listing.count} · 整批${listing.price}灵石 · ${listing.sellerName}（${listing.sellerId}）`;
    });
    return `本群坊市\n${rows.length ? rows.join('\n') : '暂无挂单。'}\n${MARKET_HELP}`;
  }
  if (action === '上架') {
    const match = input.trim().match(/^(\S+)\s+(\d+)(?:\s+(\d+))?$/u);
    if (!match) throw new GameError(MARKET_HELP);
    const item = findItem(match[1]);
    const price = positiveInteger(match[2], '整批总价');
    const count = match[3] ? positiveInteger(match[3], '数量') : 1;
    if (price < 10000) throw new GameError('坊市整批总价最低10000灵石。');
    if (world.market.filter(listing => listing.sellerId === userId).length >= 10) throw new GameError('每人最多同时上架10单，请先下架或等待售出。');
    checkStock(player, item, count);
    const equipped = (item.kind === 'weapon' || item.kind === 'armor') && player.equipment[item.kind] === item.id;
    if (equipped && player.inventory[item.id] - count < 1) throw new GameError('正在装备的物品须保留1件；只能寄售多余数量，或先卸下。');
    const id = world.nextListingId;
    const nextId = safeAdd(id, 1, '坊市编号');
    removeItem(player, item.id, count);
    world.market.push({ id, sellerId: userId, sellerName: player.name, itemId: item.id, count, price, createdAt: now });
    world.nextListingId = nextId;
    return `坊市上架成功，编号${id}：${item.name}×${count}，整批总价${price}灵石；售出税金${Math.floor(price / 10)}灵石。`;
  }
  const id = positiveInteger(input.trim(), '坊市编号');
  const index = world.market.findIndex(listing => listing.id === id);
  if (index < 0) throw new GameError('没有这个坊市编号，请发送“坊市查询”。');
  const listing = world.market[index];
  const item = items.get(listing.itemId);
  if (action === '下架') {
    if (listing.sellerId !== userId) throw new GameError('只能下架自己的挂单。');
    checkIncoming(player, item, listing.count);
    addItem(player, item.id, listing.count);
    world.market.splice(index, 1);
    return `已下架编号${id}，${item.name}×${listing.count}返还背包。`;
  }
  if (listing.sellerId === userId) throw new GameError('不能购买自己的挂单，请使用“坊市下架 编号”。');
  const seller = store.get(groupId, listing.sellerId);
  if (!seller) throw new Error(`坊市卖家存档缺失：${listing.sellerId}`);
  checkIncoming(player, item, listing.count);
  const tax = Math.floor(listing.price / 10);
  const income = listing.price - tax;
  const sellerMoney = safeAdd(seller.money, income, '卖家灵石');
  spend(player, listing.price);
  addItem(player, item.id, listing.count);
  seller.money = sellerMoney;
  store.save(groupId, seller);
  world.market.splice(index, 1);
  return `购得编号${id}：${item.name}×${listing.count}，支付整批${listing.price}灵石；卖家获得${income}，税金${tax}。`;
}

function handleInventory(ctx) {
  const { text, player } = ctx;
  const inputMatch = matchInventory(text);
  if (!inputMatch) return null;
  if (/^(?:我的背包|背包)$/u.test(text)) {
    requirePlayer(player);
    const rows = Object.entries(player.inventory).map(([id, count]) => {
      const item = items.get(id);
      const equipped = (item.kind === 'weapon' || item.kind === 'armor') && player.equipment[item.kind] === id;
      return `${item.name} [${id}] ×${count}${equipped ? '（已装备1件）' : ''}`;
    });
    return `${player.name}的背包\n${rows.length ? rows.join('\n') : '空空如也。'}\n使用 名称/ID [数量]；装备 名称/ID；卸下 法器/防具/功法/神通；功法修炼 名称/ID（消耗1本，替换不返还）。\n丹药记录每日用量，不设通用10颗上限；大境界突破丹按各自终身耐药上限。所有背包物品可交易，正在装备须保留1件。`;
  }
  if (text === '我的功法') {
    requirePlayer(player);
    return ['technique', 'skill'].map(slot => player.equipment[slot] ? itemInfo(items.get(player.equipment[slot]), player) : `${SLOT_NAMES[slot]}：无`).join('\n');
  }
  const { query } = inputMatch;
  if (query) {
    requirePlayer(player);
    if (!query[1]) throw new GameError('格式：物品信息 物品名/ID，或 查询物品名。');
    return itemInfo(findItem(query[1].trim()), player);
  }
  if (text === '商店' || text === '修仙商店') {
    requirePlayer(player);
    return `修仙商店（仅原版有售价且开放的可用普通丹药）\n${shopItems().map(item => `${item.id}. ${item.name} · 每颗${item.price}灵石`).join('\n')}\n购买 名称/ID [数量]，例如“购买1101 2”。购买没有额外境界限制；服药须满足对应条件。渡厄丹用于“渡厄突破”。`;
  }
  const { market } = inputMatch;
  if (market) {
    requirePlayer(player);
    return handleMarket(ctx, market[1], market[2] ?? '');
  }
  const { transfer } = inputMatch;
  if (transfer) {
    requirePlayer(player);
    const amountText = transfer[1].trim().match(/(?:^|[^\d.+-])(\d+)$/u)?.[1];
    if (!amountText) throw new GameError('格式：送灵石 @对象 正整数数量；目标由调用方传入targetId。');
    const amount = positiveInteger(amountText, '数量');
    if (!ctx.targetId) throw new GameError('请@目标修士，由调用方传入targetId；不支持按昵称转账。');
    if (ctx.targetId === ctx.userId) throw new GameError('不能给自己转账。');
    const target = ctx.store.get(ctx.groupId, ctx.targetId);
    if (!target) throw new GameError('目标尚未在本群注册修仙角色。');
    const targetMoney = safeAdd(target.money, amount, '目标灵石');
    spend(player, amount);
    target.money = targetMoney;
    ctx.store.save(ctx.groupId, target);
    return `已向${target.name}（${target.userId}）赠送${amount}灵石，当前余额${player.money}。`;
  }
  const { operation } = inputMatch;
  if (!operation) return null;
  requirePlayer(player);
  const [, action, input] = operation;
  if (!input.trim()) throw new GameError(`格式：${action} 物品名/ID${action === '卸下' ? '（或槽名：法器/防具/功法/神通）' : ' [数量]'}`);
  if (action === '卸下') {
    const key = input.trim();
    let slot = SLOT_ALIASES[key];
    if (!slot) {
      const item = findItem(key);
      if (!Object.hasOwn(SLOT_NAMES, item.kind)) throw new GameError('只有法器、防具、主功法和神通支持卸下。');
      slot = item.kind;
      if (player.equipment[slot] !== item.id) throw new GameError(`${item.name}未在当前槽位使用。`);
    }
    const id = player.equipment[slot];
    if (!id) throw new GameError(`${SLOT_NAMES[slot]}槽位为空。`);
    player.equipment[slot] = null;
    clampVitals(player);
    return `已卸下${items.get(id).name}。${slot === 'technique' || slot === 'skill' ? '已学习的功法/神通不会返还为书籍。' : '装备仍保留在背包。'}`;
  }
  const { item, count } = parseUse(input);
  if (action === '装备') return equip(player, item, count);
  if (action === '功法修炼') return learn(player, item, count);
  if (action === '购买') {
    if (!shopItems().some(stock => stock.id === item.id)) throw new GameError('商店不出售此物品，仅售有真实price/status的原版普通丹药。');
    const cost = item.price * count;
    if (!Number.isSafeInteger(cost)) throw new GameError('总价超出安全整数范围。');
    checkIncoming(player, item, count);
    spend(player, cost);
    addItem(player, item.id, count);
    return `购买${item.name}×${count}，花费${cost}灵石，余额${player.money}。`;
  }
  if (item.kind === 'weapon' || item.kind === 'armor') return equip(player, item, count);
  if (item.kind === 'pill') return usePill(player, item, count);
  if (item.kind === 'technique' || item.kind === 'skill') throw new GameError('主功法和神通请使用“功法修炼 物品名/ID”，学习消耗1本。');
  throw new GameError('此物品不能服用或装备；本次秘境和悬赏不消耗藏宝图、悬赏令。');
}

module.exports = { handleInventory };
