'use strict';

const { GameError, requirePlayer } = require('./rules');
const { recognizesMap } = require('./input');
const mapData = require('../data/map-data.json');

const byName = new Map(mapData.map(location => [location.name, location]));
const byCoordinate = new Map(mapData.map(location => [location.coordinate.join(','), location]));
const DIRECTIONS = {
  向北走: { name: '北', dx: 0, dy: -1 }, 向南走: { name: '南', dx: 0, dy: 1 },
  向西走: { name: '西', dx: -1, dy: 0 }, 向东走: { name: '东', dx: 1, dy: 0 }
};

function surroundings(location) {
  return Object.values(DIRECTIONS).map(direction => {
    const next = byCoordinate.get(`${location.coordinate[0] + direction.dx},${location.coordinate[1] + direction.dy}`);
    return next ? `${direction.name}：${next.name}` : null;
  }).filter(Boolean);
}

function describe(player) {
  const location = byName.get(player.position);
  if (!location) throw new Error(`未知玩家地图位置：${player.position}`);
  return `当前位置：${location.name}\n${location.desc || '此处暂时寂静无事。'}\n可前往：${surroundings(location).join('；') || '无路可走'}`;
}

function handleMap(ctx) {
  if (!recognizesMap(ctx.text)) return null;
  requirePlayer(ctx.player);
  if (ctx.text === '地图' || ctx.text === '查看周围') return describe(ctx.player);
  const current = byName.get(ctx.player.position);
  if (!current) throw new Error(`未知玩家地图位置：${ctx.player.position}`);
  const direction = DIRECTIONS[ctx.text];
  const destination = byCoordinate.get(`${current.coordinate[0] + direction.dx},${current.coordinate[1] + direction.dy}`);
  if (!destination) throw new GameError(`这个方向没有路。\n${describe(ctx.player)}`);
  ctx.player.position = destination.name;
  return `来到${destination.name}。\n${describe(ctx.player)}`;
}

module.exports = { handleMap };
