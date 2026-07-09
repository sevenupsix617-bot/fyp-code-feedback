from django.db import models

class CodeFeedbackRecord(models.Model):
    problem_statement = models.TextField()
    lecture_objective = models.TextField(blank=True)
    student_code = models.TextField()

    execution_status = models.CharField(max_length=50, blank=True)
    execution_stdout = models.TextField(blank=True)
    execution_stderr = models.TextField(blank=True)

    error_category = models.CharField(max_length=100, blank=True)
    feedback_level = models.CharField(max_length=50, blank=True)
    concept_reference = models.CharField(max_length=200, blank=True)
    feedback_text = models.TextField(blank=True)
    does_reveal_solution = models.BooleanField(default=False)

    raw_ai_response = models.TextField(blank=True)
    ai_error = models.TextField(blank=True)

# 记录使用的是哪个 AI
    llm_used = models.CharField(max_length=50, default='deepseek')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.error_category} - {self.created_at}"