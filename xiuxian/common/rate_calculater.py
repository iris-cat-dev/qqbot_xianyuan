import random


def calculated( rate: dict) -> str:
    """
    根据概率计算，轮盘型
    :rate:格式{"数据名":"获取几率"}
    :return: 数据名
    """

    get_list = []  # 概率区间存放

    n = 1
    for name, value in rate.items():  # 生成数据区间
        value_rate = int(value)
        list_rate = [_i for _i in range(n, value_rate + n)]
        get_list.append(list_rate)
        n += value_rate

    now_n = n - 1
    get_random = random.randint(1, now_n)  # 抽取随机数

    index_num = None
    for list_r in get_list:
        if get_random in list_r:  # 判断随机在那个区间
            index_num = get_list.index(list_r)
            break

    return list(rate.keys())[index_num]
