import json
import time
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, IntegerField, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .ai_response import detect_solution_leakage, parse_ai_feedback_with_metadata
from .analytics import (
    build_class_analytics,
    build_current_status,
    build_skill_timeline,
    build_student_profile,
)
from .code_runner import run_python_code
from .code_review import build_code_review
from .feedback_schema import FEEDBACK_SCHEMA_VERSION
from .forms import CodeSubmitForm, StudentCodeSubmitForm
from .json_repair import (
    combine_json_repair_responses,
    json_repair_schema_notes,
    merge_llm_call_metadata,
    should_retry_invalid_json,
)
from .llm_client import call_llm_with_metadata, get_llm_model_name
from .models import CodeFeedbackRecord, Question
from .output_comparison import (
    COMPARISON_MODE_NORMALIZED,
    COMPARISON_MODE_STRICT,
    EXACT_MATCH,
    NORMALIZED_MATCH,
    compare_outputs,
)
from .prompt_builder import (
    PROMPT_STRICT_SCAFFOLDED,
    build_feedback_prompt,
    build_json_repair_prompt,
)
from .taxonomy import TOPIC_TAXONOMY, parse_topic_tags


def _require_staff(user):
    if not user.is_staff:
        raise PermissionDenied("This page is only available to instructor accounts.")


def _latest_record_is_solved(record):
    if record.solved:
        return True
    return bool(
        record.classification_outcome == "no_error"
        and record.execution_status == "success"
        and record.output_comparison_status in {EXACT_MATCH, NORMALIZED_MATCH}
    )


def _build_student_question_status(user, questions):
    question_list = list(questions)
    question_ids = [question.pk for question in question_list]
    attempt_counts = defaultdict(int)
    latest_records = {}

    records = CodeFeedbackRecord.objects.filter(
        user=user,
        question_id__in=question_ids,
    ).order_by("question_id", "-created_at", "-id")
    for record in records:
        attempt_counts[record.question_id] += 1
        latest_records.setdefault(record.question_id, record)

    status_map = {}
    for question in question_list:
        attempts = attempt_counts[question.pk]
        latest_record = latest_records.get(question.pk)
        if latest_record is None:
            status = "not_started"
            status_badge = "Not started"
        elif _latest_record_is_solved(latest_record):
            status = "solved"
            status_badge = "Solved"
        else:
            status = "in_progress"
            attempt_label = "attempt" if attempts == 1 else "attempts"
            status_badge = f"In progress - {attempts} {attempt_label}"

        status_map[question.pk] = {"status": status, "attempts": attempts}
        question.status = status
        question.attempts = attempts
        question.status_badge = status_badge

    status_priority = {"in_progress": 0, "not_started": 1, "solved": 2}
    sorted_questions = sorted(
        question_list,
        key=lambda question: (
            status_priority[question.status],
            question.title.casefold(),
        ),
    )
    ordered_ids = [question.pk for question in sorted_questions]
    if not ordered_ids:
        return sorted_questions, Question.objects.none(), status_map

    status_order = Case(
        *[
            When(pk=question_id, then=position)
            for position, question_id in enumerate(ordered_ids)
        ],
        default=len(ordered_ids),
        output_field=IntegerField(),
    )
    question_queryset = (
        Question.objects.filter(pk__in=ordered_ids)
        .annotate(_status_order=status_order)
        .order_by("_status_order")
    )
    return sorted_questions, question_queryset, status_map


@login_required
def home(request):
    if request.user.is_staff:
        return redirect("instructor_dashboard")
    return redirect("student_submit")


def _generate_feedback_record(
    *,
    user=None,
    question=None,
    problem_statement: str,
    lecture_objective: str,
    student_code: str,
    topic_tags: str = "",
    sample_input: str = "",
    expected_output: str = "",
    comparison_mode: str = COMPARISON_MODE_NORMALIZED,
    llm_choice: str = "deepseek",
    prompt_version: str = PROMPT_STRICT_SCAFFOLDED,
    test_harness: str = "",
    trajectory_id: str = "",
    trajectory_attempt_number: int | None = None,
):
    comparison_mode = comparison_mode or COMPARISON_MODE_NORMALIZED

    execution_result = run_python_code(
        student_code,
        sample_input=sample_input,
        test_harness=test_harness,
    )
    output_comparison_status = compare_outputs(
        actual_output=execution_result.get("stdout", ""),
        expected_output=expected_output,
        execution_status=execution_result.get("execution_status", ""),
        mode=comparison_mode,
    )

    prompt = build_feedback_prompt(
        problem_statement=problem_statement,
        student_code=student_code,
        lecture_objective=lecture_objective,
        execution_result=execution_result,
        sample_input=sample_input,
        expected_output=expected_output,
        test_harness=test_harness,
        topic_tags=topic_tags,
        output_comparison_status=output_comparison_status,
        comparison_mode=comparison_mode,
        prompt_version=prompt_version,
    )

    ai_feedback_raw = ""
    ai_feedback_json = None
    ai_error = None
    llm_latency_ms = None
    llm_model_name = get_llm_model_name(llm_choice)
    llm_token_usage = {}
    estimated_cost = None
    feedback_schema_version = FEEDBACK_SCHEMA_VERSION
    schema_validation_status = ""
    schema_validation_notes = ""
    solution_leakage_flag = False
    prompt_for_record = prompt

    try:
        llm_start = time.monotonic()
        llm_result = call_llm_with_metadata(prompt, llm_choice)
        llm_latency_ms = int((time.monotonic() - llm_start) * 1000)
        ai_feedback_raw = llm_result["content"]
        parsed_feedback = parse_ai_feedback_with_metadata(ai_feedback_raw)
        ai_feedback_json = parsed_feedback["feedback_json"]
        ai_error = parsed_feedback["error"]
        feedback_schema_version = parsed_feedback["feedback_schema_version"]
        schema_validation_status = parsed_feedback["schema_validation_status"]
        schema_validation_notes = parsed_feedback["schema_validation_notes"]

        if should_retry_invalid_json(parsed_feedback, llm_result):
            initial_parse_error = parsed_feedback["error"]
            initial_raw_response = ai_feedback_raw
            repair_prompt = build_json_repair_prompt(prompt)
            prompt_for_record = repair_prompt
            try:
                repair_start = time.monotonic()
                repair_result = call_llm_with_metadata(repair_prompt, llm_choice)
                repair_latency_ms = int((time.monotonic() - repair_start) * 1000)
                repair_raw_response = repair_result["content"]
                repair_parsed = parse_ai_feedback_with_metadata(repair_raw_response)
                llm_result = merge_llm_call_metadata(llm_result, repair_result)
                llm_latency_ms += repair_latency_ms
                ai_feedback_raw = combine_json_repair_responses(
                    initial_raw_response,
                    repair_raw_response,
                )
                parsed_feedback = repair_parsed
                ai_feedback_json = parsed_feedback["feedback_json"]
                ai_error = parsed_feedback["error"]
                feedback_schema_version = parsed_feedback["feedback_schema_version"]
                schema_validation_status = parsed_feedback["schema_validation_status"]
                schema_validation_notes = json_repair_schema_notes(
                    initial_parse_error,
                    parsed_feedback["schema_validation_notes"],
                    ai_feedback_json is not None,
                )
            except Exception as repair_exc:
                ai_error = f"AI JSON repair call failed: {str(repair_exc)}"
                schema_validation_notes = json_repair_schema_notes(
                    initial_parse_error,
                    ai_error,
                    False,
                )

        llm_model_name = llm_result.get("model_name") or llm_model_name
        llm_token_usage = llm_result.get("usage") or {}
        estimated_cost = llm_result.get("estimated_cost")
        solution_leakage_flag = detect_solution_leakage(ai_feedback_raw, ai_feedback_json)
    except Exception as e:
        ai_error = f"AI call failed: {str(e)}"
        schema_validation_status = schema_validation_status or "llm_call_failed"
        schema_validation_notes = ai_error

    solved = bool(
        ai_feedback_json
        and ai_feedback_json.get("classification_outcome") == "no_error"
        and execution_result.get("execution_status") == "success"
        and output_comparison_status in {EXACT_MATCH, NORMALIZED_MATCH}
    )

    record = CodeFeedbackRecord.objects.create(
        user=user,
        question=question,
        problem_statement=problem_statement,
        lecture_objective=lecture_objective,
        student_code=student_code,
        sample_input=sample_input,
        expected_output=expected_output,
        execution_status=execution_result.get("execution_status", ""),
        execution_stdout=execution_result.get("stdout", ""),
        execution_stderr=execution_result.get("stderr", ""),
        execution_return_code=execution_result.get("return_code"),
        execution_timed_out=execution_result.get("timed_out", False),
        execution_time_ms=execution_result.get("execution_time_ms"),
        actual_output=execution_result.get("stdout", ""),
        output_comparison_status=output_comparison_status,
        comparison_mode=comparison_mode,
        error_category=ai_feedback_json.get("error_category", "") if ai_feedback_json else "",
        classification_outcome=ai_feedback_json.get("classification_outcome", "") if ai_feedback_json else "",
        solved=solved,
        peci_error_code=ai_feedback_json.get("peci_error_code", "") if ai_feedback_json else "",
        peci_error_label=ai_feedback_json.get("peci_error_label", "") if ai_feedback_json else "",
        legacy_error_category=ai_feedback_json.get("legacy_error_category", "") if ai_feedback_json else "",
        feedback_level=ai_feedback_json.get("feedback_level", "") if ai_feedback_json else "",
        concept_reference=ai_feedback_json.get("concept_reference", "") if ai_feedback_json else "",
        misconception=ai_feedback_json.get("misconception", "") if ai_feedback_json else "",
        feedback_text=ai_feedback_json.get("feedback", "") if ai_feedback_json else "",
        does_reveal_solution=ai_feedback_json.get("does_reveal_solution", False) if ai_feedback_json else False,
        uses_runtime_evidence=ai_feedback_json.get("uses_runtime_evidence", False) if ai_feedback_json else False,
        suggested_next_step=ai_feedback_json.get("suggested_next_step", "") if ai_feedback_json else "",
        confidence=str(ai_feedback_json.get("confidence", "")) if ai_feedback_json else "",
        prompt_version=prompt_version,
        prompt_text=prompt_for_record,
        feedback_schema_version=feedback_schema_version,
        raw_ai_response=ai_feedback_raw,
        ai_error=ai_error or "",
        llm_model_name=llm_model_name,
        llm_latency_ms=llm_latency_ms,
        llm_token_usage=llm_token_usage or None,
        estimated_cost=estimated_cost,
        json_compliance=ai_feedback_json is not None,
        schema_validation_status=schema_validation_status,
        schema_validation_notes=schema_validation_notes,
        solution_leakage_flag=solution_leakage_flag,
        llm_used=llm_choice,
        trajectory_id=trajectory_id,
        trajectory_attempt_number=trajectory_attempt_number,
    )

    return {
        "record": record,
        "problem_statement": problem_statement,
        "lecture_objective": lecture_objective,
        "student_code": student_code,
        "code_lines": student_code.splitlines() or [""],
        "code_review": build_code_review(
            student_code,
            execution_result.get("execution_status", ""),
            execution_result.get("stderr", ""),
        ),
        "topic_tags": topic_tags,
        "sample_input": sample_input,
        "expected_output": expected_output,
        "comparison_mode": comparison_mode,
        "execution_result": execution_result,
        "output_comparison_status": output_comparison_status,
        "ai_feedback_raw": ai_feedback_raw,
        "ai_feedback_json": ai_feedback_json,
        "ai_error": ai_error,
        "llm_choice": llm_choice,
        "prompt_version": prompt_version,
        "llm_latency_ms": llm_latency_ms,
        "llm_model_name": llm_model_name,
        "llm_token_usage": llm_token_usage,
        "estimated_cost": estimated_cost,
        "feedback_schema_version": feedback_schema_version,
        "schema_validation_status": schema_validation_status,
        "schema_validation_notes": schema_validation_notes,
        "solution_leakage_flag": solution_leakage_flag,
    }


@login_required
def submit_code(request):
    _require_staff(request.user)

    if request.method == "POST":
        form = CodeSubmitForm(request.POST)

        if form.is_valid():
            context = _generate_feedback_record(
                user=request.user if request.user.is_authenticated else None,
                problem_statement=form.cleaned_data["problem_statement"],
                lecture_objective=form.cleaned_data["lecture_objective"],
                student_code=form.cleaned_data["student_code"],
                sample_input=form.cleaned_data["sample_input"],
                expected_output=form.cleaned_data["expected_output"],
                comparison_mode=form.cleaned_data["comparison_mode"],
                llm_choice=form.cleaned_data["llm_choice"],
                prompt_version=form.cleaned_data["prompt_version"],
            )
            return render(request, "feedback_app/result.html", context)
    else:
        form = CodeSubmitForm()

    return render(request, "feedback_app/submit.html", {"form": form})


@login_required
def student_submit(request):
    if request.user.is_staff:
        return redirect("instructor_dashboard")

    questions = Question.objects.filter(is_active=True)
    topic_focus = None
    if request.method == "GET" and not request.GET.get("retry"):
        topic_id = request.GET.get("topic", "").strip()
        if topic_id:
            topic_focus = TOPIC_TAXONOMY.get(topic_id)
            if topic_focus is None:
                raise Http404("Unknown fixed topic.")
            questions = [
                question for question in questions
                if topic_id in parse_topic_tags(question.topic_tags)
            ]
    sorted_questions, question_queryset, status_map = _build_student_question_status(
        request.user,
        questions,
    )

    retry_record = None
    if request.method == "POST":
        form = StudentCodeSubmitForm(request.POST)

        if form.is_valid():
            question = form.cleaned_data["question"]
            previous = (
                CodeFeedbackRecord.objects.filter(user=request.user, question=question)
                .order_by("-created_at", "-id")
                .first()
            )
            if previous and previous.trajectory_id:
                trajectory_id = previous.trajectory_id
                trajectory_attempt_number = (previous.trajectory_attempt_number or 0) + 1
            else:
                trajectory_id = f"{request.user.pk}-{question.pk}-{time.time_ns()}"
                trajectory_attempt_number = 1
            context = _generate_feedback_record(
                user=request.user,
                question=question,
                problem_statement=question.problem_statement,
                lecture_objective=question.lecture_objective,
                student_code=form.cleaned_data["student_code"],
                topic_tags=question.topic_tags,
                sample_input=question.sample_input,
                expected_output=question.expected_output,
                comparison_mode=question.comparison_mode,
                llm_choice=question.default_llm_provider,
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                test_harness=question.test_harness,
                trajectory_id=trajectory_id,
                trajectory_attempt_number=trajectory_attempt_number,
            )
            context["question"] = question
            return render(request, "feedback_app/result.html", context)
    else:
        initial = {}
        retry_record_id = request.GET.get("retry")
        if retry_record_id:
            retry_record = get_object_or_404(
                CodeFeedbackRecord.objects.select_related("question"),
                pk=retry_record_id,
                user=request.user,
                question__is_active=True,
            )
            initial = {
                "question": retry_record.question,
                "student_code": retry_record.student_code,
            }
        elif topic_focus and sorted_questions:
            initial["question"] = sorted_questions[0]
        form = StudentCodeSubmitForm(
            initial=initial,
            question_queryset=question_queryset,
            question_status=status_map,
        )

    return render(
        request,
        "feedback_app/student_submit.html",
        {
            "form": form,
            "questions": sorted_questions,
            "retry_record": retry_record,
            "topic_focus": topic_focus,
        },
    )


@login_required
def instructor_dashboard(request):
    _require_staff(request.user)

    User = get_user_model()
    question_count = Question.objects.count()
    active_question_count = Question.objects.filter(is_active=True).count()
    inactive_question_count = question_count - active_question_count
    strict_question_count = Question.objects.filter(comparison_mode=COMPARISON_MODE_STRICT).count()
    normalized_question_count = Question.objects.filter(
        comparison_mode=COMPARISON_MODE_NORMALIZED
    ).count()
    student_count = User.objects.filter(is_staff=False, is_active=True).count()
    submission_count = CodeFeedbackRecord.objects.count()
    common_errors = (
        CodeFeedbackRecord.objects.filter(classification_outcome="peci_error")
        .exclude(peci_error_code="")
        .values("peci_error_code", "peci_error_label")
        .annotate(total=Count("id"))
        .order_by("-total", "peci_error_code")[:10]
    )
    for item in common_errors:
        item["error_category"] = item["peci_error_label"]
    provider_breakdown = (
        Question.objects.values("default_llm_provider")
        .annotate(total=Count("id"))
        .order_by("default_llm_provider")
    )
    output_breakdown = (
        CodeFeedbackRecord.objects.exclude(output_comparison_status="")
        .values("output_comparison_status")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )
    questions = Question.objects.annotate(
        submission_total=Count("codefeedbackrecord")
    ).order_by("title")
    recent_records = CodeFeedbackRecord.objects.select_related("user", "question")[:8]

    return render(
        request,
        "feedback_app/instructor_dashboard.html",
        {
            "question_count": question_count,
            "active_question_count": active_question_count,
            "inactive_question_count": inactive_question_count,
            "strict_question_count": strict_question_count,
            "normalized_question_count": normalized_question_count,
            "student_count": student_count,
            "submission_count": submission_count,
            "common_errors": common_errors,
            "provider_breakdown": provider_breakdown,
            "output_breakdown": output_breakdown,
            "questions": questions,
            "recent_records": recent_records,
        },
    )


@login_required
def analytics_dashboard(request):
    _require_staff(request.user)

    return render(request, "feedback_app/analytics.html", build_class_analytics())


@login_required
def student_profile(request, user_id):
    _require_staff(request.user)

    User = get_user_model()
    student = get_object_or_404(User, pk=user_id, is_staff=False)
    return render(
        request,
        "feedback_app/student_profile.html",
        {
            "profile": build_student_profile(student),
            "is_own_profile": False,
        },
    )


@login_required
def my_profile(request):
    if request.user.is_staff:
        return redirect("analytics_dashboard")

    return render(
        request,
        "feedback_app/student_profile.html",
        {
            "profile": build_student_profile(request.user),
            "is_own_profile": True,
        },
    )


@login_required
def student_current_status(request, user_id):
    _require_staff(request.user)

    User = get_user_model()
    student = get_object_or_404(User, pk=user_id, is_staff=False)
    return render(
        request,
        "feedback_app/current_status.html",
        {"status": build_current_status(student), "is_own_profile": False},
    )


@login_required
def my_current_status(request):
    if request.user.is_staff:
        return redirect("analytics_dashboard")

    return render(
        request,
        "feedback_app/current_status.html",
        {"status": build_current_status(request.user), "is_own_profile": True},
    )


@login_required
def student_skill_detail(request, user_id, topic_id):
    User = get_user_model()
    student = get_object_or_404(User, pk=user_id, is_staff=False)
    if not request.user.is_staff and request.user.id != student.id:
        raise PermissionDenied("You can only view your own skill evidence.")

    try:
        skill = build_skill_timeline(student, topic_id)
    except KeyError as exc:
        raise Http404("Unknown fixed topic.") from exc

    return render(
        request,
        "feedback_app/student_skill_detail.html",
        {
            "skill": skill,
            "is_own_profile": request.user.id == student.id,
        },
    )


@login_required
def history(request):
    records = CodeFeedbackRecord.objects.select_related("user", "question")
    students = []
    questions = []
    selected_student_id = None
    selected_question_id = None
    selected_attempt_id = request.GET.get("attempt", "").strip()

    if not request.user.is_staff:
        records = records.filter(user=request.user)
    else:
        User = get_user_model()
        students = User.objects.filter(is_staff=False).order_by("username")
        questions = Question.objects.order_by("title")

        try:
            selected_student_id = int(request.GET.get("student", ""))
        except ValueError:
            selected_student_id = None

        try:
            selected_question_id = int(request.GET.get("question", ""))
        except ValueError:
            selected_question_id = None

        if selected_student_id:
            records = records.filter(user_id=selected_student_id)
        if selected_question_id:
            records = records.filter(question_id=selected_question_id)

    if selected_attempt_id:
        try:
            selected_attempt_pk = int(selected_attempt_id)
        except ValueError as exc:
            raise Http404("Submission not found.") from exc
        selected_record = get_object_or_404(records, pk=selected_attempt_pk)
        if selected_record.trajectory_id:
            records = records.filter(
                user_id=selected_record.user_id,
                question_id=selected_record.question_id,
                trajectory_id=selected_record.trajectory_id,
            )
        else:
            records = records.filter(pk=selected_record.pk)

    history_groups = []
    groups_by_key = {}
    for record in records.order_by("-created_at", "-id").iterator():
        key = (
            (record.user_id, record.question_id, record.trajectory_id)
            if record.trajectory_id
            else ("single", record.pk)
        )
        group = groups_by_key.get(key)
        if group is None:
            if len(history_groups) >= 20:
                continue
            group = {
                "latest_record": record,
                "records": [],
                "is_solved": _latest_record_is_solved(record),
            }
            groups_by_key[key] = group
            history_groups.append(group)
        group["records"].append(record)

    for group in history_groups:
        group["records"].reverse()
        group["attempt_count"] = len(group["records"])

    records = [record for group in history_groups for record in group["records"]]
    return render(
        request,
        "feedback_app/history.html",
        {
            "records": records,
            "history_groups": history_groups,
            "selected_attempt_id": selected_attempt_id,
            "students": students,
            "questions": questions,
            "selected_student_id": selected_student_id,
            "selected_question_id": selected_question_id,
        },
    )


@login_required
def history_detail(request, record_id):
    record = get_object_or_404(
        CodeFeedbackRecord.objects.select_related("user", "question"),
        id=record_id,
    )
    if not request.user.is_staff and record.user_id != request.user.id:
        raise PermissionDenied("You can only view your own submission records.")

    return render(
        request,
        "feedback_app/history_detail.html",
        {
            "record": record,
            "code_lines": record.student_code.splitlines() or [""],
            "code_review": build_code_review(
                record.student_code, record.execution_status, record.execution_stderr
            ),
        },
    )
