# QQ 群修仙游戏引擎

一个使用 Node.js 和 SQLite 实现的群聊修仙游戏核心。项目不绑定具体 QQ Bot 框架：宿主只需把群消息转换为事件对象，再发送引擎返回的文本。

## 功能

- 修炼、闭关、突破、境界与排行榜
- 背包、装备、功法、商店与玩家交易
- 悬赏、秘境、邪魔、战斗与积分兑换
- 灵庄、洞天福地、炼丹、宗门、坊市与拍卖
- 地图移动、玩家互动、仙缘与交友会
- 按群隔离玩家、世界、宗门和市场数据
- 可选宿主模型判定，用于突破问答和秘境行动

在群聊中发送 `修仙帮助` 可以查看完整指令分类。

## 运行要求

- 支持 `node:sqlite` 的 Node.js 版本
- 当前代码已在 Node.js `v25.6.1` 验证
- 无第三方运行依赖

## 获取与验证

```bash
git clone --branch feature/qqbot-games --single-branch https://github.com/iris-cat-dev/qqbot_xianyuan.git
cd qqbot_xianyuan
npm test
```

## 接入机器人

`createGame` 接收 SQLite 文件路径，并返回游戏实例：

```js
const { createGame } = require('.');

const game = createGame({
  databasePath: './runtime/xiuxian.sqlite'
});

async function handleGroupMessage(message) {
  const result = await game.handleMessage({
    groupId: String(message.groupId),
    userId: String(message.userId),
    nickname: message.nickname,
    text: message.text,
    targetId: message.targetId === undefined ? undefined : String(message.targetId)
  });

  if (result.handled) {
    await message.reply(result.message);
  }
}

// 机器人退出时释放 SQLite 连接。
process.once('SIGTERM', () => game.close());
```

宿主需要负责 QQ 消息监听、@对象解析和消息发送。`targetId` 只在切磋、赠送、双修等需要目标玩家的指令中传入。

### 事件字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `groupId` | 是 | 当前群的字符串 ID |
| `userId` | 是 | 当前用户的字符串 ID |
| `text` | 是 | 原始指令文本 |
| `nickname` | 否 | 玩家首次进入时使用的昵称 |
| `targetId` | 否 | @目标用户的字符串 ID |
| `answer` | 否 | 突破或秘境问答消息传 `true` |

### 返回结果

```js
{
  handled: true,
  message: '返回给玩家的文本',
  reviewRequest: undefined,
  error: undefined
}
```

- `handled: false`：消息不是游戏指令，宿主可以继续交给其他插件。
- `reviewRequest`：需要宿主模型判定时返回的结构化请求。
- `error`：模型不可用或返回格式无效时的稳定错误代码。

## 模型判定

创建实例时可以传入异步 `judge(request)`。引擎会把突破或秘境的结构化判定请求交给该函数；函数必须返回符合 `request.schema` 的 JavaScript 对象，引擎会在结算前校验结果。

`judge` 未配置时，`handleMessage` 会直接返回 `reviewRequest`。宿主完成模型调用后，可以把 `groupId`、`userId`、`kind`、`requestId`、`revision` 和模型返回的 `review` 交给 `resolveReview`。模型调用失败不会扣除玩家资源。

## API

| 方法 | 用途 |
| --- | --- |
| `parseInput(event)` | 校验事件并判断是否为游戏指令 |
| `handleCommand(event)` | 同步处理指令；需要模型时返回 `reviewRequest` |
| `handleMessage(event)` | 处理指令，并在配置 `judge` 时自动完成异步判定 |
| `resolveReview(event)` | 提交宿主完成的突破或秘境判定 |
| `getPlayer(groupId, userId)` | 读取玩家当前状态 |
| `close()` | 关闭 SQLite 连接 |

## 项目结构

```text
.
├── src/         # 游戏引擎与各玩法模块
├── data/        # 境界、物品、地图、秘境等静态数据
├── tests/       # Node.js 行为测试
├── .gitignore   # 本地依赖、环境变量和数据库忽略规则
├── package.json # 包入口与测试命令
└── LICENSE      # MIT 许可证
```

## 数据与安全

- SQLite 数据库包含群和玩家状态，请按业务数据管理，不要提交到 Git。
- `.gitignore` 已排除 `.env`、SQLite 数据库、`node_modules` 和系统临时文件。
- 模型判定请求只包含游戏事实；测试覆盖群 ID、用户 ID 和昵称不进入判定内容。
- 数据库文件及其 WAL/SHM 文件不允许使用符号链接。

## 测试

```bash
npm test
```

测试覆盖输入边界、修炼突破、战斗、背包、秘境、模型判定、扩展玩法和数据隔离。

## 许可证

[MIT](LICENSE) © 2023 Iris
