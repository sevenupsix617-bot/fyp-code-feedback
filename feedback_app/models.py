from django.conf import settings
from django.db import models

from .feedback_schema import FEEDBACK_SCHEMA_VERSION
from .output_comparison import COMPARISON_MODE_CHOICES, COMPARISON_MODE_NORMALIZED
from .taxonomy import topic_labels


class Question(models.Model):
    PROVIDER_DEEPSEEK = "deepseek"
    PROVIDER_KIMI = "kimi"

    LLM_PROVIDER_CHOICES = [
        (PROVIDER_DEEPSEEK, "DeepSeek"),
        (PROVIDER_KIMI, "Kimi"),
    ]

    title = models.CharField(max_length=200)
    problem_statement = models.TextField()
    lecture_objective = models.TextField(blank=True, default="")
    sample_input = models.TextField(blank=True, default="")
    expected_output = models.TextField(blank=True, default="")
    test_harness = models.TextField(blank=True, default="")
    comparison_mode = models.CharField(
        max_length=30,
        choices=COMPARISON_MODE_CHOICES,
        default=COMPARISON_MODE_NORMALIZED,
    )
    difficulty = models.CharField(max_length=50, blank=True, default="")
    topic_tags = models.CharField(max_length=255, blank=True, default="")
    default_llm_provider = models.CharField(
        max_length=50,
        choices=LLM_PROVIDER_CHOICES,
        default=PROVIDER_DEEPSEEK,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def topic_label_list(self):
        return topic_labels(self.topic_tags)


class CodeFeedbackRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    problem_statement = models.TextField()
    lecture_objective = models.TextField(blank=True)
    student_code = models.TextField()
    sample_input = models.TextField(blank=True, default="")
    expected_output = models.TextField(blank=True, default="")

    execution_status = models.CharField(max_length=50, blank=True)
    execution_stdout = models.TextField(blank=True)
    execution_stderr = models.TextField(blank=True)
    execution_return_code = models.IntegerField(null=True, blank=True)
    execution_timed_out = models.BooleanField(default=False)
    execution_time_ms = models.PositiveIntegerField(null=True, blank=True)
    actual_output = models.TextField(blank=True, default="")
    output_comparison_status = models.CharField(max_length=50, blank=True, default="")
    comparison_mode = models.CharField(
        max_length=30,
        choices=COMPARISON_MODE_CHOICES,
        default=COMPARISON_MODE_NORMALIZED,
    )

    error_category = models.CharField(max_length=100, blank=True)
    classification_outcome = models.CharField(max_length=30, blank=True, default="")
    peci_error_code = models.CharField(max_length=1, blank=True, default="")
    peci_error_label = models.CharField(max_length=100, blank=True, default="")
    legacy_error_category = models.CharField(max_length=100, blank=True, default="")
    feedback_level = models.CharField(max_length=50, blank=True)
    concept_reference = models.CharField(max_length=200, blank=True)
    feedback_text = models.TextField(blank=True)
    does_reveal_solution = models.BooleanField(default=False)
    uses_runtime_evidence = models.BooleanField(default=False)
    suggested_next_step = models.TextField(blank=True, default="")
    confidence = models.CharField(max_length=50, blank=True, default="")

    prompt_version = models.CharField(max_length=50, blank=True, default="")
    prompt_text = models.TextField(blank=True, default="")
    feedback_schema_version = models.CharField(
        max_length=50,
        blank=True,
        default=FEEDBACK_SCHEMA_VERSION,
    )
    raw_ai_response = models.TextField(blank=True)
    ai_error = models.TextField(blank=True)
    llm_model_name = models.CharField(max_length=100, blank=True, default="")
    llm_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    llm_token_usage = models.JSONField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    evaluation_sample_id = models.CharField(max_length=100, blank=True, default="")
    trajectory_id = models.CharField(max_length=100, blank=True, default="")
    trajectory_attempt_number = models.PositiveIntegerField(null=True, blank=True)
    misconception = models.TextField(blank=True, default="")
    solved = models.BooleanField(default=False)
    ground_truth_category = models.CharField(max_length=100, blank=True, default="")
    json_compliance = models.BooleanField(null=True, blank=True)
    schema_validation_status = models.CharField(max_length=50, blank=True, default="not_validated")
    schema_validation_notes = models.TextField(blank=True, default="")
    solution_leakage_flag = models.BooleanField(null=True, blank=True)

    llm_used = models.CharField(max_length=50, default='deepseek')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.error_category} - {self.created_at}"


class EvaluationRun(models.Model):
    RUN_MODE_DRY_RUN = "dry_run"
    RUN_MODE_LLM = "llm"

    RUN_MODE_CHOICES = [
        (RUN_MODE_DRY_RUN, "Dry run"),
        (RUN_MODE_LLM, "LLM API run"),
    ]

    name = models.CharField(max_length=200)
    dataset_name = models.CharField(max_length=100, default="Refactory")
    dataset_path = models.CharField(max_length=500, blank=True, default="")
    dataset_size = models.PositiveIntegerField(default=0)
    providers = models.JSONField(default=list, blank=True)
    prompt_versions = models.JSONField(default=list, blank=True)
    run_mode = models.CharField(
        max_length=30,
        choices=RUN_MODE_CHOICES,
        default=RUN_MODE_DRY_RUN,
    )
    notes = models.TextField(blank=True, default="")
    summary = models.JSONField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return self.name


class EvaluationResult(models.Model):
    evaluation_run = models.ForeignKey(
        EvaluationRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    sample_id = models.CharField(max_length=100)
    source_dataset = models.CharField(max_length=100, default="Refactory")
    source_record_path = models.CharField(max_length=500, blank=True, default="")
    source_test_input_path = models.CharField(max_length=500, blank=True, default="")
    source_test_output_path = models.CharField(max_length=500, blank=True, default="")
    provider = models.CharField(max_length=50)
    prompt_version = models.CharField(max_length=50)

    ground_truth_category = models.CharField(max_length=100)
    predicted_category = models.CharField(max_length=100, blank=True, default="")
    category_match = models.BooleanField(null=True, blank=True)
    feedback_level = models.CharField(max_length=50, blank=True, default="")
    concept_reference = models.CharField(max_length=200, blank=True, default="")
    feedback_text = models.TextField(blank=True, default="")
    suggested_next_step = models.TextField(blank=True, default="")
    confidence = models.CharField(max_length=50, blank=True, default="")

    json_compliance = models.BooleanField(null=True, blank=True)
    schema_validation_status = models.CharField(max_length=50, blank=True, default="")
    schema_validation_notes = models.TextField(blank=True, default="")
    solution_leakage_flag = models.BooleanField(null=True, blank=True)
    uses_runtime_evidence = models.BooleanField(null=True, blank=True)

    execution_status = models.CharField(max_length=50, blank=True, default="")
    output_comparison_status = models.CharField(max_length=50, blank=True, default="")
    actual_output = models.TextField(blank=True, default="")
    actual_stderr = models.TextField(blank=True, default="")

    prompt_text = models.TextField(blank=True, default="")
    raw_ai_response = models.TextField(blank=True, default="")
    ai_error = models.TextField(blank=True, default="")
    llm_model_name = models.CharField(max_length=100, blank=True, default="")
    llm_latency_ms = models.PositiveIntegerField(null=True, blank=True)
    llm_token_usage = models.JSONField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)

    helpfulness_score = models.PositiveSmallIntegerField(null=True, blank=True)
    lecture_alignment_score = models.PositiveSmallIntegerField(null=True, blank=True)
    actionability_score = models.PositiveSmallIntegerField(null=True, blank=True)
    human_solution_leakage = models.BooleanField(null=True, blank=True)
    human_review_notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["evaluation_run", "sample_id", "provider", "prompt_version"]
        unique_together = ("evaluation_run", "sample_id", "provider", "prompt_version")

    def __str__(self):
        return f"{self.sample_id} - {self.provider} - {self.prompt_version}"
