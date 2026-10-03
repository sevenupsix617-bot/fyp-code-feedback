from django.contrib import admin
from .forms import QuestionAdminForm
from .models import CodeFeedbackRecord, EvaluationResult, EvaluationRun, Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    form = QuestionAdminForm
    list_display = (
        "title",
        "difficulty",
        "topic_tags",
        "comparison_mode",
        "default_llm_provider",
        "is_active",
        "updated_at",
    )
    list_filter = ("comparison_mode", "default_llm_provider", "is_active", "difficulty")
    list_editable = ("comparison_mode", "default_llm_provider", "is_active")
    search_fields = ("title", "problem_statement", "lecture_objective", "topic_tags")
    fieldsets = (
        ("Question", {
            "fields": ("title", "problem_statement", "difficulty", "topic_tags", "is_active"),
        }),
        ("Teaching Context", {
            "fields": ("lecture_objective",),
        }),
        ("Runtime Evidence", {
            "fields": ("sample_input", "expected_output", "test_harness", "comparison_mode"),
        }),
        ("LLM Defaults", {
            "fields": ("default_llm_provider",),
        }),
    )


@admin.register(CodeFeedbackRecord)
class CodeFeedbackRecordAdmin(admin.ModelAdmin):
    list_select_related = ("user", "question")
    list_display = (
        "id",
        "user",
        "question",
        "solved",
        "error_category",
        "classification_outcome",
        "solved",
        "peci_error_code",
        "output_comparison_status",
        "comparison_mode",
        "llm_used",
        "prompt_version",
        "schema_validation_status",
        "created_at",
    )
    list_filter = (
        "llm_used",
        "prompt_version",
        "execution_status",
        "output_comparison_status",
        "comparison_mode",
        "error_category",
        "classification_outcome",
        "peci_error_code",
        "does_reveal_solution",
        "uses_runtime_evidence",
        "schema_validation_status",
        "created_at",
    )
    date_hierarchy = "created_at"
    search_fields = (
        "problem_statement",
        "lecture_objective",
        "student_code",
        "feedback_text",
        "raw_ai_response",
        "schema_validation_notes",
    )
    readonly_fields = (
        "created_at",
        "prompt_text",
        "raw_ai_response",
        "llm_token_usage",
        "estimated_cost",
    )


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "dataset_name",
        "dataset_size",
        "run_mode",
        "started_at",
        "completed_at",
    )
    list_filter = ("run_mode", "dataset_name", "started_at")
    search_fields = ("name", "dataset_path", "notes")
    readonly_fields = ("started_at", "completed_at", "summary")


@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_select_related = ("evaluation_run",)
    list_display = (
        "sample_id",
        "evaluation_run",
        "provider",
        "prompt_version",
        "ground_truth_category",
        "predicted_category",
        "category_match",
        "json_compliance",
        "solution_leakage_flag",
    )
    list_filter = (
        "provider",
        "prompt_version",
        "ground_truth_category",
        "predicted_category",
        "category_match",
        "json_compliance",
        "schema_validation_status",
        "solution_leakage_flag",
        "helpfulness_score",
        "lecture_alignment_score",
    )
    search_fields = (
        "sample_id",
        "source_record_path",
        "feedback_text",
        "raw_ai_response",
        "ai_error",
    )
    readonly_fields = (
        "prompt_text",
        "raw_ai_response",
        "llm_token_usage",
        "estimated_cost",
        "created_at",
    )
    fieldsets = (
        ("Evaluation Condition", {
            "fields": (
                "evaluation_run",
                "sample_id",
                "provider",
                "prompt_version",
                "source_dataset",
                "source_record_path",
                "source_test_input_path",
                "source_test_output_path",
            ),
        }),
        ("Automatic Metrics", {
            "fields": (
                "ground_truth_category",
                "predicted_category",
                "category_match",
                "json_compliance",
                "schema_validation_status",
                "schema_validation_notes",
                "solution_leakage_flag",
                "uses_runtime_evidence",
                "llm_latency_ms",
                "llm_token_usage",
                "estimated_cost",
            ),
        }),
        ("Human Review", {
            "fields": (
                "helpfulness_score",
                "lecture_alignment_score",
                "actionability_score",
                "human_solution_leakage",
                "human_review_notes",
                "reviewed_at",
            ),
        }),
        ("Feedback Evidence", {
            "fields": (
                "feedback_level",
                "concept_reference",
                "feedback_text",
                "suggested_next_step",
                "confidence",
                "execution_status",
                "output_comparison_status",
                "actual_output",
                "actual_stderr",
                "prompt_text",
                "raw_ai_response",
                "ai_error",
                "llm_model_name",
                "created_at",
            ),
        }),
    )
