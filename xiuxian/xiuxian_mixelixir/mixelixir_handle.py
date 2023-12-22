import random

from .mix_elixir_data_source import MixElixirExamPlayerData
from ..common.item_json import Items

item = Items()

upper_limit = 10


def format_problem(problem: dict):
    yao_cai_list = problem['yao_cai']
    total = problem['total']
    msg = (f"主药：【{yao_cai_list[0]['name']}】，药性：性热{yao_cai_list[0]['yao_xin']}成，药力：{yao_cai_list[0]['power']}\n"
           f"药引：【{yao_cai_list[1]['name']}】，药性：性寒{yao_cai_list[1]['yao_xin']}成，药力：{yao_cai_list[1]['power']}\n"
           f"辅药：【{yao_cai_list[2]['name']}】，药性：性热{yao_cai_list[2]['yao_xin']}成，药力：{yao_cai_list[2]['power']}\n"
           f"每种药材消耗不能超过{upper_limit}株，药性平衡且药力到达{total}时成丹。 \n"
           f"请写出【{problem['elixir']}】丹方。")
    return msg


def get_mix_elixir_exam_problem():
    elixir_dict = item.get_elixir_data()
    elixir_ids = list(elixir_dict.keys())
    elixir_id = random.choice(elixir_ids)

    yao_cai_dict = item.get_yaocai_data()
    yao_cai_ids = list(yao_cai_dict.keys())

    main_yao_cai_A = random.choice(yao_cai_ids)
    yao_cai_ids.remove(main_yao_cai_A)

    main_yao_cai_B = random.choice(yao_cai_ids)
    yao_cai_ids.remove(main_yao_cai_B)

    main_yao_cai_C = random.choice(yao_cai_ids)

    # 解的集合
    solutions = []

    main_yao_xin_A = random.randint(2, upper_limit - 1)
    main_yao_xin_B = random.randint(2, upper_limit - 1)
    main_yao_xin_C = random.randint(2, upper_limit - 1)

    # 穷举所有可能的解
    for A in range(1, upper_limit):
        for B in range(1, upper_limit):
            for C in range(1, upper_limit):

                if main_yao_xin_A * A - main_yao_xin_B * B + main_yao_xin_C * C == 0:
                    solutions.append((A, B, C))

    powerA = random.randint(2, upper_limit - 1)
    powerB = random.randint(2, upper_limit - 1)
    powerC = random.randint(2, upper_limit - 1)

    if len(solutions) > 0:
        max = 0
        for solution in solutions:
            sum = powerA * solution[0] + powerB * solution[1] + powerC * solution[2]
            if max < sum:
                max = sum
    else:
        raise Exception()

    return {
        "yao_cai": [
            {
                "name": yao_cai_dict[main_yao_cai_A]["name"],
                "id": main_yao_cai_A,
                "yao_xin": main_yao_xin_A,
                "power": powerA
            },
            {
                "name": yao_cai_dict[main_yao_cai_B]["name"],
                "id": main_yao_cai_B,
                "yao_xin": main_yao_xin_B,
                "power": powerB
            },
            {
                "name": yao_cai_dict[main_yao_cai_C]["name"],
                "id": main_yao_cai_C,
                "yao_xin": main_yao_xin_C,
                "power": powerC
            },
        ],
        "total": max,
        "elixir": elixir_dict[elixir_id]["name"]
    }


def check_num(num: int):
    return 0 < num <= 10


def mix_elixir_exam_reward_obtained(problem):
    yao_cai_list = problem["yao_cai"]
    return random.choice(yao_cai_list)


def check_mix_elixir_exam_problem(args, problem):
    try:
        name1 = args[0]
        num1 = int(args[1])
        name2 = args[2]
        num2 = int(args[3])
        name3 = args[4]
        num3 = int(args[5])
        # name4 = args[6]
        # num4 = int(args[7])

        if not (check_num(num1) and check_num(num2) and check_num(num3)):
            return False

        yao_xin1 = problem["yao_cai"][0]["yao_xin"]
        yao_xin2 = problem["yao_cai"][1]["yao_xin"]
        yao_xin3 = problem["yao_cai"][2]["yao_xin"]

        powerA = problem["yao_cai"][0]["power"]
        powerB = problem["yao_cai"][1]["power"]
        powerC = problem["yao_cai"][2]["power"]

        total = problem["total"]

        if (num1 * yao_xin1 - num2 * yao_xin2 + num3 * yao_xin3 == 0
                and num1 * powerA + num2 * powerB + num3 * powerC >= total):
            return True


    except:
        return False
