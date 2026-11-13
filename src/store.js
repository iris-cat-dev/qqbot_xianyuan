'use strict';

const { DatabaseSync } = require('node:sqlite');
const { mkdirSync, lstatSync } = require('node:fs');
const { dirname } = require('node:path');

function parsePlayer(state) {
  const player = JSON.parse(state);
  player.breakthroughTrial ??= null;
  player.riftAdventure ??= null;
  player.insightReviews ??= [];
  player.journey ??= [];
  player.journeySequence ??= 0;
  player.bank ??= null;
  player.estate ??= null;
  player.alchemy ??= { collectionLevel: 0, fireLevel: 0, exp: 0, records: {}, exam: { points: 0, current: null } };
  player.sectId ??= null;
  player.sectPosition ??= null;
  player.sectContribution ??= 0;
  player.attackPractice ??= 0;
  player.sectTask ??= null;
  player.lastSectTaskRefreshAt ??= null;
  player.lastStealAt ??= null;
  player.position ??= '新手村广场';
  player.romance ??= { favor: {}, completedSpecial: {}, task: null, completedDay: null, confessionDates: {}, partnerFairyId: null };
  player.romance.favor ??= {};
  player.romance.completedSpecial ??= {};
  player.romance.task ??= null;
  player.romance.completedDay ??= null;
  player.romance.confessionDates ??= {};
  player.romance.partnerFairyId ??= null;
  player.daily ??= { date: null, refreshes: 0, pillUses: {} };
  player.daily.refreshes ??= 0;
  player.daily.pillUses ??= {};
  player.daily.sectTasks ??= 0;
  player.daily.sectElixirClaimed ??= false;
  player.daily.dualCultivations ??= 0;
  return player;
}

function defaultWorld() {
  return {
    rift: null, riftGeneratedAt: null, bosses: [], bossGeneratedAt: null,
    market: [], nextListingId: 1, sects: {}, nextSectId: 1, auction: null,
    romance: null, romancePartners: {}
  };
}

function parseWorld(state) {
  const world = state ? JSON.parse(state) : defaultWorld();
  world.rift ??= null;
  world.riftGeneratedAt ??= null;
  world.bosses ??= [];
  world.bossGeneratedAt ??= null;
  world.market ??= [];
  world.nextListingId ??= 1;
  world.sects ??= {};
  world.nextSectId ??= 1;
  world.auction ??= null;
  world.romance ??= null;
  world.romancePartners ??= {};
  return world;
}

function rejectSymlink(filename) {
  let stat;
  try { stat = lstatSync(filename); } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
  if (stat.isSymbolicLink()) throw new Error('游戏数据库及其辅助文件不能是符号链接。');
}

// 同一条群聊指令在一个事务内完成；跨进程调用不会覆盖其他玩家的存档。
function openStore(filename) {
  if (typeof filename !== 'string' || !filename.trim()) throw new TypeError('databasePath必须是非空SQLite路径。');
  if (filename !== ':memory:') {
    for (const path of [filename, `${filename}-wal`, `${filename}-shm`]) rejectSymlink(path);
    mkdirSync(dirname(filename), { recursive: true });
  }
  const database = new DatabaseSync(filename);
  database.exec(`
    PRAGMA busy_timeout = 5000;
    CREATE TABLE IF NOT EXISTS players (
      group_id TEXT NOT NULL,
      user_id TEXT NOT NULL,
      state TEXT NOT NULL,
      PRIMARY KEY (group_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS worlds (
      group_id TEXT PRIMARY KEY,
      state TEXT NOT NULL
    );
  `);
  const get = database.prepare('SELECT state FROM players WHERE group_id = ? AND user_id = ?');
  const list = database.prepare('SELECT state FROM players WHERE group_id = ?');
  const put = database.prepare(`
    INSERT INTO players (group_id, user_id, state) VALUES (?, ?, ?)
    ON CONFLICT (group_id, user_id) DO UPDATE SET state = excluded.state
  `);
  const getWorld = database.prepare('SELECT state FROM worlds WHERE group_id = ?');
  const putWorld = database.prepare(`
    INSERT INTO worlds (group_id, state) VALUES (?, ?)
    ON CONFLICT (group_id) DO UPDATE SET state = excluded.state
  `);

  return {
    get(groupId, userId) {
      const row = get.get(groupId, userId);
      return row ? parsePlayer(row.state) : null;
    },
    list(groupId) {
      return list.all(groupId).map(row => parsePlayer(row.state));
    },
    save(groupId, player) {
      put.run(groupId, player.userId, JSON.stringify(player));
    },
    getWorld(groupId) {
      const row = getWorld.get(groupId);
      return parseWorld(row?.state);
    },
    saveWorld(groupId, world) {
      putWorld.run(groupId, JSON.stringify(world));
    },
    transaction(action) {
      database.exec('BEGIN IMMEDIATE');
      try {
        const result = action();
        database.exec('COMMIT');
        return result;
      } catch (error) {
        database.exec('ROLLBACK');
        throw error;
      }
    },
    close() {
      database.close();
    }
  };
}

module.exports = { openStore };
