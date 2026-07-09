def build_feedback_prompt(
    problem_statement: str,
    student_code: str,
    lecture_objective: str,
    execution_result: dict
) -> str:
    """
    把学生的信息和沙盒的报错结果，拼装成给 AI 的终极命令。
    """
    prompt = f"""
You are an AI programming tutor for beginner Python students.

Your task is to generate educational feedback for a student's incorrect Python submission.

Important rules:
1. Do NOT provide the full corrected code. (绝不能提供完整代码)
2. Do NOT directly reveal the final answer. (绝不能直接透露答案)
3. Give scaffolded hints that help the student think. (给出启发性的提示)
4. Use beginner-friendly language. (语气要友好)
5. Refer to the programming question and lecture objective when relevant.
6. Identify the most likely error category.
7. Return ONLY valid JSON. Do not include markdown formatting like ```json.

Programming Question:
{problem_statement}

Lecture Objective / Course Concept:
{lecture_objective if lecture_objective else "No specific lecture objective provided."}

Student Code:
{student_code}

Execution Result:
Status: {execution_result.get("execution_status")}
Standard Output:
{execution_result.get("stdout")}
Error Output:
{execution_result.get("stderr")}

Return the result STRICTLY in this JSON format:
{{
  "error_category": "Syntax Error / Indentation Error / Type Error / Name Error / Logic Error / Unknown",
  "feedback_level": "Level 1 / Level 2 / Level 3",
  "concept_reference": "Relevant Python concept",
  "feedback": "Beginner-friendly feedback without giving the full solution",
  "does_reveal_solution": false
}}
"""
    return prompt