import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def call_llm(prompt: str, model_choice: str = "deepseek") -> str:
    """根据选择调用 DeepSeek 或 Kimi"""
    
    # 动态分配 API 网址、模型名字和密码
    if model_choice == "kimi":
        api_key = os.getenv("KIMI_API_KEY")
        base_url = "https://api.moonshot.cn/v1"
        model_name = "moonshot-v1-8k"
    else:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = "https://api.deepseek.com"
        model_name = "deepseek-chat"

    if not api_key:
        raise ValueError(f"严重错误：没有找到 {model_choice} 的 API Key！")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a programming tutor for beginner Python students. "
                    "You generate educational hints, not full solutions."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content