import datetime


def number_to(num):
    '''
    递归实现，精确为最大单位值 + 小数点后一位
    '''

    def strofsize(num, level):
        if level >= 2:
            return num, level
        elif num >= 10000:
            num /= 10000
            level += 1
            return strofsize(num, level)
        else:
            return num, level

    units = ['', '万', '亿']
    num, level = strofsize(num, 0)
    if level > len(units):
        level -= 1
    return '{}{}'.format(round(num, 1), units[level])


def time_diff_min(old_time: datetime.datetime, new_time: datetime.datetime, diff: int) -> int:
    """
    计算日期差
    """
    return int(((old_time + datetime.timedelta(minutes=diff)) - new_time).total_seconds() / 60)


def is_today(timestamp):
    # 将时间戳转换为Python的datetime对象
    dt_object = datetime.datetime.fromtimestamp(timestamp)

    # 获取今天的日期
    today = datetime.datetime.today().date()

    # 获取时间戳对应的日期
    dt_date = dt_object.date()

    # 判断两个日期是否相同
    return today == dt_date
