import math
from collections import Counter

from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from .feedback_schema import PECI_ERROR_CODES
from .models import CodeFeedbackRecord, Question
from .taxonomy import TOPIC_TAXONOMY, parse_topic_tags


NO_ERROR = "No Error"
MATCH_STATUSES = {"exact_match", "normalized_match"}
UNRESOLVED_FILTER = Q(solved=False)
RADAR_LABEL_LINES = {
    "program_structure": ("Program", "Structure"),
    "variables_assignment": ("Variables &", "Assignment"),
    "expressions_operators": ("Expressions &", "Operators"),
    "conditionals_boolean": ("Conditionals &", "Boolean Logic"),
    "iteration_range": ("Iteration &", "Range"),
    "functions_returns": ("Functions &", "Returns"),
    "strings_io": ("Strings &", "Input/Output"),
    "collections_indexing": ("Collections &", "Indexing"),
}


def _add_percent(rows, value_key="total", denominator=None):
    rows = list(rows)
    if denominator is None:
        denominator = max([row.get(value_key, 0) for row in rows], default=0)
    for row in rows:
        row["percent"] = round((row.get(value_key, 0) / denominator) * 100) if denominator else 0
    return rows


def _attempt_score(record):
    return _attempt_score_details(record)["score"]


def _attempt_score_details(record):
    if record.solved:
        return {
            "score": 100,
            "reason": "Solved attempt: No Error agreed with successful matching runtime output.",
        }
    if record.execution_status and record.execution_status != "success":
        return {
            "score": 20,
            "reason": "Execution did not finish successfully.",
        }
    if record.output_comparison_status == "mismatch":
        return {
            "score": 45,
            "reason": "Program ran, but actual output did not match expected output.",
        }
    if record.output_comparison_status in MATCH_STATUSES:
        return {
            "score": 40,
            "reason": "Sample output matched, but feedback still identified an unresolved issue.",
        }
    if record.error_category:
        return {
            "score": 35,
            "reason": "Unresolved issue classified without a decisive output-comparison signal.",
        }
    return {
        "score": 0,
        "reason": "No reliable classification or runtime evidence is available.",
    }


def _radar_point(center_x, center_y, radius, index, total):
    angle = (-math.pi / 2) + ((2 * math.pi * index) / total)
    return (
        round(center_x + math.cos(angle) * radius, 1),
        round(center_y + math.sin(angle) * radius, 1),
        angle,
    )


def _point_string(points):
    return " ".join(f"{x},{y}" for x, y in points)


def build_skill_mastery(user):
    """Build transparent per-topic scores from each attempted question's latest record.

    A question contributes at most one score to each of its fixed topic tags: the
    student's latest saved attempt for that question. When a topic covers multiple
    attempted questions, their latest-attempt scores are averaged. Topics without
    an attempted tagged question retain a score of zero with has_evidence=False.
    """

    records = list(
        CodeFeedbackRecord.objects.filter(user=user, question__isnull=False)
        .select_related("question")
        .order_by("created_at", "id")
    )
    latest_by_question = {}
    attempt_counts = Counter()

    for record in records:
        topic_ids = parse_topic_tags(record.question.topic_tags)
        for topic_id in topic_ids:
            attempt_counts[topic_id] += 1
        latest_by_question[record.question_id] = record

    latest_scores = {topic_id: [] for topic_id in TOPIC_TAXONOMY}
    for record in latest_by_question.values():
        score_details = _attempt_score_details(record)
        for topic_id in parse_topic_tags(record.question.topic_tags):
            latest_scores[topic_id].append(
                {
                    "question_id": record.question_id,
                    "question": record.question.title,
                    "record_id": record.id,
                    "score": score_details["score"],
                    "score_reason": score_details["reason"],
                    "date": record.created_at.strftime("%Y-%m-%d"),
                }
            )

    center_x = 260
    center_y = 190
    max_radius = 128
    label_radius = 168
    topic_count = len(TOPIC_TAXONOMY)
    topics = []

    for index, (topic_id, definition) in enumerate(TOPIC_TAXONOMY.items()):
        evidence = latest_scores[topic_id]
        score = round(sum(item["score"] for item in evidence) / len(evidence)) if evidence else 0
        axis_x, axis_y, angle = _radar_point(
            center_x,
            center_y,
            max_radius,
            index,
            topic_count,
        )
        point_x, point_y, _ = _radar_point(
            center_x,
            center_y,
            max_radius * (score / 100),
            index,
            topic_count,
        )
        label_x, label_y, _ = _radar_point(
            center_x,
            center_y,
            label_radius,
            index,
            topic_count,
        )
        cosine = math.cos(angle)
        label_anchor = "start" if cosine > 0.25 else "end" if cosine < -0.25 else "middle"
        has_evidence = bool(evidence)
        tooltip = (
            f"{definition['label']} | Mastery {score}/100 | "
            f"{len(evidence)} question-level latest score(s) averaged | "
            f"{attempt_counts[topic_id]} saved attempt(s)"
            if has_evidence
            else f"{definition['label']} | No attempted tagged question yet"
        )
        topics.append(
            {
                "id": topic_id,
                "label": definition["label"],
                "label_lines": RADAR_LABEL_LINES.get(topic_id, (definition["label"],)),
                "definition": definition["definition"],
                "score": score,
                "has_evidence": has_evidence,
                "question_count": len(evidence),
                "attempt_count": attempt_counts[topic_id],
                "latest_question_scores": evidence,
                "axis_x": axis_x,
                "axis_y": axis_y,
                "point_x": point_x,
                "point_y": point_y,
                "label_x": label_x,
                "label_y": label_y,
                "label_anchor": label_anchor,
                "tooltip": tooltip,
            }
        )

    grid_polygons = []
    for level in (25, 50, 75, 100):
        points = []
        for index in range(topic_count):
            x, y, _ = _radar_point(
                center_x,
                center_y,
                max_radius * (level / 100),
                index,
                topic_count,
            )
            points.append((x, y))
        grid_polygons.append({"level": level, "points": _point_string(points)})

    return {
        "topics": topics,
        "polygon_points": _point_string(
            [(topic["point_x"], topic["point_y"]) for topic in topics]
        ),
        "grid_polygons": grid_polygons,
        "center_x": center_x,
        "center_y": center_y,
        "has_evidence": any(topic["has_evidence"] for topic in topics),
        "evidence_topic_count": sum(topic["has_evidence"] for topic in topics),
        "aggregation_rule": (
            "For each topic, take the latest saved attempt score for every attempted "
            "question tagged with that topic, then calculate the arithmetic mean."
        ),
    }


def build_skill_timeline(user, topic_id, limit=30):
    if topic_id not in TOPIC_TAXONOMY:
        raise KeyError(topic_id)

    records = list(
        CodeFeedbackRecord.objects.filter(user=user, question__isnull=False)
        .select_related("question")
        .order_by("created_at", "id")
    )
    topic_records = [
        record
        for record in records
        if topic_id in parse_topic_tags(record.question.topic_tags)
    ]
    question_attempt_counts = Counter()
    timeline = []
    for index, record in enumerate(topic_records, start=1):
        question_attempt_counts[record.question_id] += 1
        score_details = _attempt_score_details(record)
        solved = record.solved
        timeline.append(
            {
                "label": f"T{index}",
                "date": record.created_at.strftime("%Y-%m-%d %H:%M"),
                "question": record.question.title,
                "question_attempt": (
                    record.trajectory_attempt_number
                    or question_attempt_counts[record.question_id]
                ),
                "category": record.error_category or "Unclassified",
                "comparison": record.output_comparison_status or "N/A",
                "score": score_details["score"],
                "score_reason": score_details["reason"],
                "solved": solved,
                "solved_label": "Solved" if solved else "Unresolved",
                "record": record,
            }
        )

    display_timeline = timeline[-limit:]
    sparkline, sparkline_nodes = _sparkline_points(display_timeline)
    mastery = build_skill_mastery(user)
    selected_topic = next(topic for topic in mastery["topics"] if topic["id"] == topic_id)
    return {
        "user": user,
        "topic": selected_topic,
        "timeline": display_timeline,
        "sparkline": sparkline,
        "sparkline_nodes": sparkline_nodes,
        "total_attempts": len(timeline),
        "displayed_attempts": len(display_timeline),
        "question_count": len({record.question_id for record in topic_records}),
    }


def _sparkline_points(attempts):
    if not attempts:
        return "", []

    plot_left = 22
    plot_right = 244
    top = 14
    bottom = 56
    spread = bottom - top
    nodes = []
    last_index = len(attempts) - 1

    for index, attempt in enumerate(attempts):
        x = 130 if last_index == 0 else plot_left + (index / last_index) * (plot_right - plot_left)
        y = bottom - (attempt["score"] / 100) * spread
        solved_fragment = (
            f" | {attempt['solved_label']}" if attempt.get("solved_label") else ""
        )
        nodes.append(
            {
                "x": round(x, 1),
                "y": round(y, 1),
                "label": attempt["label"],
                "score": attempt["score"],
                "score_label_y": round(y - 5 if y > top + 10 else y + 10, 1),
                "tooltip": (
                    f"{attempt['label']} | Score {attempt['score']} | "
                    f"{attempt['question']} | {attempt['date']} | "
                    f"{attempt['category']} | {attempt['comparison']}"
                    f"{solved_fragment} | "
                    f"{attempt['score_reason']}"
                ),
            }
        )

    return " ".join(f"{node['x']},{node['y']}" for node in nodes), nodes


def _trend_status(attempts):
    if len(attempts) < 2:
        return (
            "Needs more attempts",
            "Add more saved attempts before interpreting this descriptive trend.",
            True,
        )

    delta = attempts[-1]["score"] - attempts[0]["score"]
    score_range = max(attempt["score"] for attempt in attempts) - min(
        attempt["score"] for attempt in attempts
    )
    delta_text = f"+{delta}" if delta > 0 else str(delta)
    boundary_note = (
        "This is a descriptive heuristic across saved attempts; it does not adjust for "
        "question difficulty or compare separate questions as a formal learning measure."
    )

    if score_range >= 50 and abs(delta) < 20:
        return (
            "Mixed attempts",
            f"Scores vary by {score_range} points, while the latest attempt is {delta_text} points from the first. {boundary_note}",
            True,
        )
    if abs(delta) < 20:
        return (
            "Limited change",
            f"Latest attempt is {delta_text} points from the first. {boundary_note}",
            True,
        )
    if delta > 0:
        return (
            f"Last +{delta} vs first",
            f"Latest attempt is {delta} points above the first saved attempt. {boundary_note}",
            False,
        )
    return (
        f"Last {delta} vs first",
        f"Latest attempt is {abs(delta)} points below the first saved attempt. {boundary_note}",
        True,
    )


def _top_counts(records, field_name, exclude_values=None, limit=3):
    exclude_values = exclude_values or []
    values = (
        records.exclude(**{f"{field_name}__in": ["", *exclude_values]})
        .values(field_name)
        .annotate(total=Count("id"))
        .order_by("-total", field_name)[:limit]
    )
    return list(values)


def build_student_profile(user, limit=12):
    all_records = CodeFeedbackRecord.objects.filter(user=user).select_related("question")
    attempts = list(all_records.order_by("created_at", "id"))
    display_attempts = attempts[-limit:]

    trend = []
    for index, record in enumerate(display_attempts, start=1):
        question_title = record.question.title if record.question else "Manual test"
        score_details = _attempt_score_details(record)
        trend.append(
            {
                "label": f"A{index}",
                "date": record.created_at.strftime("%Y-%m-%d"),
                "question": question_title,
                "category": record.error_category or "Unclassified",
                "comparison": record.output_comparison_status or "N/A",
                "score": score_details["score"],
                "score_reason": score_details["reason"],
                "record": record,
            }
        )

    sparkline, sparkline_nodes = _sparkline_points(trend)
    trend_label, trend_summary, trend_follow_up = _trend_status(trend)

    attempt_total = all_records.count()
    solved_total = all_records.filter(solved=True).count()
    unresolved_total = all_records.filter(UNRESOLVED_FILTER).count()
    question_total = all_records.exclude(question=None).values("question").distinct().count()
    solved_rate = round((solved_total / attempt_total) * 100) if attempt_total else 0

    repeated_errors = _top_counts(all_records, "error_category", exclude_values=[NO_ERROR], limit=4)
    weak_concepts = _top_counts(
        all_records.filter(UNRESOLVED_FILTER),
        "concept_reference",
        exclude_values=["Unknown"],
        limit=4,
    )
    mastered_concepts = _top_counts(
        all_records.filter(solved=True),
        "concept_reference",
        exclude_values=["Unknown"],
        limit=4,
    )
    recent_next_steps = list(
        all_records.filter(UNRESOLVED_FILTER)
        .exclude(suggested_next_step="")
        .order_by("-created_at")
        .values("question__title", "error_category", "suggested_next_step")[:3]
    )

    latest_record = all_records.order_by("-created_at", "-id").first()
    skill_mastery = build_skill_mastery(user)

    return {
        "user": user,
        "attempt_total": attempt_total,
        "solved_total": solved_total,
        "unresolved_total": unresolved_total,
        "question_total": question_total,
        "solved_rate": solved_rate,
        "repeated_errors": repeated_errors,
        "weak_concepts": weak_concepts,
        "mastered_concepts": mastered_concepts,
        "recent_next_steps": recent_next_steps,
        "trend": trend,
        "trend_label": trend_label,
        "trend_summary": trend_summary,
        "trend_follow_up": trend_follow_up,
        "sparkline": sparkline,
        "sparkline_nodes": sparkline_nodes,
        "skill_mastery": skill_mastery,
        "latest_record": latest_record,
    }


def build_class_analytics():
    User = get_user_model()
    submission_count = CodeFeedbackRecord.objects.count()
    classified_count = CodeFeedbackRecord.objects.exclude(classification_outcome="").count()
    non_success_count = CodeFeedbackRecord.objects.filter(UNRESOLVED_FILTER).count()
    question_count = Question.objects.count()

    peci_error_count = CodeFeedbackRecord.objects.filter(
        classification_outcome="peci_error"
    ).exclude(peci_error_code="").count()
    common_errors = _add_percent(
        CodeFeedbackRecord.objects.filter(classification_outcome="peci_error")
        .exclude(peci_error_code="")
        .values("peci_error_code", "peci_error_label")
        .annotate(total=Count("id"))
        .order_by("-total", "peci_error_code")[:10],
        denominator=peci_error_count,
    )
    for item in common_errors:
        item["error_category"] = item["peci_error_label"]

    concept_weakness = _add_percent(
        CodeFeedbackRecord.objects.filter(UNRESOLVED_FILTER)
        .exclude(concept_reference="")
        .exclude(concept_reference="Unknown")
        .values("concept_reference")
        .annotate(total=Count("id"))
        .order_by("-total", "concept_reference")[:8],
        denominator=non_success_count,
    )

    hard_questions = Question.objects.annotate(
        submission_total=Count("codefeedbackrecord"),
        unresolved_total=Count(
            "codefeedbackrecord",
            filter=Q(codefeedbackrecord__solved=False),
        ),
        solved_total=Count(
            "codefeedbackrecord",
            filter=Q(codefeedbackrecord__solved=True),
        ),
        mismatch_total=Count(
            "codefeedbackrecord",
            filter=Q(codefeedbackrecord__output_comparison_status="mismatch"),
        ),
    ).order_by("-unresolved_total", "-mismatch_total", "title")[:8]

    output_breakdown = _add_percent(
        CodeFeedbackRecord.objects.exclude(output_comparison_status="")
        .values("output_comparison_status")
        .annotate(total=Count("id"))
        .order_by("-total", "output_comparison_status")
    )

    students = User.objects.filter(is_staff=False, is_active=True).order_by("username")
    student_profiles = [build_student_profile(student) for student in students]
    student_profiles.sort(key=lambda item: (-item["attempt_total"], item["user"].username))

    saved_next_steps = list(
        CodeFeedbackRecord.objects.filter(UNRESOLVED_FILTER)
        .exclude(suggested_next_step="")
        .select_related("user", "question")
        .order_by("-created_at")[:6]
    )

    instructional_recommendations = build_instructional_recommendations(
        common_errors,
        concept_weakness,
        student_profiles,
    )

    return {
        "submission_count": submission_count,
        "classified_count": classified_count,
        "non_success_count": non_success_count,
        "question_count": question_count,
        "taxonomy_count": len(PECI_ERROR_CODES),
        "common_errors": common_errors,
        "concept_weakness": concept_weakness,
        "hard_questions": hard_questions,
        "student_profiles": student_profiles,
        "output_breakdown": output_breakdown,
        "saved_next_steps": saved_next_steps,
        "instructional_recommendations": instructional_recommendations,
    }


def build_instructional_recommendations(common_errors, concept_weakness, student_profiles):
    recommendations = []

    if common_errors:
        top_error = common_errors[0]
        recommendations.append(
            {
                "title": f"Prioritise {top_error['error_category']}",
                "body": (
                    f"{top_error['total']} unresolved attempts are currently grouped here. "
                    "Use this category for the next mini-review or worked debugging example."
                ),
            }
        )

    if concept_weakness:
        top_concept = concept_weakness[0]
        recommendations.append(
            {
                "title": f"Review {top_concept['concept_reference']}",
                "body": (
                    f"This concept appears in {top_concept['total']} unresolved attempts. "
                    "The evidence comes from saved feedback records, not a free-form model summary."
                ),
            }
        )

    stable_students = [profile for profile in student_profiles if profile["trend_follow_up"]]
    if stable_students:
        names = ", ".join(profile["user"].username for profile in stable_students[:3])
        recommendations.append(
            {
                "title": "Use profile trends for follow-up",
                "body": (
                    f"Check {names} first because their saved attempt trend is not clearly improving."
                ),
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "title": "Keep collecting submissions",
                "body": "More saved attempts are needed before class-level teaching recommendations are reliable.",
            }
        )

    return recommendations
