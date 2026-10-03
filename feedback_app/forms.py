from django import forms
from .models import Question
from .output_comparison import COMPARISON_MODE_CHOICES, COMPARISON_MODE_NORMALIZED
from .prompt_builder import PROMPT_VERSION_CHOICES, PROMPT_STRICT_SCAFFOLDED
from .taxonomy import parse_topic_tags, serialize_topic_tags, topic_choices


class QuestionAdminForm(forms.ModelForm):
    topic_tags = forms.MultipleChoiceField(
        choices=topic_choices(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Fixed Topic Tags",
        help_text=(
            "Select only from the human-defined topic set derived from PECI. "
            "A question may cover more than one topic."
        ),
    )

    class Meta:
        model = Question
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["topic_tags"] = parse_topic_tags(self.instance.topic_tags)

    def clean_topic_tags(self):
        return serialize_topic_tags(self.cleaned_data["topic_tags"])


class CodeSubmitForm(forms.Form):
    LLM_CHOICES = [
        ('deepseek', 'DeepSeek AI'),
        ('kimi', 'Kimi AI'),
    ]
    llm_choice = forms.ChoiceField(
        choices=LLM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select mb-3'}),
        label="AI Tutor"
    )
    prompt_version = forms.ChoiceField(
        choices=PROMPT_VERSION_CHOICES,
        initial=PROMPT_STRICT_SCAFFOLDED,
        widget=forms.Select(attrs={'class': 'form-select mb-3'}),
        label="Prompt Version"
    )

    problem_statement = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Enter the programming question.'}),
        label="Programming Question",
        required=False
    )
    lecture_objective = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: practise for loops and range boundaries.'}),
        label="Lecture Objective",
        required=False
    )
    student_code = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 8, 'placeholder': 'Paste the student Python code.'}),
        label="Student Python Code",
        required=True
    )
    sample_input = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 3,
            'placeholder': 'Optional stdin. Use new lines for multiple input() calls.'
        }),
        label="Sample Input",
        required=False
    )
    expected_output = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 3,
            'placeholder': 'Optional expected output for comparison.'
        }),
        label="Expected Output",
        required=False
    )
    comparison_mode = forms.ChoiceField(
        choices=COMPARISON_MODE_CHOICES,
        initial=COMPARISON_MODE_NORMALIZED,
        widget=forms.Select(attrs={'class': 'form-select mb-3'}),
        label="Output Comparison Mode",
    )


class _StatusQuestionField(forms.ModelChoiceField):
    status_map = {}

    def label_from_instance(self, obj):
        label = str(obj)
        info = self.status_map.get(obj.pk, {})
        if info.get("status") == "solved":
            return f"✓ {label}"
        if info.get("status") == "in_progress":
            return f"↻ {label} ({info.get('attempts', 0)})"
        return f"○ {label}"


class StudentCodeSubmitForm(forms.Form):
    question = _StatusQuestionField(
        queryset=Question.objects.filter(is_active=True),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'form-select mb-3'}),
        label="Question",
    )
    student_code = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 10,
            'placeholder': 'Paste your Python code here.'
        }),
        label="Your Python Code",
        required=True
    )

    def __init__(
        self,
        *args,
        question_queryset=None,
        question_status=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if question_queryset is not None:
            self.fields["question"].queryset = question_queryset
        if question_status is not None:
            self.fields["question"].status_map = question_status
