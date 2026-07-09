import json
from django.shortcuts import render, get_object_or_404
from .forms import CodeSubmitForm
from .code_runner import run_python_code
from .prompt_builder import build_feedback_prompt
from .llm_client import call_llm
from .models import CodeFeedbackRecord  # <-- 新增引入数据库模型

def submit_code(request):
    if request.method == "POST":
        form = CodeSubmitForm(request.POST)

        if form.is_valid():
            llm_choice = form.cleaned_data["llm_choice"]

            problem_statement = form.cleaned_data["problem_statement"]
            lecture_objective = form.cleaned_data["lecture_objective"]
            student_code = form.cleaned_data["student_code"]

            execution_result = run_python_code(student_code)

            prompt = build_feedback_prompt(
                problem_statement=problem_statement,
                student_code=student_code,
                lecture_objective=lecture_objective,
                execution_result=execution_result
            )

            ai_feedback_raw = ""
            ai_feedback_json = None
            ai_error = None

            try:
                # 把你的选择 (kimi 还是 deepseek) 传给通讯员
                ai_feedback_raw = call_llm(prompt, llm_choice) 
                clean_json_str = ai_feedback_raw.strip().strip('```json').strip('```').strip()
                ai_feedback_json = json.loads(clean_json_str)
            except json.JSONDecodeError:
                ai_error = "AI 返回的不是标准的 JSON 格式，无法解析。"
            except Exception as e:
                ai_error = f"调用 AI 时发生错误: {str(e)}"

            # ================= [这是 Week 11 新增的保存逻辑] =================
            # 把当前的数据存入数据库
            CodeFeedbackRecord.objects.create(
                problem_statement=problem_statement,
                lecture_objective=lecture_objective,
                student_code=student_code,
                execution_status=execution_result.get("execution_status", ""),
                execution_stdout=execution_result.get("stdout", ""),
                execution_stderr=execution_result.get("stderr", ""),
                error_category=ai_feedback_json.get("error_category", "") if ai_feedback_json else "",
                feedback_level=ai_feedback_json.get("feedback_level", "") if ai_feedback_json else "",
                concept_reference=ai_feedback_json.get("concept_reference", "") if ai_feedback_json else "",
                feedback_text=ai_feedback_json.get("feedback", "") if ai_feedback_json else "",
                does_reveal_solution=ai_feedback_json.get("does_reveal_solution", False) if ai_feedback_json else False,
                raw_ai_response=ai_feedback_raw,
                ai_error=ai_error or "",
                llm_used=llm_choice, # <--- 数据库保存里，最后加上这一行
            )
            # ===============================================================

            return render(request, "feedback_app/result.html", {
                "problem_statement": problem_statement,
                "lecture_objective": lecture_objective,
                "student_code": student_code,
                "execution_result": execution_result,
                "ai_feedback_raw": ai_feedback_raw,
                "ai_feedback_json": ai_feedback_json,
                "ai_error": ai_error,
                "llm_choice": llm_choice,
            })
    else:
        form = CodeSubmitForm()

    return render(request, "feedback_app/submit.html", {"form": form})

# ================= [这也是 Week 11 新增的：用来查看历史记录] =================
def history(request):
    # 从数据库里按照时间倒序，拿出最近的 20 条记录
    records = CodeFeedbackRecord.objects.order_by("-created_at")[:20]
    return render(request, "feedback_app/history.html", {"records": records})

def history_detail(request, record_id):
    # 根据传进来的 ID，去数据库里把那条具体的记录翻出来
    record = get_object_or_404(CodeFeedbackRecord, id=record_id)
    return render(request, "feedback_app/history_detail.html", {"record": record})