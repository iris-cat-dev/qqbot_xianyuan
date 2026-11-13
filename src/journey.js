'use strict';

const { data, stats } = require('./rules');

// 只保留最近八次真实结算，不读取群聊、昵称或其他玩家档案。
function recordJourney(player, type, at, details) {
  player.journeySequence++;
  player.journey.push({ id: `journey-${player.journeySequence}`, type, at, ...details });
  if (player.journey.length > 8) player.journey.shift();
}

function buildBreakthroughFacts(player) {
  const attributes = stats(player);
  return [
    {
      id: 'state', type: 'state', realm: data.realms[player.realm].name,
      exp: player.exp, root: player.root.type, rootSpeed: player.root.speed,
      hp: player.hp, maxHp: attributes.maxHp, mp: player.mp, maxMp: attributes.maxMp
    },
    ...player.journey
  ];
}

module.exports = { recordJourney, buildBreakthroughFacts };
