from feedback_app.llm_client import call_deepseek

print("正在呼叫 DeepSeek 大师思考中...")

prompt = """
Please analyze this beginner Python code.

Problem:
Print numbers from 0 to 4.

Student code:
for i in range(5)
    print(i)

Please identify the error category and give a beginner-friendly hint.
Do not provide the full corrected code.
"""

result = call_deepseek(prompt)
print("\n=== AI 大师的回复 ===")
print(result)