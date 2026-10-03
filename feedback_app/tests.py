import csv
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .ai_response import (
    detect_solution_leakage,
    parse_ai_feedback,
    parse_ai_feedback_with_metadata,
)
from .analytics import (
    _attempt_score,
    build_class_analytics,
    build_skill_mastery,
    build_skill_timeline,
    build_student_profile,
)
from .feedback_schema import (
    ERROR_CATEGORIES,
    FEEDBACK_JSON_SCHEMA,
    PECI_ERROR_CODES,
    REQUIRED_FIELDS,
    canonicalize_error_category,
)
from .forms import QuestionAdminForm
from .views import _generate_feedback_record
from .code_runner import run_python_code
from .evaluation_dataset import (
    DEFAULT_REFACTORY_DATA_DIR,
    HAND_CRAFTED_BOUNDARY_RECORDS,
    REFACTORY_SOURCE_METADATA,
    SAMPLE_ORIGIN_HAND_CRAFTED,
    SAMPLE_ORIGIN_REFACTORY,
    SELECTED_REFACTORY_RECORDS,
    build_evaluation_samples,
    summarise_evaluation_samples,
    validate_evaluation_samples,
)
from .evaluation_analysis import export_day12_artifacts, import_manual_review_scores
from .evaluation_runner import _is_retryable_llm_error, run_evaluation_dataset
from .llm_client import estimate_llm_cost, get_llm_model_name
from .models import CodeFeedbackRecord, EvaluationResult, EvaluationRun, Question
from .peci_ax_evaluation import build_peci_ground_truth_prompt
from .output_comparison import (
    COMPARISON_MODE_NORMALIZED,
    COMPARISON_MODE_STRICT,
    compare_outputs,
    normalize_output,
)
from .prompt_builder import (
    PROMPT_STRICT_SCAFFOLDED,
    build_feedback_prompt,
    build_topic_classification_prompt,
)
from .taxonomy import (
    ERROR_TAXONOMY,
    PECI_ERROR_TAXONOMY,
    TOPIC_TAXONOMY,
    canonicalize_topic_reference,
    parse_topic_tags,
    serialize_topic_tags,
    topic_labels,
)


class CodeRunnerTests(SimpleTestCase):
    def test_successful_program(self):
        result = run_python_code("print('hello')\n")

        self.assertEqual(result["execution_status"], "success")
        self.assertEqual(result["stdout"], "hello\n")
        self.assertEqual(result["return_code"], 0)
        self.assertFalse(result["timed_out"])
        self.assertIsInstance(result["execution_time_ms"], int)

    def test_syntax_error_is_classified(self):
        result = run_python_code("for i in range(3)\n    print(i)\n")

        self.assertEqual(result["execution_status"], "syntax_error")
        self.assertIn("SyntaxError", result["stderr"])

    def test_indentation_error_is_classified(self):
        result = run_python_code("def f():\nprint(1)\n")

        self.assertEqual(result["execution_status"], "indentation_error")
        self.assertIn("IndentationError", result["stderr"])

    def test_name_error_is_classified(self):
        result = run_python_code("total = 10\nprint(totall)\n")

        self.assertEqual(result["execution_status"], "name_error")
        self.assertIn("NameError", result["stderr"])

    def test_unbound_local_error_is_classified_as_name_error(self):
        result = run_python_code("def f():\n    print(x)\n    x = 1\nf()\n")

        self.assertEqual(result["execution_status"], "name_error")
        self.assertIn("UnboundLocalError", result["stderr"])

    def test_type_error_is_classified(self):
        result = run_python_code("age = 18\nprint('Age: ' + age)\n")

        self.assertEqual(result["execution_status"], "type_error")
        self.assertIn("TypeError", result["stderr"])

    def test_single_input_program(self):
        result = run_python_code("name = input()\nprint('Hello', name)\n", sample_input="Lu\n")

        self.assertEqual(result["execution_status"], "success")
        self.assertEqual(result["stdout"], "Hello Lu\n")

    def test_multiple_input_program_uses_newline_separated_stdin(self):
        code = "a = int(input())\nb = int(input())\nprint(a + b)\n"

        result = run_python_code(code, sample_input="2\n3\n")

        self.assertEqual(result["execution_status"], "success")
        self.assertEqual(result["stdout"], "5\n")

    def test_missing_input_is_runtime_evidence(self):
        code = "first = input()\nsecond = input()\nprint(first, second)\n"

        result = run_python_code(code, sample_input="only-one-line\n")

        self.assertEqual(result["execution_status"], "eof_error")
        self.assertIn("EOFError", result["stderr"])

    def test_timeout_is_captured(self):
        result = run_python_code("while True:\n    pass\n", timeout=1)

        self.assertEqual(result["execution_status"], "timeout")
        self.assertTrue(result["timed_out"])
        self.assertIn("timed out", result["stderr"].lower())

    def test_missing_import_is_classified(self):
        result = run_python_code("import imaginary_fyp_package\n")

        self.assertEqual(result["execution_status"], "module_not_found")
        self.assertIn("ModuleNotFoundError", result["stderr"])

    def test_function_question_can_use_test_harness(self):
        result = run_python_code(
            "def square(n):\n    return n * n\n",
            test_harness="print(square(5))\n",
        )

        self.assertEqual(result["execution_status"], "success")
        self.assertEqual(result["stdout"], "25\n")

    def test_multi_function_question_can_use_test_harness(self):
        student_code = """
def area(width, height):
    return width * height

def perimeter(width, height):
    return 2 * (width + height)
"""
        test_harness = "print(area(3, 4))\nprint(perimeter(3, 4))\n"

        result = run_python_code(student_code, test_harness=test_harness)

        self.assertEqual(result["execution_status"], "success")
        self.assertEqual(result["stdout"], "12\n14\n")


class OutputComparisonTests(SimpleTestCase):
    def test_normalize_output_trims_spacing_case_and_blank_lines(self):
        self.assertEqual(normalize_output("\n Hello   Lu \n\n"), "hello lu")

    def test_exact_match(self):
        self.assertEqual(compare_outputs("Hello Lu\n", "Hello Lu\n", "success"), "exact_match")

    def test_trailing_space_can_be_normalized(self):
        result = compare_outputs("Hello Lu  \n", "Hello Lu\n", "success")

        self.assertEqual(result, "normalized_match")

    def test_case_difference_can_be_normalized(self):
        result = compare_outputs("hello lu\n", "Hello Lu\n", "success")

        self.assertEqual(result, "normalized_match")

    def test_extra_blank_lines_can_be_normalized(self):
        result = compare_outputs("Hello Lu\n\n", "Hello Lu\n", "success")

        self.assertEqual(result, "normalized_match")

    def test_strict_mode_rejects_format_differences(self):
        result = compare_outputs(
            "hello lu\n",
            "Hello Lu\n",
            "success",
            mode=COMPARISON_MODE_STRICT,
        )

        self.assertEqual(result, "mismatch")

    def test_normalized_mode_accepts_format_differences(self):
        result = compare_outputs(
            "hello   lu\n",
            "Hello Lu\n",
            "success",
            mode=COMPARISON_MODE_NORMALIZED,
        )

        self.assertEqual(result, "normalized_match")

    def test_mismatch(self):
        self.assertEqual(compare_outputs("45\n", "55\n", "success"), "mismatch")

    def test_execution_error_short_circuits_comparison(self):
        self.assertEqual(compare_outputs("", "55\n", "syntax_error"), "execution_error")


class HumanDefinedTaxonomyTests(SimpleTestCase):
    def test_topic_taxonomy_is_fixed_to_eight_introductory_areas(self):
        self.assertEqual(len(TOPIC_TAXONOMY), 8)
        self.assertEqual(
            list(TOPIC_TAXONOMY),
            [
                "program_structure",
                "variables_assignment",
                "expressions_operators",
                "conditionals_boolean",
                "iteration_range",
                "functions_returns",
                "strings_io",
                "collections_indexing",
            ],
        )

    def test_legacy_free_form_tags_are_mapped_to_fixed_topics(self):
        self.assertEqual(
            parse_topic_tags("loops,range,off-by-one,variables"),
            ["variables_assignment", "iteration_range"],
        )
        self.assertEqual(
            serialize_topic_tags(["functions", "return", "scope"]),
            "functions_returns",
        )
        self.assertEqual(
            topic_labels("functions_returns"),
            ["Functions and Return Values"],
        )

    def test_schema_categories_come_from_defined_error_taxonomy(self):
        self.assertEqual(ERROR_CATEGORIES, list(ERROR_TAXONOMY))
        self.assertEqual(PECI_ERROR_CODES, list(PECI_ERROR_TAXONOMY))
        self.assertEqual(len(PECI_ERROR_CODES), 24)
        self.assertIn("assignment", PECI_ERROR_TAXONOMY["P"]["definition"].lower())

    def test_concept_reference_is_normalised_to_the_fixed_topic_set(self):
        self.assertEqual(
            canonicalize_topic_reference("range boundary")[0],
            "Iteration and Range",
        )
        self.assertEqual(
            canonicalize_topic_reference("range() function boundaries")[0],
            "Iteration and Range",
        )
        self.assertEqual(
            canonicalize_topic_reference("List indexing")[0],
            "Collections and Indexing",
        )
        self.assertEqual(canonicalize_topic_reference("invented topic")[0], "Unknown")

    def test_feedback_prompt_contains_definitions_topics_and_priority_rules(self):
        prompt = build_feedback_prompt(
            problem_statement="Print the sum from 1 to n.",
            lecture_objective="Use a loop and accumulator.",
            student_code="print(sum(range(1, n)))",
            topic_tags="variables_assignment,iteration_range",
            execution_result={"execution_status": "success", "stdout": "10\n"},
            expected_output="15\n",
            output_comparison_status="mismatch",
        )

        self.assertIn("PECI Table 1 Error Taxonomy", prompt)
        self.assertIn("S - Missing colon, comma or operator", prompt)
        self.assertIn("Never invent, merge, or rename", prompt)
        self.assertIn("Variables and Assignment, Iteration and Range", prompt)
        self.assertIn("one passing sample is not proof", prompt)
        self.assertIn("misconception field", prompt)
        self.assertIn('Escape every double quote inside text as \\"', prompt)
        self.assertIn("encode line breaks as \\n", prompt)
        self.assertIn("misconception", REQUIRED_FIELDS)
        self.assertEqual(FEEDBACK_JSON_SCHEMA["properties"]["misconception"]["type"], "string")

    def test_question_topic_prompt_forbids_new_topics(self):
        prompt = build_topic_classification_prompt(
            "Read an integer and print whether it is even or odd."
        )

        self.assertIn("do not create a new topic", prompt)
        self.assertIn("conditionals_boolean", prompt)
        self.assertIn('{"topic_tags": ["topic_id"]}', prompt)


class QuestionTopicAdminFormTests(TestCase):
    def _form_data(self, topic_tags):
        return {
            "title": "Check a number",
            "problem_statement": "Read an integer and print whether it is even.",
            "lecture_objective": "Use modulo and a conditional.",
            "sample_input": "4\n",
            "expected_output": "Even\n",
            "test_harness": "",
            "comparison_mode": COMPARISON_MODE_NORMALIZED,
            "difficulty": "Beginner",
            "topic_tags": topic_tags,
            "default_llm_provider": "deepseek",
            "is_active": True,
        }

    def test_admin_topic_field_is_fixed_multiple_choice(self):
        form = QuestionAdminForm(
            data=self._form_data(["expressions_operators", "conditionals_boolean"])
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["topic_tags"],
            "expressions_operators,conditionals_boolean",
        )

    def test_admin_topic_field_rejects_free_text(self):
        form = QuestionAdminForm(data=self._form_data(["invented_topic"]))

        self.assertFalse(form.is_valid())
        self.assertIn("topic_tags", form.errors)


class TagQuestionTopicsCommandTests(TestCase):
    def setUp(self):
        self.untagged = Question.objects.create(
            title="Untagged question",
            problem_statement="Read n and print whether n is even.",
            lecture_objective="Use modulo and a conditional.",
        )
        self.tagged = Question.objects.create(
            title="Already tagged",
            problem_statement="Print a variable.",
            topic_tags="variables_assignment",
        )

    @patch("feedback_app.management.commands.tag_question_topics.call_llm_with_metadata")
    def test_dry_run_validates_but_does_not_save(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": '{"topic_tags": ["expressions_operators", "conditionals_boolean"]}'
        }
        stdout = io.StringIO()

        call_command(
            "tag_question_topics",
            provider="deepseek",
            dry_run=True,
            stdout=stdout,
        )

        self.untagged.refresh_from_db()
        self.assertEqual(self.untagged.topic_tags, "")
        self.assertEqual(mock_call_llm.call_count, 1)
        self.assertIn("no database changes were made", stdout.getvalue())

    @patch("feedback_app.management.commands.tag_question_topics.call_llm_with_metadata")
    def test_valid_fixed_topics_are_saved(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": "```json\n{\"topic_tags\": [\"conditionals_boolean\"]}\n```"
        }

        call_command("tag_question_topics", provider="kimi", verbosity=0)

        self.untagged.refresh_from_db()
        self.tagged.refresh_from_db()
        self.assertEqual(self.untagged.topic_tags, "conditionals_boolean")
        self.assertEqual(self.tagged.topic_tags, "variables_assignment")
        self.assertEqual(mock_call_llm.call_count, 1)

    @patch("feedback_app.management.commands.tag_question_topics.call_llm_with_metadata")
    def test_unknown_topic_is_rejected_without_saving(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": '{"topic_tags": ["conditionals_boolean", "invented_topic"]}'
        }

        with self.assertRaisesMessage(CommandError, "1 failure"):
            call_command("tag_question_topics", verbosity=0)

        self.untagged.refresh_from_db()
        self.assertEqual(self.untagged.topic_tags, "")


class LlmCostTests(SimpleTestCase):
    def test_model_names_can_be_overridden_from_environment(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_MODEL_NAME": "deepseek-test-model",
                "KIMI_MODEL_NAME": "kimi-test-model",
            },
        ):
            self.assertEqual(get_llm_model_name("deepseek"), "deepseek-test-model")
            self.assertEqual(get_llm_model_name("kimi"), "kimi-test-model")

    def test_cost_is_estimated_when_token_rates_are_configured(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_INPUT_COST_PER_1M": "0.10",
                "DEEPSEEK_OUTPUT_COST_PER_1M": "0.30",
            },
        ):
            cost = estimate_llm_cost(
                "deepseek",
                {
                    "prompt_tokens": 1000,
                    "completion_tokens": 2000,
                    "total_tokens": 3000,
                },
            )

        self.assertEqual(str(cost), "0.000700")

    def test_cost_is_none_when_token_rates_are_missing(self):
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_INPUT_COST_PER_1M": "",
                "DEEPSEEK_OUTPUT_COST_PER_1M": "",
            },
        ):
            cost = estimate_llm_cost(
                "deepseek",
                {
                    "prompt_tokens": 1000,
                    "completion_tokens": 2000,
                },
            )

        self.assertIsNone(cost)


class ErrorCategoryTaxonomyTests(SimpleTestCase):
    def test_common_snake_case_labels_map_to_shared_taxonomy(self):
        expected = {
            "off_by_one": "Loop Boundary Error",
            "no_error": "No Error",
            "string_formatting": "Output Format Error",
            "operator_misuse": "Condition Error",
            "Syntax Error / Indentation Error": "Indentation Error",
        }

        for raw_value, canonical_value in expected.items():
            with self.subTest(raw_value=raw_value):
                result, _ = canonicalize_error_category(raw_value)
                self.assertEqual(result, canonical_value)


class EvaluationDatasetTests(SimpleTestCase):
    def test_refactory_manifest_meets_day10_size_target(self):
        self.assertEqual(len(SELECTED_REFACTORY_RECORDS), 55)
        self.assertEqual(
            len({record.sample_id for record in SELECTED_REFACTORY_RECORDS}),
            len(SELECTED_REFACTORY_RECORDS),
        )

        question_counts = {}
        for record in SELECTED_REFACTORY_RECORDS:
            question_counts[record.question_id] = question_counts.get(record.question_id, 0) + 1
            self.assertIn(record.ground_truth_category, ERROR_CATEGORIES)
            self.assertTrue(record.relative_code_path.startswith("data/question_"))
            self.assertIn("/code/wrong/wrong_", record.relative_code_path)

        self.assertEqual(question_counts, {1: 11, 2: 11, 3: 11, 4: 11, 5: 11})

    def test_dataset_has_schema_valid_ground_truth_and_source_provenance(self):
        if not DEFAULT_REFACTORY_DATA_DIR.exists():
            self.skipTest("Refactory data.zip has not been extracted in this environment.")

        samples = build_evaluation_samples(DEFAULT_REFACTORY_DATA_DIR)
        errors = validate_evaluation_samples(samples)
        summary = summarise_evaluation_samples(samples)

        self.assertEqual(errors, [])
        expected_total = len(SELECTED_REFACTORY_RECORDS) + len(
            HAND_CRAFTED_BOUNDARY_RECORDS
        )

        self.assertEqual(summary["total"], expected_total)
        self.assertEqual(summary["real_refactory_records"], 55)
        self.assertEqual(
            summary["hand_crafted_boundary_cases"],
            len(HAND_CRAFTED_BOUNDARY_RECORDS),
        )
        self.assertGreaterEqual(summary["requires_input_count"], 1)
        self.assertGreaterEqual(summary["expected_timeout_count"], 1)
        self.assertIn("Syntax Error", summary["category_counts"])
        self.assertIn("Indentation Error", summary["category_counts"])
        self.assertIn("Timeout", summary["category_counts"])
        self.assertIn("Input Error", summary["category_counts"])

        for sample in samples:
            self.assertIn(
                sample["sample_origin"],
                {SAMPLE_ORIGIN_REFACTORY, SAMPLE_ORIGIN_HAND_CRAFTED},
            )
            self.assertTrue(sample["source_citations"])
            self.assertTrue(sample["source_basis"])
            self.assertTrue(sample["source_record_path"].endswith(".py"))
            self.assertTrue(sample["source_test_input_path"].endswith(".txt"))
            self.assertTrue(sample["source_test_output_path"].endswith(".txt"))
            self.assertIn(sample["ground_truth_category"], ERROR_CATEGORIES)

            if sample["sample_origin"] == SAMPLE_ORIGIN_REFACTORY:
                self.assertIn("/code/wrong/wrong_", sample["source_record_path"])
            else:
                self.assertTrue(sample["source_record_path"].startswith("hand_crafted/"))
                self.assertIn("not a real student submission", sample["source_basis"])


class EvaluationRunnerTests(TestCase):
    def test_legacy_dataset_real_run_is_blocked_under_peci_v3(self):
        with self.assertRaisesMessage(CommandError, "legacy v1/v2 ground-truth labels"):
            call_command("run_evaluation_dataset", run_llm=True, limit=1)

    def test_quota_errors_are_not_retried(self):
        self.assertFalse(
            _is_retryable_llm_error(
                "HTTP 429 from LLM provider: exceeded_current_quota_error, please recharge"
            )
        )
        self.assertTrue(_is_retryable_llm_error("HTTP 429 from LLM provider: rate limit"))

    def test_dry_run_persists_results_and_exports_summary(self):
        if not DEFAULT_REFACTORY_DATA_DIR.exists():
            self.skipTest("Refactory data.zip has not been extracted in this environment.")

        with tempfile.TemporaryDirectory() as temp_dir:
            samples = build_evaluation_samples(
                DEFAULT_REFACTORY_DATA_DIR,
                records=SELECTED_REFACTORY_RECORDS[:2],
            )
            dataset_path = Path(temp_dir) / "evaluation_samples.json"
            dataset_path.write_text(
                json.dumps(
                    {
                        "metadata": REFACTORY_SOURCE_METADATA,
                        "samples": samples,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = run_evaluation_dataset(
                dataset_path=dataset_path,
                providers=["deepseek"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                run_llm=False,
                output_dir=temp_dir,
                name="Unit dry run",
            )

        self.assertEqual(EvaluationRun.objects.count(), 1)
        self.assertEqual(EvaluationResult.objects.count(), 2)
        self.assertEqual(result["summary"]["total_results"], 2)
        self.assertEqual(result["summary"]["category_accuracy"], 1.0)

        first_result = EvaluationResult.objects.order_by("sample_id").first()
        self.assertEqual(first_result.provider, "deepseek")
        self.assertEqual(first_result.prompt_version, PROMPT_STRICT_SCAFFOLDED)
        self.assertTrue(first_result.json_compliance)
        self.assertFalse(first_result.solution_leakage_flag)
        self.assertTrue(first_result.source_record_path.endswith(".py"))
        self.assertIn("Test Harness:", first_result.prompt_text)

    def test_sample_offset_runs_a_later_dataset_window(self):
        if not DEFAULT_REFACTORY_DATA_DIR.exists():
            self.skipTest("Refactory data.zip has not been extracted in this environment.")

        with tempfile.TemporaryDirectory() as temp_dir:
            samples = build_evaluation_samples(
                DEFAULT_REFACTORY_DATA_DIR,
                records=SELECTED_REFACTORY_RECORDS[:4],
            )
            dataset_path = Path(temp_dir) / "evaluation_samples.json"
            dataset_path.write_text(
                json.dumps(
                    {
                        "metadata": REFACTORY_SOURCE_METADATA,
                        "samples": samples,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = run_evaluation_dataset(
                dataset_path=dataset_path,
                providers=["deepseek"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                offset=2,
                limit=1,
                run_llm=False,
                output_dir=temp_dir,
                name="Offset dry run",
            )

        self.assertEqual(result["summary"]["total_results"], 1)
        stored_result = EvaluationResult.objects.get()
        self.assertEqual(stored_result.sample_id, samples[2]["sample_id"])
        self.assertIn("offset=2", result["run"].notes)

    @patch("feedback_app.evaluation_runner.call_llm_with_metadata")
    def test_llm_call_failure_is_saved_as_evaluation_result(self, mock_call_llm):
        if not DEFAULT_REFACTORY_DATA_DIR.exists():
            self.skipTest("Refactory data.zip has not been extracted in this environment.")

        mock_call_llm.side_effect = RuntimeError("temporary provider failure")

        with tempfile.TemporaryDirectory() as temp_dir:
            samples = build_evaluation_samples(
                DEFAULT_REFACTORY_DATA_DIR,
                records=SELECTED_REFACTORY_RECORDS[:1],
            )
            dataset_path = Path(temp_dir) / "evaluation_samples.json"
            dataset_path.write_text(
                json.dumps(
                    {
                        "metadata": REFACTORY_SOURCE_METADATA,
                        "samples": samples,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = run_evaluation_dataset(
                dataset_path=dataset_path,
                providers=["deepseek"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                run_llm=True,
                output_dir=temp_dir,
                name="Provider failure test",
            )

        stored_result = EvaluationResult.objects.get()
        self.assertEqual(result["summary"]["total_results"], 1)
        self.assertFalse(stored_result.json_compliance)
        self.assertIn("temporary provider failure", stored_result.ai_error)


class PeciAxEvaluationTests(TestCase):
    def _write_dataset(self, temp_dir):
        samples = []
        for index in range(1, 56):
            samples.append(
                {
                    "sample_id": f"refactory-peci-test-{index:03d}",
                    "sample_origin": "real_student_submission_refactory",
                    "source_dataset": "Refactory",
                    "source_record_path": f"data/wrong_{index:03d}.py",
                    "source_test_input_path": "data/input.txt",
                    "source_test_output_path": "data/output.txt",
                    "problem_statement": "Print the value one.",
                    "lecture_objective": "Use a valid Python identifier.",
                    "support_code": "",
                    "student_code": "print(0)\n",
                    "sample_input": "",
                    "expected_output": "1\n",
                    "actual_output": "0\n",
                    "actual_stderr": "",
                    "test_harness": "",
                    "comparison_mode": "normalized",
                    "output_comparison_status": "mismatch",
                    "ground_truth_category": "Logic Error",
                    "expected_feedback_focus": "Inspect the value printed by the program.",
                    "expected_execution_status": "success",
                }
            )
        path = Path(temp_dir) / "evaluation_samples.json"
        path.write_text(
            json.dumps(
                {"metadata": {"dataset_name": "Refactory"}, "samples": samples},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path, samples

    def _write_confirmed_csv(self, temp_dir, samples, *, complete=True):
        path = Path(temp_dir) / "peci_ax_ground_truth_confirmed.csv"
        rows = samples if complete else samples[:-1]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "sample_id",
                    "confirmed_outcome",
                    "confirmed_peci_code",
                ],
            )
            writer.writeheader()
            for sample in rows:
                writer.writerow(
                    {
                        "sample_id": sample["sample_id"],
                        "confirmed_outcome": "peci_error",
                        "confirmed_peci_code": "A",
                    }
                )
        return path

    def _peci_feedback_response(self):
        return {
            "content": json.dumps(
                {
                    "classification_outcome": "peci_error",
                    "peci_error_code": "A",
                    "feedback_level": "Level 2",
                    "concept_reference": "Program Structure",
                    "misconception": "The student uses an invalid identifier.",
                    "feedback": "Inspect the identifier used in the program.",
                    "does_reveal_solution": False,
                    "uses_runtime_evidence": True,
                    "suggested_next_step": "Compare the identifier with Python naming rules.",
                    "confidence": "high",
                }
            ),
            "model_name": "mock-model",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "estimated_cost": None,
        }

    def test_annotation_prompt_uses_peci_and_withholds_legacy_label(self):
        sample = {
            "problem_statement": "Print one.",
            "student_code": "print(0)",
            "actual_output": "0\n",
            "expected_output": "1\n",
            "actual_stderr": "",
            "output_comparison_status": "mismatch",
            "expected_execution_status": "success",
            "ground_truth_category": "Logic Error",
        }

        prompt = build_peci_ground_truth_prompt(sample)

        self.assertIn("PECI A-X error inventory", prompt)
        self.assertIn("- A - Invalid names", prompt)
        self.assertIn('"actual_output": "0\\n"', prompt)
        self.assertIn('"output_comparison_status": "mismatch"', prompt)
        self.assertIn('Escape every double quote inside text as \\"', prompt)
        self.assertNotIn("Logic Error", prompt)

    @patch("feedback_app.peci_ax_evaluation.call_llm_with_metadata")
    def test_proposal_dry_run_prints_55_rows_without_writing(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": json.dumps(
                {
                    "classification_outcome": "peci_error",
                    "peci_error_code": "A",
                    "rationale": "The identifier is invalid in this context.",
                }
            )
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path, _samples = self._write_dataset(temp_dir)
            output_path = Path(temp_dir) / "proposals.csv"
            stdout = io.StringIO()

            call_command(
                "propose_peci_ground_truth",
                dataset_path=str(dataset_path),
                output_path=str(output_path),
                dry_run=True,
                retry_delay=0,
                stdout=stdout,
            )

            self.assertFalse(output_path.exists())
            self.assertIn("[55/55] refactory-peci-test-055", stdout.getvalue())
            self.assertIn("no proposal CSV", stdout.getvalue())
        self.assertEqual(mock_call_llm.call_count, 55)
        self.assertEqual(EvaluationRun.objects.count(), 0)

    @patch("feedback_app.peci_ax_evaluation.call_llm_with_metadata")
    def test_proposal_csv_keeps_confirmation_columns_blank(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": json.dumps(
                {
                    "classification_outcome": "peci_error",
                    "peci_error_code": "A - Invalid names",
                    "rationale": "The identifier is invalid in this context.",
                }
            )
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path, _samples = self._write_dataset(temp_dir)
            output_path = Path(temp_dir) / "proposals.csv"

            call_command(
                "propose_peci_ground_truth",
                dataset_path=str(dataset_path),
                output_path=str(output_path),
                retry_delay=0,
                stdout=io.StringIO(),
            )

            with output_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 55)
            self.assertEqual(rows[0]["proposed_peci_code"], "A")
            self.assertEqual(rows[0]["confirmed_outcome"], "")
            self.assertEqual(rows[0]["confirmed_peci_code"], "")

    @patch("feedback_app.evaluation_runner.call_llm_with_metadata")
    def test_peci_evaluation_requires_complete_confirmed_csv(self, mock_call_llm):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path, samples = self._write_dataset(temp_dir)
            confirmed_path = self._write_confirmed_csv(
                temp_dir,
                samples,
                complete=False,
            )

            with self.assertRaisesMessage(CommandError, "does not exactly match"):
                call_command(
                    "run_peci_ax_evaluation",
                    confirmed_csv=str(confirmed_path),
                    dataset_path=str(dataset_path),
                    output_dir=temp_dir,
                    run_llm=True,
                    retry_delay=0,
                    stdout=io.StringIO(),
                )

        mock_call_llm.assert_not_called()
        self.assertEqual(EvaluationRun.objects.count(), 0)

    @patch("feedback_app.peci_ax_evaluation._build_runtime_evidence")
    @patch("feedback_app.evaluation_runner.call_llm_with_metadata")
    def test_peci_evaluation_writes_independent_reports(
        self,
        mock_call_llm,
        mock_runtime,
    ):
        invalid_kimi_response_sent = False

        def mock_provider_response(prompt, provider):
            nonlocal invalid_kimi_response_sent
            is_repair_retry = "JSON REPAIR RETRY" in prompt
            if provider == "kimi" and not invalid_kimi_response_sent and not is_repair_retry:
                invalid_kimi_response_sent = True
                return {
                    "content": (
                        '{"classification_outcome":"peci_error",'
                        '"feedback":"Check "return i + 1" before continuing."}'
                    ),
                    "model_name": "mock-kimi",
                    "usage": {
                        "prompt_tokens": 8,
                        "completion_tokens": 4,
                        "total_tokens": 12,
                    },
                    "estimated_cost": None,
                }
            return self._peci_feedback_response()

        mock_call_llm.side_effect = mock_provider_response
        mock_runtime.return_value = (
            {
                "execution_status": "success",
                "stdout": "0\n",
                "stderr": "",
            },
            "mismatch",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path, samples = self._write_dataset(temp_dir)
            confirmed_path = self._write_confirmed_csv(temp_dir, samples)

            call_command(
                "run_peci_ax_evaluation",
                confirmed_csv=str(confirmed_path),
                dataset_path=str(dataset_path),
                output_dir=temp_dir,
                run_llm=True,
                retry_delay=0,
                stdout=io.StringIO(),
            )

            summary_path = Path(temp_dir) / "peci_ax_evaluation_summary.json"
            markdown_path = Path(temp_dir) / "peci_ax_evaluation_summary.md"
            matrix_path = Path(temp_dir) / "peci_ax_evaluation_confusion_matrix.csv"
            self.assertTrue(summary_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(matrix_path.exists())

            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            summary = payload["summary"]
            self.assertEqual(summary["sample_count"], 55)
            self.assertEqual(summary["total_results"], 110)
            self.assertEqual(summary["overall_accuracy"], 1.0)
            self.assertEqual(summary["per_provider"]["deepseek"]["accuracy"], 1.0)
            self.assertEqual(summary["per_provider"]["kimi"]["accuracy"], 1.0)
            self.assertEqual(summary["ai_error_count"], 0)
            self.assertEqual(summary["json_repair_attempt_count"], 1)
            self.assertEqual(summary["json_repair_success_count"], 1)
            self.assertEqual(
                summary["per_provider"]["deepseek"]["json_repair_attempt_count"],
                0,
            )
            self.assertEqual(
                summary["per_provider"]["kimi"]["json_repair_attempt_count"],
                1,
            )
            self.assertEqual(
                summary["per_provider"]["kimi"]["json_repair_success_count"],
                1,
            )
            self.assertIn(
                "researcher-confirmed AI-assisted A-X annotation",
                markdown_path.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Day 12 legacy-taxonomy",
                markdown_path.read_text(encoding="utf-8"),
            )

        self.assertEqual(mock_call_llm.call_count, 111)
        self.assertEqual(EvaluationRun.objects.count(), 1)
        self.assertEqual(EvaluationResult.objects.count(), 110)
        repaired_result = EvaluationResult.objects.get(
            provider="kimi",
            sample_id="refactory-peci-test-001",
        )
        self.assertTrue(repaired_result.json_compliance)
        self.assertIn("JSON REPAIR RETRY", repaired_result.prompt_text)
        self.assertIn("INITIAL INVALID JSON RESPONSE", repaired_result.raw_ai_response)
        self.assertIn("JSON repair retry succeeded", repaired_result.schema_validation_notes)


class EvaluationAnalysisTests(TestCase):
    def _create_small_dry_run(self, temp_dir):
        if not DEFAULT_REFACTORY_DATA_DIR.exists():
            self.skipTest("Refactory data.zip has not been extracted in this environment.")

        samples = build_evaluation_samples(
            DEFAULT_REFACTORY_DATA_DIR,
            records=SELECTED_REFACTORY_RECORDS[:2],
        )
        dataset_path = Path(temp_dir) / "evaluation_samples.json"
        dataset_path.write_text(
            json.dumps(
                {
                    "metadata": REFACTORY_SOURCE_METADATA,
                    "samples": samples,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result = run_evaluation_dataset(
            dataset_path=dataset_path,
            providers=["deepseek"],
            prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
            run_llm=False,
            output_dir=temp_dir,
            name="Analysis dry run",
        )
        return result["run"]

    def test_day12_artifacts_include_charts_and_review_template(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluation_run = self._create_small_dry_run(temp_dir)
            summary = export_day12_artifacts(
                evaluation_run,
                output_dir=temp_dir,
                review_limit=2,
            )

            artifact_paths = summary["artifact_paths"]
            for key in [
                "summary_json",
                "summary_markdown",
                "manual_review_csv",
                "accuracy_chart_svg",
                "quality_rates_svg",
                "ground_truth_distribution_svg",
                "confusion_matrix_svg",
            ]:
                self.assertTrue(Path(artifact_paths[key]).exists(), key)

            self.assertTrue(summary["dry_run_caveat"])
            self.assertEqual(summary["automatic_metrics"]["total_results"], 2)

            evaluation_run.refresh_from_db()
            self.assertIn("day12_analysis", evaluation_run.summary)

    def test_manual_review_scores_can_be_imported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluation_run = self._create_small_dry_run(temp_dir)
            summary = export_day12_artifacts(
                evaluation_run,
                output_dir=temp_dir,
                review_limit=1,
            )
            csv_path = Path(summary["artifact_paths"]["manual_review_csv"])

            with csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fieldnames = rows[0].keys()

            rows[0]["helpfulness_score"] = "5"
            rows[0]["lecture_alignment_score"] = "4"
            rows[0]["actionability_score"] = "5"
            rows[0]["human_solution_leakage"] = "false"
            rows[0]["human_review_notes"] = "Actionable hint without revealing code."

            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            updated = import_manual_review_scores(csv_path)

            reviewed_result = EvaluationResult.objects.get(pk=rows[0]["database_id"])
            self.assertEqual(updated, 1)
            self.assertEqual(reviewed_result.helpfulness_score, 5)
            self.assertEqual(reviewed_result.lecture_alignment_score, 4)
            self.assertEqual(reviewed_result.actionability_score, 5)
            self.assertFalse(reviewed_result.human_solution_leakage)
            self.assertEqual(
                reviewed_result.human_review_notes,
                "Actionable hint without revealing code.",
            )
            self.assertIsNotNone(reviewed_result.reviewed_at)

    def test_aggregate_evaluation_runs_command_exports_combined_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_one = EvaluationRun.objects.create(
                name="Aggregate part one",
                dataset_size=1,
                providers=["deepseek"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                run_mode=EvaluationRun.RUN_MODE_LLM,
                completed_at=timezone.now(),
            )
            run_two = EvaluationRun.objects.create(
                name="Aggregate part two",
                dataset_size=1,
                providers=["deepseek"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                run_mode=EvaluationRun.RUN_MODE_LLM,
                completed_at=timezone.now(),
            )
            EvaluationResult.objects.create(
                evaluation_run=run_one,
                sample_id="sample_one",
                provider="deepseek",
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                ground_truth_category="Logic Error",
                predicted_category="Logic Error",
                category_match=True,
                json_compliance=True,
                schema_validation_status="valid_schema",
                solution_leakage_flag=False,
                uses_runtime_evidence=True,
            )
            EvaluationResult.objects.create(
                evaluation_run=run_two,
                sample_id="sample_two",
                provider="deepseek",
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                ground_truth_category="Type Error",
                predicted_category="Logic Error",
                category_match=False,
                json_compliance=True,
                schema_validation_status="valid_schema",
                solution_leakage_flag=False,
                uses_runtime_evidence=True,
            )

            output = io.StringIO()
            call_command(
                "aggregate_evaluation_runs",
                "--run-ids",
                f"{run_one.id},{run_two.id}",
                "--providers",
                "deepseek",
                "--output-dir",
                temp_dir,
                "--slug",
                "aggregate_test",
                stdout=output,
            )

            self.assertIn("Total results: 2", output.getvalue())
            for filename in [
                "aggregate_test_summary.json",
                "aggregate_test_summary.md",
                "aggregate_test_results.json",
                "aggregate_test_manual_review_template.csv",
                "aggregate_test_reference_review_suggestions.csv",
                "aggregate_test_accuracy_by_condition.svg",
                "aggregate_test_quality_rates.svg",
                "aggregate_test_ground_truth_distribution.svg",
                "aggregate_test_confusion_matrix.svg",
            ]:
                self.assertTrue(Path(temp_dir, filename).exists(), filename)

    def test_aggregate_evaluation_runs_can_dedupe_rerun_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            older_run = EvaluationRun.objects.create(
                name="Older aggregate part",
                dataset_size=1,
                providers=["kimi"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                run_mode=EvaluationRun.RUN_MODE_LLM,
                completed_at=timezone.now(),
            )
            newer_run = EvaluationRun.objects.create(
                name="Newer aggregate part",
                dataset_size=1,
                providers=["kimi"],
                prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
                run_mode=EvaluationRun.RUN_MODE_LLM,
                completed_at=timezone.now(),
            )
            EvaluationResult.objects.create(
                evaluation_run=older_run,
                sample_id="same_sample",
                provider="kimi",
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                ground_truth_category="Logic Error",
                predicted_category="",
                category_match=False,
                json_compliance=False,
                schema_validation_status="invalid_json",
                solution_leakage_flag=False,
                uses_runtime_evidence=False,
                ai_error="temporary error",
            )
            EvaluationResult.objects.create(
                evaluation_run=newer_run,
                sample_id="same_sample",
                provider="kimi",
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                ground_truth_category="Logic Error",
                predicted_category="Logic Error",
                category_match=True,
                json_compliance=True,
                schema_validation_status="valid_schema",
                solution_leakage_flag=False,
                uses_runtime_evidence=True,
            )

            output = io.StringIO()
            call_command(
                "aggregate_evaluation_runs",
                "--run-ids",
                f"{older_run.id},{newer_run.id}",
                "--dedupe-latest",
                "--output-dir",
                temp_dir,
                "--slug",
                "dedupe_test",
                stdout=output,
            )

            self.assertIn("Total results: 1", output.getvalue())
            payload = json.loads(Path(temp_dir, "dedupe_test_results.json").read_text())
            self.assertEqual(len(payload["results"]), 1)
            self.assertEqual(payload["results"][0]["evaluation_run_id"], newer_run.id)


class AiResponseParsingTests(SimpleTestCase):
    def test_fenced_json_is_not_solution_leakage_by_itself(self):
        raw_response = """```json
{
  "error_category": "off_by_one",
  "feedback_level": "hint",
  "concept_reference": "Iteration and Range",
  "feedback": "Check whether your loop includes the final value.",
  "does_reveal_solution": false,
  "uses_runtime_evidence": true,
  "suggested_next_step": "Print the values generated by range().",
  "confidence": "high"
}
```"""

        parsed, error = parse_ai_feedback(raw_response)

        self.assertIsNone(error)
        self.assertIsNotNone(parsed)
        self.assertFalse(detect_solution_leakage(raw_response, parsed))

    def test_json_object_can_be_extracted_from_surrounding_text(self):
        raw_response = """
Here is the requested feedback:
{
  "classification_outcome": "peci_error",
  "peci_error_code": "E",
  "feedback_level": "Level 2",
  "concept_reference": "Iteration and Range",
  "misconception": "The student may confuse the loop bound with the inclusive endpoint.",
  "feedback": "Your loop runs, but the total does not match the expected output.",
  "does_reveal_solution": false,
  "uses_runtime_evidence": true,
  "suggested_next_step": "Compare the actual total with the expected total.",
  "confidence": "high"
}
Please review it.
"""

        result = parse_ai_feedback_with_metadata(raw_response)

        self.assertEqual(result["schema_validation_status"], "valid_schema")
        self.assertEqual(result["feedback_json"]["error_category"], "Literal values instead of variables")
        self.assertIn("loop bound", result["feedback_json"]["misconception"])

    def test_missing_fields_are_repaired_for_display_and_statistics(self):
        raw_response = """
{
  "error_category": "off_by_one",
  "feedback": "Check whether your range includes the last required number."
}
"""

        result = parse_ai_feedback_with_metadata(raw_response)

        self.assertEqual(result["schema_validation_status"], "repaired_schema")
        self.assertIsNone(result["error"])
        self.assertEqual(result["feedback_json"]["error_category"], "Loop Boundary Error")
        self.assertEqual(result["feedback_json"]["feedback_level"], "Level 2")
        self.assertEqual(result["feedback_json"]["misconception"], "")
        self.assertIn("missing field", result["schema_validation_notes"])

    def test_misconception_is_limited_to_400_characters(self):
        result = parse_ai_feedback_with_metadata(
            json.dumps({"classification_outcome": "peci_error", "peci_error_code": "E", "misconception": "x" * 450})
        )

        self.assertEqual(len(result["feedback_json"]["misconception"]), 400)
        self.assertIn("misconception was trimmed", result["schema_validation_notes"])

    def test_correct_or_unknown_outcome_does_not_keep_misconception(self):
        for outcome in ("no_error", "unknown"):
            with self.subTest(outcome=outcome):
                result = parse_ai_feedback_with_metadata(
                    json.dumps({
                        "classification_outcome": outcome,
                        "misconception": "The student has a loop misconception.",
                    })
                )
                self.assertEqual(result["feedback_json"]["misconception"], "")
                self.assertIn("misconception cleared", result["schema_validation_notes"])

    def test_string_booleans_are_coerced(self):
        raw_response = """
{
  "error_category": "Input Error",
  "feedback_level": "Level 2",
  "concept_reference": "Strings, Input, and Output",
  "feedback": "The program asks for more input than the sample input provides.",
  "does_reveal_solution": "false",
  "uses_runtime_evidence": "true",
  "suggested_next_step": "Check how many input() calls your program reaches.",
  "confidence": "medium"
}
"""

        result = parse_ai_feedback_with_metadata(raw_response)

        self.assertEqual(result["schema_validation_status"], "repaired_schema")
        self.assertFalse(result["feedback_json"]["does_reveal_solution"])
        self.assertTrue(result["feedback_json"]["uses_runtime_evidence"])

    def test_invalid_json_is_reported_without_crashing(self):
        result = parse_ai_feedback_with_metadata("{bad json")

        self.assertEqual(result["feedback_json"], None)
        self.assertEqual(result["schema_validation_status"], "invalid_json")
        self.assertIn("not valid JSON", result["error"])

    def test_non_object_json_is_invalid_schema(self):
        result = parse_ai_feedback_with_metadata('["not", "an", "object"]')

        self.assertEqual(result["feedback_json"], None)
        self.assertEqual(result["schema_validation_status"], "invalid_schema")
        self.assertIn("object", result["error"])

    def test_semantic_solution_leakage_is_detected(self):
        raw_response = """
{
  "error_category": "Logic Error",
  "feedback_level": "Level 3",
  "concept_reference": "Iteration and Range",
  "feedback": "Here is the corrected code: print(sum(range(1, 11)))",
  "does_reveal_solution": false,
  "uses_runtime_evidence": true,
  "suggested_next_step": "Review the full solution.",
  "confidence": "high"
}
"""
        parsed, error = parse_ai_feedback(raw_response)

        self.assertIsNone(error)
        self.assertTrue(detect_solution_leakage(raw_response, parsed))


class FeedbackGenerationResilienceTests(TestCase):
    @patch("feedback_app.views.call_llm_with_metadata")
    def test_incomplete_llm_json_is_repaired_and_saved(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": '{"error_category": "off_by_one", "feedback": "Check the end value in range()."}',
            "model_name": "deepseek-chat",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "estimated_cost": None,
        }

        context = _generate_feedback_record(
            problem_statement="Print the sum of integers from 1 to 10.",
            lecture_objective="Use range boundaries and an accumulator.",
            student_code="print(sum(range(1, 10)))\n",
            expected_output="55\n",
        )
        record = context["record"]

        self.assertEqual(record.schema_validation_status, "repaired_schema")
        self.assertTrue(record.json_compliance)
        self.assertEqual(record.error_category, "Loop Boundary Error")
        self.assertIn("missing field", record.schema_validation_notes)
        self.assertEqual(record.llm_token_usage["total_tokens"], 15)
        mock_call_llm.assert_called_once()

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_invalid_llm_json_is_saved_as_readable_error(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": "{bad json",
            "model_name": "deepseek-chat",
            "usage": {},
            "estimated_cost": None,
        }

        context = _generate_feedback_record(
            problem_statement="Print hello.",
            lecture_objective="Use print().",
            student_code="print('hello')\n",
            expected_output="hello\n",
        )
        record = context["record"]

        self.assertEqual(record.schema_validation_status, "invalid_json")
        self.assertFalse(record.json_compliance)
        self.assertIn("not valid JSON", record.ai_error)
        self.assertEqual(context["ai_feedback_json"], None)
        self.assertEqual(mock_call_llm.call_count, 2)
        self.assertIn("JSON REPAIR RETRY", record.prompt_text)
        self.assertIn("INITIAL INVALID JSON RESPONSE", record.raw_ai_response)
        self.assertIn("JSON REPAIR RETRY RESPONSE", record.raw_ai_response)
        self.assertIn("JSON repair retry failed", record.schema_validation_notes)

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_invalid_llm_json_is_retried_once_and_repaired(self, mock_call_llm):
        mock_call_llm.side_effect = [
            {
                "content": (
                    '{"classification_outcome":"peci_error",'
                    '"feedback":"Check "return i + 1" before continuing."}'
                ),
                "model_name": "kimi-k2.5",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
                "estimated_cost": None,
            },
            {
                "content": json.dumps(
                    {
                        "classification_outcome": "peci_error",
                        "peci_error_code": "A",
                        "feedback_level": "Level 2",
                        "concept_reference": "Program Structure and Statements",
                        "misconception": "The student treats an invalid identifier as valid.",
                        "feedback": "Inspect the identifier before continuing.",
                        "does_reveal_solution": False,
                        "uses_runtime_evidence": True,
                        "suggested_next_step": "Compare it with Python naming rules.",
                        "confidence": "high",
                    }
                ),
                "model_name": "kimi-k2.5",
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20,
                },
                "estimated_cost": None,
            },
        ]

        context = _generate_feedback_record(
            problem_statement="Print hello.",
            lecture_objective="Use print().",
            student_code="print('hello')\n",
            expected_output="hello\n",
            llm_choice="kimi",
        )
        record = context["record"]

        self.assertEqual(mock_call_llm.call_count, 2)
        self.assertTrue(record.json_compliance)
        self.assertEqual(record.ai_error, "")
        self.assertEqual(record.classification_outcome, "peci_error")
        self.assertEqual(record.peci_error_code, "A")
        self.assertEqual(record.llm_token_usage["total_tokens"], 35)
        self.assertIn("JSON REPAIR RETRY", record.prompt_text)
        self.assertIn("INITIAL INVALID JSON RESPONSE", record.raw_ai_response)
        self.assertIn("JSON repair retry succeeded", record.schema_validation_notes)

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_llm_call_failure_is_saved_without_crashing(self, mock_call_llm):
        mock_call_llm.side_effect = ValueError("Missing API key for deepseek.")

        context = _generate_feedback_record(
            problem_statement="Print hello.",
            lecture_objective="Use print().",
            student_code="print('hello')\n",
            expected_output="hello\n",
        )
        record = context["record"]

        self.assertEqual(record.schema_validation_status, "llm_call_failed")
        self.assertFalse(record.json_compliance)
        self.assertIn("AI call failed", record.ai_error)
        self.assertIn("Missing API key", record.schema_validation_notes)


class LearningAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", with_history=True, verbosity=0)

    def test_student_profile_summarises_progress_and_patterns(self):
        User = get_user_model()
        student = User.objects.get(username="student1")

        profile = build_student_profile(student)

        self.assertEqual(profile["attempt_total"], 10)
        self.assertEqual(profile["question_total"], 2)
        self.assertEqual(profile["trend_label"], "Last +80 vs first")
        self.assertTrue(profile["sparkline"])
        self.assertIn("does not adjust for question difficulty", profile["trend_summary"])
        self.assertEqual(profile["solved_rate"], 20)
        self.assertTrue(profile["repeated_errors"])
        self.assertTrue(profile["recent_next_steps"])
        self.assertEqual(profile["skill_mastery"]["evidence_topic_count"], 3)

    def test_skill_mastery_uses_latest_attempt_per_question_and_fixed_topics(self):
        User = get_user_model()
        student = User.objects.get(username="student1")

        mastery = build_skill_mastery(student)
        topics = {topic["id"]: topic for topic in mastery["topics"]}

        self.assertEqual(len(topics), 8)
        self.assertEqual(topics["variables_assignment"]["score"], 100)
        self.assertEqual(topics["variables_assignment"]["question_count"], 2)
        self.assertEqual(topics["variables_assignment"]["attempt_count"], 10)
        self.assertEqual(topics["iteration_range"]["score"], 100)
        self.assertEqual(topics["strings_io"]["score"], 100)
        self.assertFalse(topics["functions_returns"]["has_evidence"])
        self.assertEqual(topics["functions_returns"]["score"], 0)
        self.assertEqual(len(mastery["grid_polygons"]), 4)

    def test_skill_timeline_exposes_traceable_attempt_evidence(self):
        User = get_user_model()
        student = User.objects.get(username="student1")

        skill = build_skill_timeline(student, "iteration_range")

        self.assertEqual(skill["topic"]["label"], "Iteration and Range")
        self.assertEqual(skill["total_attempts"], 5)
        self.assertEqual(skill["question_count"], 1)
        self.assertEqual(skill["timeline"][0]["question_attempt"], 1)
        self.assertEqual(skill["timeline"][0]["score"], 20)
        self.assertFalse(skill["timeline"][0]["solved"])
        self.assertEqual(skill["timeline"][-1]["score"], 100)
        self.assertTrue(skill["timeline"][-1]["solved"])
        self.assertTrue(skill["sparkline"])

    def test_sample_match_with_error_category_is_not_scored_as_solved(self):
        record = CodeFeedbackRecord.objects.get(evaluation_sample_id="demo-student2-even-002")

        self.assertEqual(record.output_comparison_status, "exact_match")
        self.assertEqual(record.error_category, "Division and modulo")
        self.assertEqual(_attempt_score(record), 40)

    def test_class_analytics_separates_statistics_from_saved_suggestions(self):
        context = build_class_analytics()

        self.assertEqual(context["submission_count"], 20)
        self.assertEqual(context["question_count"], 20)
        self.assertEqual(len(context["student_profiles"]), 2)
        self.assertIn(
            "Misspelled names or keywords",
            [item["error_category"] for item in context["common_errors"]],
        )
        self.assertTrue(context["concept_weakness"])
        self.assertTrue(context["instructional_recommendations"])
        self.assertTrue(context["saved_next_steps"])


@override_settings(ALLOWED_HOSTS=["testserver"])
class RoleAndStudentPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", with_history=True, verbosity=0)

    def test_home_redirects_by_role(self):
        self.client.login(username="student1", password="student123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/student/")

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/instructor/")

    def test_login_post_redirects_to_the_right_role_home(self):
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "student1",
                "password": "student123",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/student/")

        self.client.logout()
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "instructor",
                "password": "instructor123",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], "/instructor/")

    def test_anonymous_users_are_redirected_to_login(self):
        for path in [
            "/",
            "/student/",
            "/profile/",
            "/history/",
            "/instructor/",
            "/experiment/",
            "/analytics/",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response["Location"].startswith("/accounts/login/"))

    @override_settings(DEBUG=True)
    def test_debug_login_page_shows_demo_accounts(self):
        response = self.client.get("/accounts/login/")

        self.assertContains(response, "Demo accounts")
        self.assertContains(response, "student1")
        self.assertContains(response, "student2")
        self.assertContains(response, "instructor")

    @override_settings(DEBUG=False)
    def test_non_debug_login_page_hides_demo_accounts(self):
        response = self.client.get("/accounts/login/")

        self.assertNotContains(response, "Demo accounts")
        self.assertNotContains(response, "student1")
        self.assertNotContains(response, "student2")
        self.assertNotContains(response, "<code>instructor</code>", html=True)

    def test_student_portal_hides_teacher_side_metadata(self):
        self.client.login(username="student1", password="student123")

        response = self.client.get("/student/")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Sample Input", html)
        self.assertIn("Expected Output", html)
        self.assertNotIn("Lecture Objective", html)
        self.assertNotIn("Comparison:", html)
        self.assertNotIn("DeepSeek", html)
        self.assertNotIn("Kimi", html)
        self.assertNotIn("Experiment", html)
        self.assertNotIn("Instructor", html)

    def test_question_dropdown_orders_and_labels_student_progress(self):
        student = get_user_model().objects.create_user(
            username="question_status_student",
            password="test_password",
        )
        in_progress_question = Question.objects.get(title="Average of a list")
        solved_question = Question.objects.get(title="Sum from 1 to 10")

        for code in ("print(0)", "print(2)"):
            CodeFeedbackRecord.objects.create(
                user=student,
                question=in_progress_question,
                problem_statement=in_progress_question.problem_statement,
                student_code=code,
                classification_outcome="peci_error",
                solved=False,
            )
        CodeFeedbackRecord.objects.create(
            user=student,
            question=solved_question,
            problem_statement=solved_question.problem_statement,
            student_code="print(sum(range(1, 11)))",
            classification_outcome="no_error",
            execution_status="success",
            output_comparison_status="exact_match",
            solved=True,
        )
        self.client.force_login(student)

        response = self.client.get("/student/")
        questions = list(response.context["questions"])
        labels = [
            str(label)
            for _value, label in response.context["form"].fields["question"].choices
        ]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(questions[0].title, "Average of a list")
        self.assertEqual(questions[0].status, "in_progress")
        self.assertEqual(questions[0].attempts, 2)
        self.assertEqual(questions[-1].title, "Sum from 1 to 10")
        self.assertEqual(questions[-1].status, "solved")
        self.assertEqual(labels[0], "↻ Average of a list (2)")
        self.assertIn("○ Even or odd", labels)
        self.assertEqual(labels[-1], "✓ Sum from 1 to 10")
        self.assertContains(response, "In progress - 2 attempts")
        self.assertContains(response, "Not started")
        self.assertContains(response, "Solved")

    def test_staff_is_redirected_away_from_student_portal(self):
        self.client.login(username="instructor", password="instructor123")

        response = self.client.get("/student/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/instructor/")

    def test_experiment_interface_is_staff_only(self):
        self.client.login(username="student1", password="student123")
        response = self.client.get("/experiment/")
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        response = self.client.get("/experiment/")
        self.assertContains(response, "Evaluator-only")
        self.assertContains(response, "AI Tutor")
        self.assertContains(response, "Prompt Version")

    def test_analytics_dashboard_is_staff_only(self):
        self.client.login(username="student1", password="student123")
        response = self.client.get("/analytics/")
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        response = self.client.get("/analytics/")
        self.assertContains(response, "Class Analytics")
        self.assertContains(response, "Common PECI Error Categories")
        self.assertContains(response, "Weak Concepts")
        self.assertContains(response, "Instructional Suggestions")
        self.assertContains(response, "Skill Mastery Overview")
        self.assertContains(response, "Hard Questions")
        self.assertContains(response, "Student Activity")
        self.assertContains(response, "Division and modulo")

    def test_evaluation_dashboard_is_staff_only(self):
        self.client.login(username="student1", password="student123")
        response = self.client.get("/evaluation/")
        self.assertEqual(response.status_code, 403)

        EvaluationRun.objects.create(
            name="Dashboard artifact test",
            dataset_size=2,
            providers=["deepseek"],
            prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
            summary={
                "total_results": 2,
                "category_accuracy": 1.0,
                "json_compliance_rate": 1.0,
                "solution_leakage_rate": 0.0,
                "runtime_evidence_usage_rate": 1.0,
                "average_latency_ms": 0,
                "day12_analysis": {
                    "human_review_metrics": {
                        "review_coverage_rate": 0.5,
                        "average_helpfulness_score": 4.0,
                        "average_actionability_score": 5.0,
                    },
                    "artifact_paths": {
                        "summary_markdown": "/tmp/run_1_day12_summary.md",
                        "manual_review_csv": "/tmp/run_1_manual_review_template.csv",
                    },
                },
            },
        )

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        response = self.client.get("/evaluation/")
        self.assertContains(response, "Batch Evaluation Results")
        self.assertContains(response, "Systematic Evaluation")
        self.assertContains(response, "Historical taxonomy notice")
        self.assertContains(response, "not PECI Table 1 categories")
        self.assertContains(response, "Key findings for demo/report discussion")
        self.assertContains(response, "Runtime evidence is the main improvement")
        self.assertContains(response, "Kimi was more accurate but slower and more costly")
        self.assertContains(response, "Function vs Logic boundaries need refinement")
        self.assertContains(response, "Database Run Detail")
        self.assertContains(response, "AI-Assisted Review Coverage")
        self.assertContains(response, "Report Artifacts")
        self.assertContains(response, "manual_review_csv")

    def test_student_profile_routes_use_role_boundaries(self):
        User = get_user_model()
        student1 = User.objects.get(username="student1")

        self.client.login(username="student1", password="student123")
        response = self.client.get("/profile/")
        self.assertContains(response, "My Learning Progress")
        self.assertContains(response, "Skill Mastery Radar")
        self.assertContains(response, "How mastery is calculated")
        self.assertContains(response, "Repeated Error Pattern")
        self.assertContains(response, "Next-Step Suggestions")

        response = self.client.get(f"/analytics/students/{student1.id}/")
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        response = self.client.get(f"/analytics/students/{student1.id}/")
        self.assertContains(response, "Student Profile")
        self.assertContains(response, "Skill Mastery Radar")
        self.assertContains(response, "Weak Concepts")
        self.assertContains(response, "Mastered Concepts")

    def test_skill_detail_routes_enforce_student_boundaries(self):
        User = get_user_model()
        student1 = User.objects.get(username="student1")
        student2 = User.objects.get(username="student2")
        own_path = f"/analytics/students/{student1.id}/skill/iteration_range/"

        self.client.login(username="student1", password="student123")
        response = self.client.get(own_path)
        self.assertContains(response, "Iteration and Range Attempt Timeline")
        self.assertContains(response, "prototype heuristic")
        self.assertContains(response, "Sum from 1 to 10")

        response = self.client.get(
            f"/analytics/students/{student2.id}/skill/conditionals_boolean/"
        )
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        response = self.client.get(own_path)
        self.assertContains(response, "Back to Student Profile")

        response = self.client.get(
            f"/analytics/students/{student1.id}/skill/not_a_fixed_topic/"
        )
        self.assertEqual(response.status_code, 404)

    def test_instructor_dashboard_exposes_question_management_workflow(self):
        self.client.login(username="instructor", password="instructor123")

        response = self.client.get("/instructor/")

        self.assertContains(response, "Question Bank")
        self.assertContains(response, "Add Question")
        self.assertContains(response, "Manage Questions")
        self.assertContains(response, "Analytics")
        self.assertContains(response, "Function square")
        self.assertContains(response, "strict")

    def test_student_history_contains_only_own_records(self):
        self.client.login(username="student1", password="student123")

        response = self.client.get("/history/")
        records = list(response.context["records"])

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(records), 0)
        self.assertTrue(all(record.user.username == "student1" for record in records))

    def test_student_cannot_view_another_students_record_detail(self):
        other_record = CodeFeedbackRecord.objects.filter(user__username="student2").first()
        self.client.login(username="student1", password="student123")

        response = self.client.get(f"/history/{other_record.id}/")

        self.assertEqual(response.status_code, 403)

    def test_instructor_can_filter_history_by_student_and_question(self):
        User = get_user_model()
        student2 = User.objects.get(username="student2")
        question = Question.objects.get(title="Even or odd")
        self.client.login(username="instructor", password="instructor123")

        response = self.client.get(
            "/history/",
            {
                "student": student2.id,
                "question": question.id,
            },
        )
        records = list(response.context["records"])

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(records), 0)
        self.assertTrue(all(record.user_id == student2.id for record in records))
        self.assertTrue(all(record.question_id == question.id for record in records))

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_student_submission_binds_user_and_question(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": """
{
  "error_category": "Loop Boundary Error",
  "feedback_level": "Level 2",
  "concept_reference": "Iteration and Range",
  "feedback": "The output is close, but check whether the loop includes the final value.",
  "does_reveal_solution": false,
  "uses_runtime_evidence": true,
  "suggested_next_step": "Print the values generated by range().",
  "confidence": "high"
}
""",
            "model_name": "deepseek-chat",
            "usage": {"prompt_tokens": 100, "completion_tokens": 80, "total_tokens": 180},
            "estimated_cost": None,
        }
        question = Question.objects.get(title="Sum from 1 to 10")
        self.client.login(username="student1", password="student123")

        response = self.client.post(
            "/student/",
            {
                "question": question.id,
                "student_code": "print(sum(range(1, 10)))\n",
            },
        )
        record = CodeFeedbackRecord.objects.latest("id")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(record.user.username, "student1")
        self.assertEqual(record.question, question)
        self.assertEqual(record.output_comparison_status, "mismatch")
        self.assertContains(response, "Retry this question")
        self.assertContains(response, "Jump to another question")
        self.assertNotIn("Prompt:", html)
        self.assertNotIn("Schema status", html)
        self.assertNotIn("DeepSeek", html)
        self.assertNotIn("Comparison mode", html)
        self.assertNotIn("Confidence", html)
        self.assertNotIn("AI self-reported confidence", html)

        detail_response = self.client.get(f"/history/{record.id}/")
        self.assertNotContains(detail_response, "Confidence")
        self.assertNotContains(detail_response, "AI self-reported confidence")

        self.client.logout()
        self.client.login(username="instructor", password="instructor123")
        instructor_detail = self.client.get(f"/history/{record.id}/")
        self.assertContains(instructor_detail, "AI self-reported confidence")
        self.assertContains(instructor_detail, "Not a calibrated reliability score")

        self.client.logout()
        self.client.login(username="student1", password="student123")

        retry_response = self.client.get("/student/", {"retry": record.id})
        retry_form = retry_response.context["form"]
        self.assertEqual(retry_response.status_code, 200)
        self.assertEqual(retry_form.initial["question"], question)
        self.assertEqual(
            retry_form.initial["student_code"],
            "print(sum(range(1, 10)))",
        )
        self.assertContains(retry_response, "Your previous code is preserved below")

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_solved_requires_llm_and_deterministic_runtime_agreement(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": json.dumps({
                "classification_outcome": "no_error",
                "peci_error_code": "",
                "feedback_level": "Level 1",
                "concept_reference": "Iteration and Range",
                "misconception": "",
                "feedback": "The submitted program appears correct.",
                "does_reveal_solution": False,
                "uses_runtime_evidence": True,
                "suggested_next_step": "Review the runtime result.",
                "confidence": "high",
            }),
            "model_name": "deepseek-chat",
            "usage": {},
            "estimated_cost": None,
        }
        student = get_user_model().objects.create_user(
            username="solved_evidence_student", password="test_password"
        )
        question = Question.objects.get(title="Sum from 1 to 10")
        self.client.force_login(student)

        mismatch_response = self.client.post(
            "/student/", {"question": question.pk, "student_code": "print(45)"}
        )
        mismatch_record = CodeFeedbackRecord.objects.filter(user=student).latest("id")
        self.assertEqual(mismatch_record.classification_outcome, "no_error")
        self.assertEqual(mismatch_record.execution_status, "success")
        self.assertEqual(mismatch_record.output_comparison_status, "mismatch")
        self.assertFalse(mismatch_record.solved)
        self.assertEqual(_attempt_score(mismatch_record), 45)
        self.assertNotIn("<strong>Solved</strong>", mismatch_response.content.decode())

        error_response = self.client.post(
            "/student/",
            {"question": question.pk, "student_code": "for i in range(3)\n    print(i)"},
        )
        error_record = CodeFeedbackRecord.objects.filter(user=student).latest("id")
        self.assertEqual(error_record.classification_outcome, "no_error")
        self.assertNotEqual(error_record.execution_status, "success")
        self.assertEqual(error_record.output_comparison_status, "execution_error")
        self.assertFalse(error_record.solved)
        self.assertEqual(_attempt_score(error_record), 20)
        self.assertNotIn("<strong>Solved</strong>", error_response.content.decode())

        solved_response = self.client.post(
            "/student/",
            {"question": question.pk, "student_code": "print(sum(range(1, 11)))"},
        )
        solved_record = CodeFeedbackRecord.objects.filter(user=student).latest("id")
        self.assertEqual(solved_record.classification_outcome, "no_error")
        self.assertEqual(solved_record.execution_status, "success")
        self.assertEqual(solved_record.output_comparison_status, "exact_match")
        self.assertTrue(solved_record.solved)
        self.assertEqual(_attempt_score(solved_record), 100)
        self.assertIn("<strong>Solved</strong>", solved_response.content.decode())
        profile = build_student_profile(student)
        self.assertEqual(profile["solved_total"], 1)
        self.assertEqual(profile["unresolved_total"], 2)
        self.assertEqual(profile["solved_rate"], 33)
        self.assertEqual(mock_call_llm.call_count, 3)

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_live_attempts_store_misconception_and_track_each_question(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": json.dumps({
                "classification_outcome": "peci_error",
                "peci_error_code": "E",
                "feedback_level": "Level 2",
                "concept_reference": "Variables and Assignment",
                "misconception": "The student replaces the accumulated total instead of adding to it.",
                "feedback": "Check how the total changes in each iteration.",
                "does_reveal_solution": False,
                "uses_runtime_evidence": True,
                "suggested_next_step": "Trace the accumulator for two iterations.",
                "confidence": "high",
            }),
            "model_name": "deepseek-chat",
            "usage": {},
            "estimated_cost": None,
        }
        student = get_user_model().objects.create_user(
            username="live_student", password="test_password"
        )
        sum_question = Question.objects.get(title="Sum from 1 to 10")
        greeting_question = Question.objects.get(title="Greeting with input")
        self.client.force_login(student)

        records = []
        for question in (sum_question, sum_question, greeting_question, sum_question):
            response = self.client.post(
                "/student/", {"question": question.pk, "student_code": "print(45)"}
            )
            self.assertEqual(response.status_code, 200)
            records.append(CodeFeedbackRecord.objects.filter(user=student).latest("id"))

        self.assertEqual(mock_call_llm.call_count, 4)
        self.assertEqual(
            [record.trajectory_attempt_number for record in records], [1, 2, 1, 3]
        )
        self.assertTrue(records[0].trajectory_id)
        self.assertLess(len(records[0].trajectory_id), 100)
        self.assertEqual(records[0].trajectory_id, records[1].trajectory_id)
        self.assertEqual(records[0].trajectory_id, records[3].trajectory_id)
        self.assertNotEqual(records[0].trajectory_id, records[2].trajectory_id)
        self.assertTrue(all(record.misconception for record in records))
        self.assertContains(response, "Misconception")

    @patch("feedback_app.views.call_llm_with_metadata")
    def test_live_submission_starts_trajectory_after_legacy_record(self, mock_call_llm):
        mock_call_llm.return_value = {
            "content": "{\"classification_outcome\": \"unknown\"}",
            "model_name": "deepseek-chat",
        }
        student = get_user_model().objects.create_user(
            username="legacy_student", password="test_password"
        )
        question = Question.objects.get(title="Sum from 1 to 10")
        CodeFeedbackRecord.objects.create(
            user=student,
            question=question,
            problem_statement=question.problem_statement,
            student_code="print(0)",
        )
        self.client.force_login(student)

        response = self.client.post(
            "/student/", {"question": question.pk, "student_code": "print(45)"}
        )
        record = CodeFeedbackRecord.objects.filter(user=student).latest("id")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(record.trajectory_id)
        self.assertEqual(record.trajectory_attempt_number, 1)
        self.assertEqual(record.misconception, "")

    def test_student_cannot_retry_another_students_attempt(self):
        other_record = CodeFeedbackRecord.objects.filter(user__username="student2").first()
        self.client.login(username="student1", password="student123")

        response = self.client.get("/student/", {"retry": other_record.id})

        self.assertEqual(response.status_code, 404)

    def test_jump_flow_returns_an_uninitialised_submission_form(self):
        self.client.login(username="student1", password="student123")

        response = self.client.get("/student/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("student_code", response.context["form"].initial)
        self.assertNotContains(response, "Your previous code is preserved below")


class SeedDemoCommandTests(TestCase):
    def test_seed_demo_creates_reproducible_students_questions_and_history(self):
        call_command("seed_demo", with_history=True, verbosity=0)
        initial_count = CodeFeedbackRecord.objects.filter(
            evaluation_sample_id__startswith="demo-"
        ).count()

        call_command("seed_demo", with_history=True, verbosity=0)
        repeated_count = CodeFeedbackRecord.objects.filter(
            evaluation_sample_id__startswith="demo-"
        ).count()

        self.assertEqual(initial_count, 20)
        self.assertEqual(repeated_count, 20)
        self.assertEqual(Question.objects.count(), 20)
        self.assertEqual(
            Question.objects.get(title="Function square").comparison_mode,
            COMPARISON_MODE_STRICT,
        )

        for username in ("student1", "student2"):
            student_records = CodeFeedbackRecord.objects.filter(user__username=username)
            question_count = student_records.values("question").distinct().count()
            self.assertEqual(question_count, 2)
            for question_id in student_records.values_list("question_id", flat=True).distinct():
                question_records = student_records.filter(question_id=question_id)
                self.assertEqual(question_records.count(), 5)
                self.assertEqual(
                    list(
                        question_records.order_by("trajectory_attempt_number").values_list(
                            "trajectory_attempt_number", flat=True
                        )
                    ),
                    [1, 2, 3, 4, 5],
                )
                self.assertEqual(
                    question_records.get(trajectory_attempt_number=5).classification_outcome,
                    "no_error",
                )
                self.assertFalse(
                    question_records.get(trajectory_attempt_number=4).solved
                )
                self.assertTrue(
                    question_records.get(trajectory_attempt_number=5).solved
                )

    def test_seed_questions_use_fixed_topics_with_minimum_coverage(self):
        call_command("seed_demo", verbosity=0)
        coverage = {topic_id: 0 for topic_id in TOPIC_TAXONOMY}

        for question in Question.objects.all():
            topic_ids = parse_topic_tags(question.topic_tags)
            self.assertTrue(topic_ids)
            self.assertEqual(question.topic_tags, serialize_topic_tags(topic_ids))
            for topic_id in topic_ids:
                coverage[topic_id] += 1

        self.assertEqual(Question.objects.count(), 20)
        self.assertTrue(all(total >= 2 for total in coverage.values()), coverage)

    def test_seed_history_persists_trajectory_metadata(self):
        call_command("seed_demo", with_history=True, verbosity=0)
        trajectory = CodeFeedbackRecord.objects.filter(
            trajectory_id="demo-student1-sum"
        ).order_by("trajectory_attempt_number")

        self.assertEqual(trajectory.count(), 5)
        self.assertTrue(all(record.misconception for record in trajectory))
        self.assertEqual(trajectory.first().classification_outcome, "peci_error")
        self.assertFalse(trajectory.first().solved)
        self.assertEqual(trajectory.last().classification_outcome, "no_error")
        self.assertTrue(trajectory.last().solved)
        self.assertEqual(trajectory.last().actual_output, "55\n")

    def test_seed_demo_stores_canonical_taxonomy_labels(self):
        call_command("seed_demo", with_history=True, verbosity=0)

        for record in CodeFeedbackRecord.objects.filter(
            evaluation_sample_id__startswith="demo-"
        ):
            self.assertIn(
                record.classification_outcome,
                {"peci_error", "no_error", "outside_peci_scope"},
            )
            if record.classification_outcome == "peci_error":
                self.assertIn(record.peci_error_code, PECI_ERROR_CODES)
                self.assertTrue(record.peci_error_label)
            else:
                self.assertEqual(record.peci_error_code, "")
            self.assertEqual(record.legacy_error_category, "")
            self.assertTrue(record.trajectory_id)
            self.assertIsNotNone(record.trajectory_attempt_number)
            self.assertTrue(record.misconception)

    def test_reset_demo_history_removes_manual_demo_records_before_reseeding(self):
        call_command("seed_demo", verbosity=0)
        student = get_user_model().objects.get(username="student1")
        question = Question.objects.get(title="Sum from 1 to 10")
        stale_record = CodeFeedbackRecord.objects.create(
            user=student,
            question=question,
            problem_statement=question.problem_statement,
            lecture_objective=question.lecture_objective,
            student_code="print(45)",
            error_category="Loop Boundary Error",
            prompt_version="strict_scaffolded",
            llm_model_name="deepseek-chat",
        )

        call_command(
            "seed_demo",
            with_history=True,
            reset_demo_history=True,
            verbosity=0,
        )

        self.assertFalse(CodeFeedbackRecord.objects.filter(pk=stale_record.pk).exists())
        self.assertEqual(
            CodeFeedbackRecord.objects.filter(user__username="student1").count(),
            10,
        )

    def test_reset_demo_history_requires_history_option(self):
        with self.assertRaisesMessage(
            CommandError,
            "--reset-demo-history requires --with-history.",
        ):
            call_command("seed_demo", reset_demo_history=True, verbosity=0)


class CategoryCleanupCommandTests(TestCase):
    def test_canonicalize_categories_updates_existing_records(self):
        first = CodeFeedbackRecord.objects.create(
            problem_statement="Print a sum.",
            lecture_objective="Use loops.",
            student_code="print(sum(range(1, 10)))",
            error_category="off_by_one",
            ground_truth_category="no_error",
        )
        second = CodeFeedbackRecord.objects.create(
            problem_statement="Define a function.",
            lecture_objective="Use indentation.",
            student_code="def f():\nprint(1)",
            error_category="Syntax Error / Indentation Error",
            ground_truth_category="operator_misuse",
        )
        third = CodeFeedbackRecord.objects.create(
            problem_statement="Use modulo.",
            lecture_objective="Check divisibility.",
            student_code="print(7 / 2)",
            error_category="I - Division and modulo",
            ground_truth_category="I - Division and modulo",
            classification_outcome="peci_error",
            peci_error_code="I",
            peci_error_label="Division and modulo",
            feedback_schema_version="feedback_schema_v3_peci",
        )

        call_command("canonicalize_categories", stdout=io.StringIO())

        first.refresh_from_db()
        second.refresh_from_db()
        third.refresh_from_db()
        self.assertEqual(first.error_category, "Loop Boundary Error")
        self.assertEqual(first.ground_truth_category, "No Error")
        self.assertEqual(second.error_category, "Indentation Error")
        self.assertEqual(second.ground_truth_category, "Condition Error")
        self.assertEqual(third.error_category, "Division and modulo")
        self.assertEqual(third.peci_error_code, "I")
