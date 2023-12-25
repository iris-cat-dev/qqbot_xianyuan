import json

import zhipuai

api_key = "06d37f9697a8988e3c69aab61f8cf129.mJ9KNw6TFf34zsp1"


def async_invoke_example():
    response = zhipuai.model_api.async_invoke(
        model="chatglm_turbo",
        prompt=[{"role": "user", "content": "人工智能"}],
        top_p=0.7,
        temperature=0.9,
    )
    print(response)


def request_gpt(prompt):
    print("prompt: " + prompt)
    zhipuai.api_key = api_key
    response = zhipuai.model_api.invoke(
        model="chatglm_turbo",
        prompt=[{"role": "user", "content": prompt}],
        top_p=0.7,
        temperature=0.9,
    )
    #print(json.dumps(response))
    if response["code"] == 200:
        return True, response["data"]["choices"][0]["content"]
    else:
        return False, ""


if __name__ == "__main__":
    pass
    # invoke_example()
