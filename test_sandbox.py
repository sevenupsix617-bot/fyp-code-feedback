from feedback_app.code_runner import run_python_code

print("=== 测试 1: 语法错误 (缺冒号) ===")
code1 = """
for i in range(5)
    print(i)
"""
result1 = run_python_code(code1)
print(result1['stderr']) 
# 期待看到：SyntaxError: expected ':'


print("\n=== 测试 2: 名字错误 (打错字) ===")
code2 = """
total = 10
print(totall)
"""
result2 = run_python_code(code2)
print(result2['stderr'])
# 期待看到：NameError: name 'totall' is not defined


print("\n=== 测试 3: 类型错误 (文字加数字) ===")
code3 = """
age = 18
print("Age: " + age)
"""
result3 = run_python_code(code3)
print(result3['stderr'])
# 期待看到：TypeError: can only concatenate str (not "int") to str


print("\n=== 测试 4: 死循环超时测试 ===")
code4 = """
while True:
    print("hello")
"""
result4 = run_python_code(code4)
print(result4['stderr'])
# 期待看到：Execution timed out after 3 seconds.