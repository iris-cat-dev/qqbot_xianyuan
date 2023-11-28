from nonebot import Bot, on_fullmatch
from nonebot.adapters.onebot.v11 import GroupMessageEvent, GROUP

from .common.bot_utils import xiuxian_send_message
from .lay_out import Cooldown
from .utils import CommandObjectID, check_user
from .xiuxian2_handle import XiuxianDateManage
from ..xiuxian import XiuConfig

__xiuxian_notes__ = f"""
指令：
1、我要修仙:进入修仙模式
2、我的修仙信息:获取修仙数据
3、修仙签到:获取灵石及修为
4、重入仙途:重置灵根数据,每次{XiuConfig().remake}灵石
6、改名xx:修改你的道号
7、突破:修为足够后,可突破境界（一定几率失败）
8、闭关、出关、灵石出关、灵石修炼、双修:修炼增加修为,挂机功能
10、排行榜:修仙排行榜,灵石排行榜,战力排行榜,宗门排行榜
11、悬赏令帮助:获取悬赏令帮助信息
12、我的状态:查看当前HP,我的功法：查看当前技能
13、宗门系统:发送"宗门帮助"获取
14、灵庄系统:发送"灵庄帮助"获取
15、世界BOSS:发送"世界boss帮助"获取
16、功法/灵田：发送“功法帮助/灵田帮助”查看，当前获取途径看“宗门帮助”
17、背包系统：发送"背包帮助"获取
18、秘境系统:发送"秘境帮助"获取
19、炼丹帮助:炼丹功能
22、启用/禁用修仙功能：当前群开启或关闭修仙功能
""".strip()

__warring_help__ = f"""
配置地址:修仙插件下 xiuxian_config.py
self.put_bot = []  # 接收消息qq,主qq,框架将只处理此qq的消息.
self.main_bo = []  # 负责发送消息的qq
self.shield_group = []  # 屏蔽的群聊
self.layout_bot_dict = {{}}  # QQ所负责的群聊{{群 :bot}}   其中 bot类型 []或str 
""".strip()

__xiuxian_updata_data__ = f"""
## 更新2023.3.1 - 2023.3.6
1.修复已知bug
2.支持每个群boss刷新时间定制
3.支持适配修仙1的境界
3.宗门可以根据qq号踢人,宗门成员查看获得qq号
4.支持随机存档背景
5.支持批量使用丹药
6.支持批量炼金和炼金绑定丹药
7.修改了世界积分价格,需要删除boss模块下的config.json生效
8.增加了修仙全局命令调用锁,默认一分钟五次
9.增加隐藏职业：器师
器师：指依托于大宗门下的炼器士，其修为一般很低，但不可小觑，因为一般是大修士的转生与亲信，替大修士完成红尘历练。
更新类容：## 更新2023.3.11
1.修改背包容量
2.坊市支持批量上架和购买
3.解决手机部分图片需要点开才能看到字的问题
""".strip()

xiuxian_update_level = on_fullmatch('修仙适配', priority=15, permission=GROUP, block=True)
xiuxian_update_log = on_fullmatch('更新记录', priority=15, permission=GROUP, block=True)
help_in = on_fullmatch("修仙帮助", priority=12, permission=GROUP, block=True)
warring_help = on_fullmatch("风控帮助", priority=12, permission=GROUP, block=True)

sql_message = XiuxianDateManage()


@help_in.handle(parameterless=[Cooldown(cd_time=5, at_sender=True)])
async def help_in_(_: Bot, __: GroupMessageEvent):
    """
    修仙帮助
    """
    await xiuxian_send_message(help_in, __xiuxian_notes__)


@warring_help.handle(parameterless=[Cooldown(at_sender=True)])
async def warring_help_(bot: Bot, _: GroupMessageEvent):
    """
    风控帮助
    """
    await xiuxian_send_message(help_in, __warring_help__)


@xiuxian_update_log.handle(parameterless=[Cooldown(at_sender=True)])
async def xiuxian_update_log_(bot: Bot, _: GroupMessageEvent):
    await xiuxian_send_message(xiuxian_update_log, __xiuxian_updata_data__)


@xiuxian_update_level.handle(parameterless=[Cooldown(at_sender=True)])
async def xiuxian_updata_level_(bot: Bot, event: GroupMessageEvent):
    """将修仙1的境界适配到修仙2"""
    _, user_info, msg = check_user(event)
    level_dict = {
        "练气境": "练气境",
        "筑基境": "筑基境",
        "结丹境": "结丹境",
        "元婴境": "元婴境",
        "化神境": "化神境",
        "炼虚境": "炼虚境",
        "合体境": "合体境",
        "大乘境": "大乘境",
        "渡劫境": "渡劫境",
        "半步真仙": "真仙境中期",
        "真仙境": "玄仙境",
        "金仙境": "地仙境",
        "太乙境": "天仙境"
    }
    level = user_info.level
    user_id = user_info.user_id
    if level == "半步真仙":
        level = "真仙境中期"
    else:
        try:
            level = level_dict.get(level[:3]) + level[-2:]
        except:
            level = level
    sql_message.updata_level(user_id=user_id, level_name=level)
    msg = '境界适配成功成功！'
    await xiuxian_send_message(xiuxian_update_level, msg)
