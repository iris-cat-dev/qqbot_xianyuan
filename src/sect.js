'use strict';

const {
  data, items, GameError, MINUTE, addExp, addItem, clampVitals, integer,
  playerRank, positiveInteger, requirePlayer, safeAdd, safeMultiply, spend
} = require('./rules');
const { recognizesSect } = require('./input');

const DAY = 24 * 60 * MINUTE;
const SHANGHAI_OFFSET = 8 * 60 * MINUTE;
const CREATE_COST = 4_000_000;
const MIN_REALM = data.realms.findIndex(realm => realm.name === '元婴境圆满');
const POSITIONS = ['宗主', '长老', '亲传弟子', '内门弟子', '外门弟子'];
const POSITION_EXP_CAPS = [20_000_000, 10_000_000, 7_000_000, 5_000_000, 3_000_000];
const PRACTICE_COSTS = [100_000, 200_000, 400_000, 500_000, 600_000, 700_000, 800_000, 900_000, 1_000_000, 1_100_000, 1_200_000, 1_400_000, 1_600_000, 1_800_000, 2_000_000, 2_400_000, 2_800_000, 3_200_000, 4_800_000, 5_600_000, 6_400_000, 8_600_000, 10_400_000, 12_800_000, 25_600_000];
const LEVEL_NAMES = ['人阶下品', '人阶上品', '黄阶下品', '黄阶上品', '玄阶下品', '玄阶上品', '地阶下品', '地阶上品', '天阶下品', '天阶上品'];
const ELIXIR_ROOMS = [
  { name: '黄级', scale: 1_000_000, stone: 200_000 },
  { name: '玄级', scale: 60_000_000, stone: 400_000 },
  { name: '地级', scale: 70_000_000, stone: 800_000 },
  { name: '天级', scale: 80_000_000, stone: 1_600_000 },
  { name: '仙级', scale: 100_000_000, stone: 3_200_000 }
];
const TASKS = [
  { name: '狩猎邪修', desc: '山外村庄有邪修作乱，下山为民除害。', kind: 'hp', cost: 0.45, give: 0.012, sect: 14_000 },
  { name: '查抄窝点', desc: '查抄私设窝点，收缴物资归宗。', kind: 'hp', cost: 0.35, give: 0.01, sect: 10_000 },
  { name: '九转仙丹', desc: '为宗门采买一批炼丹药草。', kind: 'money', cost: 90_000, give: 0.008, sect: 15_000 },
  { name: '仗义疏财', desc: '替受困师弟偿清欠款。', kind: 'money', cost: 100_000, give: 0.0085, sect: 12_000 },
  { name: '红尘寻宝', desc: '在山下市场为宗门购入蒙尘奇宝。', kind: 'money', cost: 150_000, give: 0.009, sect: 18_000 }
];
const HELP = [
  '宗门：创建宗门 名称（元婴境圆满、400万灵石）、宗门列表、加入宗门 编号、我的宗门、宗门成员查询。',
  '治理：宗门捐献 数量、宗门职位变更 @成员 1～4、踢出宗门 @成员、宗主传位 @成员、退出宗门。',
  '成长：宗门任务接取/我的宗门任务/宗门任务完成/宗门任务刷新；升级攻击修炼。',
  '秘籍：宗门功法搜寻、宗门神通搜寻、宗门功法查询、学习宗门功法 名称、学习宗门神通 名称。',
  '丹房：宗门丹房建设、宗门丹药领取。宗门每天北京时间11:00、12:00各按建设度获得一次资材。'
].join('\n');

function localDay(now) {
  return Math.floor((now + SHANGHAI_OFFSET) / DAY);
}

function materialSlot(now) {
  const shifted = now + SHANGHAI_OFFSET;
  const day = Math.floor(shifted / DAY);
  const hour = Math.floor((shifted - day * DAY) / (60 * MINUTE));
  return day * 2 + (hour >= 12 ? 2 : hour >= 11 ? 1 : 0);
}

function refreshSect(sect, now) {
  const slot = materialSlot(now);
  const grants = Math.max(0, slot - sect.lastMaterialSlot);
  if (grants) {
    sect.materials = safeAdd(sect.materials, safeMultiply(sect.scale, grants, '宗门资材发放'), '宗门资材');
    sect.lastMaterialSlot = slot;
  }
  const day = localDay(now);
  const elapsedDays = Math.max(0, day - sect.lastMaintenanceDay);
  if (elapsedDays && sect.elixirRoomLevel) {
    const dailyCost = ELIXIR_ROOMS[sect.elixirRoomLevel - 1].scale;
    const payableDays = Math.min(elapsedDays, Math.floor(sect.materials / dailyCost));
    sect.materials -= payableDays * dailyCost;
  }
  sect.lastMaintenanceDay = day;
}

function currentSect(ctx) {
  if (ctx.player.sectId === null) throw new GameError('尚未加入宗门。');
  const sect = ctx.world.sects[String(ctx.player.sectId)];
  if (!sect) throw new Error(`玩家宗门存档缺失：${ctx.player.sectId}`);
  refreshSect(sect, ctx.now);
  return sect;
}

function saveTarget(ctx, target) {
  ctx.store.save(ctx.groupId, target);
}

function targetMember(ctx, sect, action) {
  if (!ctx.targetId) throw new GameError(`${action}需要明确@一位本群成员。`);
  if (ctx.targetId === ctx.userId) throw new GameError(`不能对自己执行${action}。`);
  const target = ctx.store.get(ctx.groupId, ctx.targetId);
  if (!target || target.sectId !== sect.id) throw new GameError('目标不是本宗成员。');
  return target;
}

function sectGear(sect) {
  return Math.max(1, Math.min(10, Math.floor(sect.scale / 5_000_000)));
}

function taskText(task, now) {
  const remain = Math.max(0, Math.ceil((task.readyAt - now) / MINUTE));
  return `${task.name}：${task.desc}\n${remain ? `${remain}分钟后可完成` : '现在可以完成'}；消耗${task.kind === 'hp' ? `基础气血的${task.cost * 100}%` : `${task.cost}灵石`}。`;
}

function searchManual(ctx, sect, kind) {
  if (ctx.player.sectPosition !== 0) throw new GameError('只有宗主可以搜寻宗门秘籍。');
  const gear = sectGear(sect);
  const level = LEVEL_NAMES[gear - 1];
  const collection = kind === 'technique' ? data.techniques : data.skills;
  const pool = Object.entries(collection).filter(([, item]) => item.level === level);
  if (!pool.length) throw new Error(`没有${level}${kind === 'technique' ? '功法' : '神通'}配置。`);
  const [id, manual] = pool[integer(0, pool.length - 1, ctx.random)];
  const list = kind === 'technique' ? sect.techniques : sect.skills;
  if (list.includes(id)) return `搜寻到重复的${manual.name}，未消耗宗门资源。`;
  const stone = gear * 30_000;
  const materials = gear * 600_000;
  if (sect.reserve < stone || sect.materials < materials) throw new GameError(`搜寻需要${stone}宗门灵石和${materials}资材；当前${sect.reserve}/${sect.materials}。`);
  sect.reserve -= stone;
  sect.materials -= materials;
  list.push(id);
  return `消耗${stone}宗门灵石、${materials}资材，搜寻到${level}${kind === 'technique' ? '功法' : '神通'}：${manual.name}。`;
}

function learnManual(ctx, sect, kind) {
  if (ctx.player.sectPosition === 4) throw new GameError('外门弟子不能使用宗门资材学习秘籍。');
  const prefix = kind === 'technique' ? '学习宗门功法' : '学习宗门神通';
  const name = ctx.text.slice(prefix.length).trim();
  if (!name) throw new GameError(`格式：${prefix} 名称。`);
  const ids = kind === 'technique' ? sect.techniques : sect.skills;
  const id = ids.find(candidate => candidate === name || items.get(candidate).name === name);
  if (!id) throw new GameError(`本宗没有该${kind === 'technique' ? '功法' : '神通'}。`);
  const item = items.get(id);
  if (ctx.player.equipment[kind] === id) throw new GameError(`已经学会${item.name}。`);
  const gear = LEVEL_NAMES.indexOf(item.level) + 1;
  const cost = gear * 600_000;
  if (sect.materials < cost) throw new GameError(`学习需要${cost}宗门资材，当前${sect.materials}。`);
  sect.materials -= cost;
  const previous = ctx.player.equipment[kind];
  ctx.player.equipment[kind] = id;
  clampVitals(ctx.player);
  return `消耗${cost}宗门资材，学会${item.name}。${previous ? `原${kind === 'technique' ? '功法' : '神通'}${items.get(previous).name}被替换且不返还。` : ''}`;
}

function buildElixirRoom(ctx, sect) {
  if (ctx.player.sectPosition !== 0) throw new GameError('只有宗主可以建设宗门丹房。');
  if (sect.elixirRoomLevel >= ELIXIR_ROOMS.length) throw new GameError('宗门丹房已达仙级。');
  const room = ELIXIR_ROOMS[sect.elixirRoomLevel];
  if (sect.scale < room.scale || sect.reserve < room.stone) throw new GameError(`本级丹房需要${room.scale}建设度和${room.stone}宗门灵石；当前${sect.scale}/${sect.reserve}。`);
  sect.scale -= room.scale;
  sect.reserve -= room.stone;
  sect.elixirRoomLevel++;
  return `消耗${room.scale}建设度、${room.stone}宗门灵石，丹房升为${room.name}。`;
}

function claimElixir(ctx, sect) {
  if (ctx.player.sectPosition === 4) throw new GameError('外门弟子不能领取宗门丹药。');
  if (!sect.elixirRoomLevel) throw new GameError('本宗尚未建设丹房。');
  if (ctx.player.sectContribution < 100_000) throw new GameError('领取丹药需要至少100000宗门贡献。');
  if (ctx.player.daily.sectElixirClaimed) throw new GameError('今日已经领取宗门丹药。');
  const maintenance = ELIXIR_ROOMS[sect.elixirRoomLevel - 1].scale;
  if (sect.materials < maintenance) throw new GameError(`宗门资材不足以维持丹房，需要至少${maintenance}。`);
  const rewards = { '1999': 1 };
  if (sect.elixirRoomLevel > 1) {
    const rank = playerRank(ctx.player) - 1;
    const pool = Object.entries(data.pills).filter(([id, pill]) => id !== '1999' && pill.rank >= rank && pill.rank - rank <= 6).map(([id]) => id);
    if (!pool.length) rewards['1999'] = 2;
    else for (let i = 1; i < sect.elixirRoomLevel; i++) {
      const id = pool[integer(0, pool.length - 1, ctx.random)];
      rewards[id] = (rewards[id] ?? 0) + 1;
    }
  }
  for (const [id, count] of Object.entries(rewards)) addItem(ctx.player, id, count);
  ctx.player.daily.sectElixirClaimed = true;
  return `领取宗门丹药：${Object.entries(rewards).map(([id, count]) => `${items.get(id).name}×${count}`).join('、')}。`;
}

function handleSect(ctx) {
  if (!recognizesSect(ctx.text)) return null;
  if (ctx.text === '宗门帮助') return HELP;
  requirePlayer(ctx.player);
  if (ctx.text === '宗门列表') {
    const sects = Object.values(ctx.world.sects);
    for (const sect of sects) refreshSect(sect, ctx.now);
    sects.sort((a, b) => b.scale - a.scale || a.id - b.id);
    return `本群宗门列表\n${sects.length ? sects.map((sect, index) => `${index + 1}. [${sect.id}] ${sect.name} · 建设度${sect.scale} · 宗主${ctx.store.get(ctx.groupId, sect.ownerId)?.name ?? sect.ownerId}`).join('\n') : '暂无宗门。'}`;
  }
  if (ctx.text.startsWith('创建宗门')) {
    if (ctx.player.sectId !== null) throw new GameError('已经加入宗门，不能另建宗门。');
    if (ctx.player.realm < MIN_REALM) throw new GameError(`创建宗门至少需要${data.realms[MIN_REALM].name}。`);
    const name = ctx.text.slice('创建宗门'.length).trim();
    if (!name || Array.from(name).length > 12) throw new GameError('宗门名称须为1～12个字符。');
    if (Object.values(ctx.world.sects).some(sect => sect.name === name)) throw new GameError('本群已有同名宗门。');
    spend(ctx.player, CREATE_COST);
    const id = ctx.world.nextSectId;
    ctx.world.nextSectId = safeAdd(id, 1, '宗门编号');
    ctx.world.sects[String(id)] = {
      id, name, ownerId: ctx.userId, scale: 0, reserve: 0, materials: 0,
      techniques: [], skills: [], elixirRoomLevel: 0, createdAt: ctx.now,
      lastMaterialSlot: materialSlot(ctx.now), lastMaintenanceDay: localDay(ctx.now)
    };
    ctx.player.sectId = id;
    ctx.player.sectPosition = 0;
    ctx.player.sectContribution = 0;
    return `消耗${CREATE_COST}灵石，创建宗门“${name}”，编号${id}；你成为宗主。`;
  }
  if (ctx.text.startsWith('加入宗门')) {
    if (ctx.player.sectId !== null) throw new GameError('已经加入宗门，请先退出当前宗门。');
    const match = ctx.text.match(/^加入宗门\s*(\d+)$/u);
    if (!match) throw new GameError('格式：加入宗门 编号。');
    const id = positiveInteger(match[1], '宗门编号');
    const sect = ctx.world.sects[String(id)];
    if (!sect) throw new GameError('本群没有这个宗门编号。');
    refreshSect(sect, ctx.now);
    ctx.player.sectId = id;
    ctx.player.sectPosition = 4;
    ctx.player.sectContribution = 0;
    return `加入${sect.name}，当前职位为外门弟子。`;
  }
  const sect = currentSect(ctx);
  if (ctx.text === '我的宗门') {
    const owner = ctx.store.get(ctx.groupId, sect.ownerId);
    const room = sect.elixirRoomLevel ? ELIXIR_ROOMS[sect.elixirRoomLevel - 1].name : '暂无';
    return `${ctx.player.name}所在宗门\n宗门：${sect.name} [${sect.id}]\n宗主：${owner?.name ?? sect.ownerId}\n职位：${POSITIONS[ctx.player.sectPosition]}\n建设度：${sect.scale} · 宗门灵石：${sect.reserve} · 资材：${sect.materials}\n个人贡献：${ctx.player.sectContribution} · 攻击修炼：${ctx.player.attackPractice}/25\n丹房：${room}`;
  }
  if (ctx.text === '宗门成员查询') {
    const members = ctx.store.list(ctx.groupId).filter(player => player.sectId === sect.id)
      .sort((a, b) => a.sectPosition - b.sectPosition || b.sectContribution - a.sectContribution);
    return `${sect.name}成员\n${members.map((member, index) => `${index + 1}. ${member.name}（${member.userId}）· ${POSITIONS[member.sectPosition]} · 贡献${member.sectContribution}`).join('\n')}`;
  }
  if (ctx.text.startsWith('宗门捐献')) {
    const match = ctx.text.match(/^宗门捐献\s*(\d+)$/u);
    if (!match) throw new GameError('格式：宗门捐献 正整数灵石。');
    const amount = positiveInteger(match[1], '捐献');
    spend(ctx.player, amount);
    sect.scale = safeAdd(sect.scale, amount, '宗门建设度');
    sect.reserve = safeAdd(sect.reserve, amount, '宗门灵石');
    ctx.player.sectContribution = safeAdd(ctx.player.sectContribution, amount, '宗门贡献');
    return `捐献${amount}灵石；宗门建设度和储备各增加${amount}，个人贡献${ctx.player.sectContribution}。`;
  }
  if (ctx.text.startsWith('宗门职位变更')) {
    if (ctx.player.sectPosition > 1) throw new GameError('只有宗主和长老可以管理职位。');
    const target = targetMember(ctx, sect, '职位变更');
    const match = ctx.text.match(/([1-4])$/u);
    if (!match) throw new GameError('格式：宗门职位变更 @成员 1～4。');
    const position = Number(match[1]);
    if (target.sectPosition <= ctx.player.sectPosition || position <= ctx.player.sectPosition) throw new GameError('只能管理职位低于自己的人，并授予低于自己的职位。');
    target.sectPosition = position;
    saveTarget(ctx, target);
    return `${target.name}的职位变更为${POSITIONS[position]}。`;
  }
  if (ctx.text.startsWith('踢出宗门')) {
    if (ctx.player.sectPosition > 1) throw new GameError('只有宗主和长老可以踢出成员。');
    const target = targetMember(ctx, sect, '踢出宗门');
    if (target.sectPosition <= ctx.player.sectPosition) throw new GameError('不能踢出职位不低于自己的成员。');
    target.sectId = null; target.sectPosition = null; target.sectContribution = 0; target.sectTask = null;
    saveTarget(ctx, target);
    return `${target.name}已被${sect.name}除名。`;
  }
  if (ctx.text.startsWith('宗主传位')) {
    if (ctx.player.sectPosition !== 0) throw new GameError('只有宗主可以传位。');
    const target = targetMember(ctx, sect, '宗主传位');
    target.sectPosition = 0;
    ctx.player.sectPosition = 1;
    sect.ownerId = target.userId;
    saveTarget(ctx, target);
    return `${target.name}继任${sect.name}宗主；${ctx.player.name}转为长老。`;
  }
  if (ctx.text === '退出宗门') {
    if (ctx.player.sectPosition === 0) throw new GameError('宗主须先传位，不能直接退出宗门。');
    const name = sect.name;
    ctx.player.sectId = null; ctx.player.sectPosition = null; ctx.player.sectContribution = 0; ctx.player.sectTask = null;
    return `已退出${name}，恢复散修身份。`;
  }
  if (ctx.text === '宗门任务接取' || ctx.text === '我的宗门任务') {
    if (ctx.text === '我的宗门任务' && !ctx.player.sectTask) return '当前没有宗门任务。';
    if (!ctx.player.sectTask) {
      if (ctx.player.daily.sectTasks >= 3) throw new GameError('今日已完成3次宗门任务。');
      const task = TASKS[integer(0, TASKS.length - 1, ctx.random)];
      ctx.player.sectTask = { ...task, readyAt: ctx.now + 15 * MINUTE };
    }
    return taskText(ctx.player.sectTask, ctx.now);
  }
  if (ctx.text === '宗门任务刷新') {
    if (!ctx.player.sectTask) throw new GameError('当前没有宗门任务。');
    const readyAt = (ctx.player.lastSectTaskRefreshAt ?? 0) + 5 * MINUTE;
    if (ctx.now < readyAt) throw new GameError(`任务刷新冷却中，还需${Math.ceil((readyAt - ctx.now) / MINUTE)}分钟。`);
    const task = TASKS[integer(0, TASKS.length - 1, ctx.random)];
    ctx.player.sectTask = { ...task, readyAt: ctx.now + 15 * MINUTE };
    ctx.player.lastSectTaskRefreshAt = ctx.now;
    return `宗门任务已刷新。\n${taskText(ctx.player.sectTask, ctx.now)}`;
  }
  if (ctx.text === '宗门任务完成') {
    const task = ctx.player.sectTask;
    if (!task) throw new GameError('当前没有宗门任务。');
    if (ctx.now < task.readyAt) throw new GameError(`任务尚未完成，还需${Math.ceil((task.readyAt - ctx.now) / MINUTE)}分钟。`);
    if (task.kind === 'hp') {
      const cost = Math.floor((ctx.player.exp / 2) * task.cost);
      if (ctx.player.hp <= ctx.player.exp / 10 || ctx.player.hp <= cost) throw new GameError(`状态不足以完成任务，需要保留气血且本次消耗${cost}。`);
      ctx.player.hp -= cost;
    } else spend(ctx.player, task.cost);
    const gain = addExp(ctx.player, Math.min(Math.floor(ctx.player.exp * task.give), POSITION_EXP_CAPS[ctx.player.sectPosition]));
    sect.scale = safeAdd(sect.scale, task.sect, '宗门建设度');
    sect.reserve = safeAdd(sect.reserve, task.sect, '宗门灵石');
    sect.materials = safeAdd(sect.materials, task.sect * 10, '宗门资材');
    ctx.player.sectContribution = safeAdd(ctx.player.sectContribution, task.sect, '宗门贡献');
    ctx.player.daily.sectTasks++;
    ctx.player.sectTask = null;
    return `完成${task.name}，获得${gain}修为；宗门建设度与灵石各+${task.sect}、资材+${task.sect * 10}、个人贡献+${task.sect}。今日${ctx.player.daily.sectTasks}/3次。`;
  }
  if (ctx.text === '升级攻击修炼') {
    if (ctx.player.sectPosition === 4) throw new GameError('外门弟子不能使用宗门资材升级攻击修炼。');
    if (ctx.player.attackPractice >= 25) throw new GameError('攻击修炼已达25级。');
    const cap = Math.min(25, Math.floor(sect.scale / 500_000));
    if (ctx.player.attackPractice >= cap) throw new GameError(`当前建设度仅支持攻击修炼${cap}级。`);
    const cost = PRACTICE_COSTS[ctx.player.attackPractice];
    if (sect.materials < cost || ctx.player.sectContribution < cost) throw new GameError(`升级需要${cost}资材和个人贡献；当前${sect.materials}/${ctx.player.sectContribution}。`);
    sect.materials -= cost;
    ctx.player.sectContribution -= cost;
    ctx.player.attackPractice++;
    return `攻击修炼升至${ctx.player.attackPractice}级，攻击加成${ctx.player.attackPractice * 4}%；消耗${cost}资材和贡献。`;
  }
  if (ctx.text === '宗门功法搜寻') return searchManual(ctx, sect, 'technique');
  if (ctx.text === '宗门神通搜寻') return searchManual(ctx, sect, 'skill');
  if (ctx.text === '宗门功法查询') {
    const rows = [
      ...sect.techniques.map(id => `功法：${items.get(id).name} [${id}] · ${items.get(id).level}`),
      ...sect.skills.map(id => `神通：${items.get(id).name} [${id}] · ${items.get(id).level}`)
    ];
    return `${sect.name}宗门秘籍\n${rows.length ? rows.join('\n') : '尚无秘籍，由宗主搜寻。'}`;
  }
  if (ctx.text.startsWith('学习宗门功法')) return learnManual(ctx, sect, 'technique');
  if (ctx.text.startsWith('学习宗门神通')) return learnManual(ctx, sect, 'skill');
  if (ctx.text === '宗门丹房建设') return buildElixirRoom(ctx, sect);
  return claimElixir(ctx, sect);
}

module.exports = { handleSect, refreshSect, materialSlot };
