from nonebot import require
from nonebot.plugin import PluginMetadata

require('nonebot_plugin_apscheduler')

__plugin_meta__ = PluginMetadata(
    name='修仙模拟器',
    description='',
    usage=(
        "必死之境逢仙缘，修仙之路何壮阔！\n"
        "输入 < 修仙帮助 > 获取仙界信息。"
    ),
    extra={
        "show": True,
        "priority": 15
    }
)

