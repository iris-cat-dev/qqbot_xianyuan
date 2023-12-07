import json
from pathlib import Path
import os

two_exp = on_startswith("双修", priority=5, permission=GROUP, block=True)
my_exp_num = on_fullmatch("我的双修次数", priority=9, permission=GROUP, block=True)
del_exp_decimal = on_fullmatch("抑制黑暗动乱", priority=9, permission=GROUP, block=True)

two_exp_cd_up = require("nonebot_plugin_apscheduler").scheduler

# 每日0点重置用户宗门任务次数、宗门丹药领取次数
@two_exp_cd_up.scheduled_job("cron", hour=0, minute=0)
async def two_exp_cd_up_():
    two_exp_cd.re_data()
    logger.info('双修次数已更新！')


two_exp_limit = 3

@two_exp.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def two_exp_(bot: Bot, event: GroupMessageEvent):
    """
    双修
    """
    global two_exp_limit
    _, user_1, msg = check_user(event)

    two_qq = None  # 艾特的时候存到这里
    try:
        two_qq = event.original_message[1].data.get("qq", "")
    except:
        msg = "指令输入错误：【双修+@对方】"
        await xiuxian_send_message(two_exp, message=msg)

    if two_qq is None:
        msg = "请at你的道侣,与其一起双修！"
        await xiuxian_send_message(two_exp, message=msg)

    user_2 = sql_message.get_user_message(two_qq)
    if int(user_1.user_id) == int(two_qq):
        msg = "道友无法与自己双修！"
        await xiuxian_send_message(two_exp, message=msg)

    if user_2:
        exp_1 = user_1.exp
        exp_2 = user_2.exp
        if exp_2 > exp_1:
            msg = "修仙大能看了看你，不屑一顾，扬长而去！"
            await xiuxian_send_message(two_exp, message=msg)

        else:
            limt_1 = two_exp_cd.find_user(user_1.user_id)
            limt_2 = two_exp_cd.find_user(user_2.user_id)
            # 加入传承

            impart_two_exp_1 = 0
            impart_two_exp_2 = 0
            if limt_1 >= two_exp_limit + impart_two_exp_1:
                msg = "道友今天双修次数已经到达上限！"
                await xiuxian_send_message(two_exp, message=msg)

            if limt_2 >= two_exp_limit + impart_two_exp_2:
                msg = "对方今天双修次数已经到达上限！"
                await xiuxian_send_message(two_exp, message=msg)

            max_exp_1 = (
                    int(OtherSet().set_closing_type(user_1.level)) * XiuConfig().closing_exp_upper_limit
            )  # 获取下个境界需要的修为 * 1.5为闭关上限
            max_exp_2 = (
                    int(OtherSet().set_closing_type(user_2.level)) * XiuConfig().closing_exp_upper_limit
            )
            user_get_exp_max_1 = int(max_exp_1) - user_1.exp
            user_get_exp_max_2 = int(max_exp_2) - user_2.exp

            if user_get_exp_max_1 < 0:
                user_get_exp_max_1 = 0
            if user_get_exp_max_2 < 0:
                user_get_exp_max_2 = 0

            msg = ""
            msg += f"{user_1.user_name}与{user_2.user_name}情投意合，于某地一起修炼了一晚。"
            if random.randint(1, 100) in [13, 14, 52, 10, 66]:
                exp = int((exp_1 + exp_2) * 0.0055)

                if user_1.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_1.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_1 = max_exp
                else:
                    exp_limit_1 = exp

                if exp_limit_1 >= user_get_exp_max_1:
                    sql_message.update_exp(user_1.user_id, user_get_exp_max_1)
                    msg += f"{user_1.user_name}修为到达上限，增加修为{user_get_exp_max_1}。"
                else:
                    sql_message.update_exp(user_1.user_id, exp_limit_1)
                    msg += f"{user_1.user_name}增加修为{exp_limit_1}。"
                sql_message.update_power2(user_1.user_id)

                if user_2.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_2.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_2 = max_exp
                else:
                    exp_limit_2 = exp

                if exp_limit_2 >= user_get_exp_max_2:
                    sql_message.update_exp(user_2.user_id, user_get_exp_max_2)
                    msg += f"{user_2.user_name}修为到达上限，增加修为{user_get_exp_max_2}。"
                else:
                    sql_message.update_exp(user_2.user_id, exp_limit_2)
                    msg += f"{user_2.user_name}增加修为{exp_limit_2}。"
                sql_message.update_power2(user_2.user_id)
                sql_message.update_levelrate(user_1.user_id, user_1.level_up_rate + 2)
                sql_message.update_levelrate(user_2.user_id, user_2.level_up_rate + 2)
                two_exp_cd.add_user(user_1.user_id)
                two_exp_cd.add_user(user_2.user_id)
                msg += f"离开时双方互相留法宝为对方护道,双方各增加突破概率2%。"
                await xiuxian_send_message(two_exp, message=msg)

            else:
                exp = int((exp_1 + exp_2) * 0.0055)

                if user_1.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_1.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_1 = max_exp
                else:
                    exp_limit_1 = exp
                if exp_limit_1 >= user_get_exp_max_1:
                    sql_message.update_exp(user_1.user_id, user_get_exp_max_1)
                    msg += f"{user_1.user_name}修为到达上限，增加修为{user_get_exp_max_1}。"
                else:
                    sql_message.update_exp(user_1.user_id, exp_limit_1)
                    msg += f"{user_1.user_name}增加修为{exp_limit_1}。"
                sql_message.update_power2(user_1.user_id)

                if user_2.sect_position is None:
                    max_exp_limit = 4
                else:
                    max_exp_limit = user_2.sect_position
                max_exp = jsondata.sect_config_data()[str(max_exp_limit)]["max_exp"]
                if exp >= max_exp:
                    exp_limit_2 = max_exp
                else:
                    exp_limit_2 = exp
                if exp_limit_2 >= user_get_exp_max_2:
                    sql_message.update_exp(user_2.user_id, user_get_exp_max_2)
                    msg += f"{user_2.user_name}修为到达上限，增加修为{user_get_exp_max_2}。"
                else:
                    sql_message.update_exp(user_2.user_id, exp_limit_2)
                    msg += f"{user_2.user_name}增加修为{exp_limit_2}。"
                sql_message.update_power2(user_2.user_id)
                two_exp_cd.add_user(user_1.user_id)
                two_exp_cd.add_user(user_2.user_id)
                await xiuxian_send_message(two_exp, message=msg)

    else:
        msg = "修仙者应一心向道，务要留恋凡人！"
        await xiuxian_send_message(two_exp, message=msg)


@my_exp_num.handle(parameterless=[Cooldown(at_sender=True), check_player()])
async def my_exp_num_(bot: Bot, event: GroupMessageEvent):
    """
    我的双修次数
    """
    global two_exp_limit
    _, user_info, msg = check_user(event)

    user_id = user_info.user_id
    limit = two_exp_cd.find_user(user_id)
    impart_data = None
    impart_two_exp = impart_data.impart_two_exp if impart_data is not None else 0
    num = (two_exp_limit + impart_two_exp) - limit
    if num <= 0:
        num = 0
    msg = f"道友剩余双修次数{num}次！"
    await xiuxian_send_message(out_closing, message=msg)


class TWO_EXP_CD(object):
    def __init__(self):
        self.dir_path = Path(__file__).parent
        self.data_path = os.path.join(self.dir_path, "two_exp_cd.json")
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except:
            self.info = {"two_exp_cd": {}}
            data = json.dumps(self.info, ensure_ascii=False, indent=4)
            with open(self.data_path, mode="x", encoding="UTF-8") as f:
                f.write(data)
                f.close()
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

    def __save(self):
        """
        :return:保存
        """
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def find_user(self, user_id):
        """
        匹配词条
        :param user_id:
        """
        user_id = str(user_id)
        try:
            if self.data["two_exp_cd"][user_id] >= 0:
                return self.data["two_exp_cd"][user_id]
        except:
            self.data["two_exp_cd"][user_id] = 0
            self.__save()
            return self.data["two_exp_cd"][user_id]

    def add_user(self, user_id) -> bool:
        """
        加入数据
        :param user_id: qq号
        :return: True or False
        """
        user_id = str(user_id)
        if self.find_user(user_id) >= 0:
            self.data["two_exp_cd"][user_id] = self.data["two_exp_cd"][user_id] + 1
            self.__save()
            return True

    def re_data(self):
        """
        重置数据
        """
        self.data = {"two_exp_cd": {}}
        self.__save()


two_exp_cd = TWO_EXP_CD()
