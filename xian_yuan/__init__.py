from nonebot import Bot
from nonebot.adapters.qq import MessageEvent
from nonebot.message import run_postprocessor, event_preprocessor
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='仙缘',
    description='',
    usage=(
        "必死之境逢仙缘，仙路崎岖意更坚！\n"
        "输入 < 修仙帮助 > 获取仙界信息。"
    ),
    extra={
        "show": True,
        "priority": 15
    }
)


@event_preprocessor
async def _(bot: Bot, event: MessageEvent):...


@run_postprocessor
async def _(e: Exception): ...


