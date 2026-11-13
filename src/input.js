'use strict';

const { items } = require('./rules');

const ITEM_NAMES = [...items.values()].map(item => item.name);
const SLOT_NAMES = new Set(['法器', '武器', '防具', '护具', '防具装备', '功法', '主功法', '神通']);

function recognizesProgression(text) {
  return /^(?:我要修仙|我的修仙信息|我的状态|修仙签到|新手礼包领取|领取新手礼包|重入仙途|闭关|出关|灵石出关|直接突破|渡厄突破|我的突破概率|排行榜|修仙排行榜|灵石排行榜|战力排行榜)$/u.test(text)
    || /^改名(?:\s|$)/u.test(text);
}

function recognizesMission(text) {
  return /^(?:悬赏令|悬赏令帮助|悬赏令刷新|悬赏令结算|悬赏令终止|悬赏令放弃)$/u.test(text)
    || text.startsWith('悬赏令接取');
}

// 名称/ID连写兼容原玩法；日常的“使用电脑”“查询天气”不作为游戏请求。
function isItemArgument(input) {
  return /^\d/u.test(input) || ITEM_NAMES.some(name => input.startsWith(name)
    && (input.length === name.length || /^[\s\d]/u.test(input.slice(name.length))));
}

function matchInventory(text) {
  if (/^(?:我的背包|背包|我的功法|商店|修仙商店)$/u.test(text)) return { simple: true };
  const query = text.match(/^(?:物品信息|查询)\s*(.*)$/u);
  if (query && (text.startsWith('物品信息') || /^(?:查询)(?:\s|$)/u.test(text) || isItemArgument(query[1]))) return { query };
  const market = text.match(/^坊市(?:(上架|查询|购买|下架)\s*(.*))?$/u);
  if (market) return { market };
  const transfer = text.match(/^送灵石\s*(.*)$/u);
  if (transfer) return { transfer };
  const operation = text.match(/^(功法修炼|使用|装备|卸下|购买)\s*(.*)$/u);
  if (operation && (operation[1] === '功法修炼' || text === operation[1]
    || /^\s/u.test(text.slice(operation[1].length)) || isItemArgument(operation[2])
    || (operation[1] === '卸下' && SLOT_NAMES.has(operation[2])))) return { operation };
  return null;
}

function recognizesEncounters(text) {
  return /^(?:秘境查询|秘境探索|秘境结算|秘境探索终止|邪魔查询|我的积分|积分查询)$/u.test(text)
    || text.startsWith('讨伐邪魔') || text.startsWith('积分兑换') || /^切磋(?:\s|@|$)/u.test(text);
}
function recognizesBank(text) {
  return /^(?:灵庄帮助|灵庄信息|灵庄结算|灵庄会员升级)$/u.test(text)
    || /^灵庄(?:存入|取出)(?:\s|\d|$)/u.test(text);
}

function recognizesEstate(text) {
  return /^(?:洞天福地帮助|洞天福地购买|我的洞天福地|灵田帮助|灵田开垦|灵田收取|灵矿帮助|灵矿开垦|灵矿收取)$/u.test(text)
    || /^洞天福地改名(?:\s|$)/u.test(text);
}

function recognizesAlchemy(text) {
  return /^(?:炼丹|炼丹帮助|炼丹配方帮助|我的炼丹信息|升级收取等级|升级丹药控火|炼丹考核开始)$/u.test(text)
    || /^配方(?:\s|主药|$)/u.test(text) || /^炼丹考核解答(?:\s|$)/u.test(text);
}

function recognizesSocial(text) {
  return /^(?:我的双修次数)$/u.test(text)
    || /^(?:赠送|偷灵石|打劫|双修)(?:\s|@|$)/u.test(text);
}

function recognizesSect(text) {
  return /^(?:宗门帮助|我的宗门|宗门列表|退出宗门|宗门任务接取|我的宗门任务|宗门任务完成|宗门任务刷新|宗门功法搜寻|宗门神通搜寻|宗门功法查询|宗门成员查询|升级攻击修炼|宗门丹房建设|宗门丹药领取)$/u.test(text)
    || /^(?:创建宗门|加入宗门|宗门捐献|宗门职位变更|踢出宗门|宗主传位|学习宗门功法|学习宗门神通)(?:\s|@|$)/u.test(text);
}

function recognizesAuction(text) {
  return /^(?:举行交友会|交友会查询)$/u.test(text) || /^出价(?:\s|\d|$)/u.test(text);
}

function recognizesMap(text) {
  return /^(?:地图|查看周围|向北走|向南走|向西走|向东走)$/u.test(text);
}

function recognizesRomance(text) {
  return /^(?:仙缘帮助|仙缘查询|我的仙缘|仙缘任务接取|我的仙缘任务|仙缘任务完成)$/u.test(text)
    || text.startsWith('表白');
}


function recognizesCommand(text) {
  return text === '修仙帮助' || recognizesProgression(text) || recognizesMission(text)
    || matchInventory(text) !== null || recognizesEncounters(text) || recognizesBank(text)
    || recognizesEstate(text) || recognizesAlchemy(text) || recognizesSocial(text)
    || recognizesSect(text) || recognizesAuction(text) || recognizesMap(text)
    || recognizesRomance(text) || /^(?:突破|取消突破|用丹|不用丹)$/u.test(text);
}

module.exports = {
  recognizesCommand, recognizesProgression, recognizesMission, matchInventory,
  recognizesEncounters, recognizesBank, recognizesEstate, recognizesAlchemy,
  recognizesSocial, recognizesSect, recognizesAuction, recognizesMap, recognizesRomance
};
