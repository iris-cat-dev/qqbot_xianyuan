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


def date_diff(new_time , old_time):
    """
    计算日期差
    """
    if isinstance(new_time, datetime.datetime):
        pass
    else:
        new_time = datetime.datetime.strptime(new_time, '%Y-%m-%d %H:%M:%S.%f')

    if isinstance(old_time, datetime.datetime):
        pass
    else:
        old_time = datetime.datetime.strptime(old_time, '%Y-%m-%d %H:%M:%S.%f')

    day = (new_time - old_time).days
    sec = (new_time - old_time).seconds

    return (day * 24 * 60 * 60) + sec
