from django import forms

class CodeSubmitForm(forms.Form):
    # 新增：让用户选择 AI 老师
    LLM_CHOICES = [
        ('deepseek', 'DeepSeek AI (推荐)'),
        ('kimi', 'Kimi 智能助手'),
    ]
    llm_choice = forms.ChoiceField(
        choices=LLM_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select mb-3'}),
        label="Select AI Tutor (选择 AI 老师)"
    )

    problem_statement = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '请输入题目描述...'}),
        label="Programming Question (题目描述)",
        required=False
    )
    lecture_objective = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例如：学习如何使用 for 循环'}),
        label="Lecture Objective (课程目标)",
        required=False
    )
    student_code = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 8, 'placeholder': '粘贴代码...'}),
        label="Student Python Code (学生代码)",
        required=True
    )