import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .code_runner import run_python_code
from .feedback_schema import ERROR_CATEGORIES
from .output_comparison import (
    COMPARISON_MODE_NORMALIZED,
    COMPARISON_MODE_STRICT,
    EXECUTION_ERROR,
    MISMATCH,
    TIMEOUT,
    compare_outputs,
)


EVALUATION_DATASET_FILENAME = "evaluation_samples.json"
EVALUATION_SOURCE_REPORT_FILENAME = "evaluation_dataset_sources.md"
SAMPLE_ORIGIN_REFACTORY = "real_student_submission_refactory"
SAMPLE_ORIGIN_HAND_CRAFTED = "hand_crafted_boundary_case"
ALLOWED_SAMPLE_ORIGINS = {SAMPLE_ORIGIN_REFACTORY, SAMPLE_ORIGIN_HAND_CRAFTED}
DEFAULT_REFACTORY_DATA_DIR = Path(
    os.environ.get("REFACTORY_DATA_DIR", "/private/tmp/refactory_data/data")
)

REFACTORY_SOURCE_METADATA = {
    "dataset_name": "Refactory",
    "dataset_repository": "https://github.com/githubhuyang/refactory",
    "dataset_archive": "https://github.com/githubhuyang/refactory/blob/master/data.zip",
    "user_reference": (
        "6hao.pdf / Haque et al. (2025), Section 3.1 Datasets: "
        "uses Refactory as a faulty Python student-program dataset."
    ),
    "original_paper": (
        "Hu et al. (2019), Refactory: A Tool for Refactoring Python "
        "Programs, ASE 2019, Section V and Table II."
    ),
    "original_paper_dataset_note": (
        "The Refactory paper reports 2,442 correct and 1,783 incorrect "
        "student submissions from 361 students across five Python assignments."
    ),
    "repository_dataset_note": (
        "The repository README states that data.zip contains 2,442 correct "
        "and 1,783 buggy program attempts by 361 NUS undergraduate students."
    ),
    "license": "LGPL-3.0 license in the Refactory GitHub repository.",
}

QUESTION_OBJECTIVES = {
    1: "Use loops and conditional boundaries to find an insertion index in a sorted sequence.",
    2: "Use helper functions, tuple indexing, and Boolean return values to reason about unique dates.",
    3: "Use list traversal and membership checks to remove duplicate elements while preserving order.",
    4: "Use tuple indexing and selection/swap logic to sort records by descending age.",
    5: "Use loops and list operations to return the greatest k values in descending order.",
}

EVALUATION_TAXONOMY = [
    {
        "id": "conditional_boundary",
        "label": "Conditional boundary",
        "canonical_categories": ["Condition Error"],
        "literature_basis": "Boundary comparisons such as < versus <= are recurrent novice logic mistakes.",
    },
    {
        "id": "syntax_indentation",
        "label": "Syntax and indentation",
        "canonical_categories": ["Syntax Error", "Indentation Error"],
        "literature_basis": "Beginner Python submissions frequently fail because of missing punctuation or block indentation.",
    },
    {
        "id": "loop_boundary_off_by_one",
        "label": "Loop boundary and off-by-one",
        "canonical_categories": ["Loop Boundary Error"],
        "literature_basis": "Loop bounds, termination conditions, and early return placement often cause wrong outputs.",
    },
    {
        "id": "name_undefined_variable",
        "label": "Name and undefined variable",
        "canonical_categories": ["Name Error"],
        "literature_basis": "Variable-name mismatches and uninitialised local variables appear in real beginner submissions.",
    },
    {
        "id": "type_operation",
        "label": "Type and operation misuse",
        "canonical_categories": ["Type Error", "Value Error"],
        "literature_basis": "Students may call methods incorrectly or use operations on incompatible values.",
    },
    {
        "id": "input_handling",
        "label": "Input handling",
        "canonical_categories": ["Input Error", "Value Error"],
        "literature_basis": "Programs that assume missing or malformed input can fail even when their core algorithm is close.",
    },
    {
        "id": "list_indexing",
        "label": "List and indexing",
        "canonical_categories": ["Index Error"],
        "literature_basis": "Indexing and mutation during traversal can access elements outside a list or tuple.",
    },
    {
        "id": "function_return",
        "label": "Function return and call behaviour",
        "canonical_categories": ["Function Error"],
        "literature_basis": "Function tasks expose missing returns, printing instead of returning, and method-call confusion.",
    },
    {
        "id": "algorithm_logic",
        "label": "Algorithmic logic",
        "canonical_categories": ["Logic Error"],
        "literature_basis": "Real submissions often run successfully but fail tests because the algorithmic state update is wrong.",
    },
    {
        "id": "timeout_infinite_loop",
        "label": "Timeout and infinite loop",
        "canonical_categories": ["Timeout"],
        "literature_basis": "Non-terminating loops are an important sandbox and feedback boundary case for beginner programs.",
    },
    {
        "id": "output_formatting",
        "label": "Output formatting",
        "canonical_categories": ["Output Format Error"],
        "literature_basis": "Some novice submissions compute the right idea but fail exact-output tasks because of formatting.",
    },
    {
        "id": "module_import",
        "label": "Module import",
        "canonical_categories": ["Module Import Error"],
        "literature_basis": "Unavailable or misspelled imports should be identified as environment/import issues rather than logic bugs.",
    },
]

TAXONOMY_BY_ID = {item["id"]: item for item in EVALUATION_TAXONOMY}


@dataclass(frozen=True)
class RefactoryRecord:
    question_id: int
    filename: str
    ground_truth_category: str
    taxonomy_group: str
    expected_feedback_focus: str
    annotation_note: str

    @property
    def sample_id(self):
        record_number = self.filename.replace(".py", "").split("_")[-1]
        return f"refactory-q{self.question_id}-wrong-{record_number}"

    @property
    def relative_code_path(self):
        return f"data/question_{self.question_id}/code/wrong/{self.filename}"


@dataclass(frozen=True)
class HandCraftedRecord:
    sample_id: str
    ground_truth_category: str
    taxonomy_group: str
    problem_statement: str
    lecture_objective: str
    student_code: str
    expected_output: str
    expected_feedback_focus: str
    annotation_note: str
    sample_input: str = ""
    support_code: str = ""
    test_harness: str = ""
    comparison_mode: str = COMPARISON_MODE_NORMALIZED

    @property
    def relative_code_path(self):
        return f"hand_crafted/{self.sample_id}.py"


SELECTED_REFACTORY_RECORDS = [
    RefactoryRecord(1, "wrong_1_001.py", "Condition Error", "conditional_boundary", "Check whether the comparison should include equality when x matches an existing sequence value.", "The first failing test returns index 2 instead of 1 because the branch uses x < e rather than x <= e."),
    RefactoryRecord(1, "wrong_1_002.py", "Name Error", "name_undefined_variable", "Check what happens to the loop variable when the sequence is empty.", "The failing empty-sequence test raises UnboundLocalError because i is returned after a loop that never ran."),
    RefactoryRecord(1, "wrong_1_003.py", "Loop Boundary Error", "loop_boundary_off_by_one", "Check the fallback return value after the loop, especially for an empty sequence.", "The fallback uses i + 1 after initialising i to 0, so an empty sequence returns 1 instead of 0."),
    RefactoryRecord(1, "wrong_1_004.py", "Index Error", "list_indexing", "Inspect the j + 1 access near the final iteration of the sequence loop.", "The test with an empty sequence reaches seq[0], producing an IndexError before any boundary handling."),
    RefactoryRecord(1, "wrong_1_005.py", "Index Error", "list_indexing", "Check whether the empty-sequence guard handles both tuples and lists.", "The code only guards seq == (), so an empty list reaches seq[0] and raises IndexError."),
    RefactoryRecord(1, "wrong_1_006.py", "Index Error", "list_indexing", "Trace the access to seq[i + 1] when i is already at the final valid index.", "The loop iterates to length - 1 and then reads seq[i + 1], which can go beyond the tuple."),
    RefactoryRecord(1, "wrong_1_007.py", "Logic Error", "algorithm_logic", "Check whether the else branch should return after only the first comparison.", "The else branch is nested inside the loop, so the function can return too early after checking one element."),
    RefactoryRecord(1, "wrong_1_008.py", "Condition Error", "conditional_boundary", "Check the boundary case where x is equal to the final element.", "The x >= seq[-1] condition returns the last existing index instead of the insertion position after duplicates."),
    RefactoryRecord(1, "wrong_1_009.py", "Logic Error", "algorithm_logic", "Compare each element with the next actual sequence value instead of elem + 1.", "The condition elem < x < elem + 1 assumes consecutive numbers rather than using neighbouring sequence elements."),
    RefactoryRecord(1, "wrong_1_010.py", "Condition Error", "conditional_boundary", "Check whether comparing x with elem + 1 is meaningful for an arbitrary sorted sequence.", "The condition returns a position based on numeric distance from elem, not the next sequence boundary."),
    RefactoryRecord(1, "wrong_1_011.py", "Logic Error", "algorithm_logic", "Trace the returned index for values greater than all sequence elements.", "The function returns None for values outside its narrow elem-to-elem+1 condition range."),
    RefactoryRecord(2, "wrong_2_001.py", "Logic Error", "algorithm_logic", "Check how contains_unique_day should behave when a month has no uniquely identifying day.", "The helper functions run, but the final Boolean decision is wrong on a case where the expected result is False."),
    RefactoryRecord(2, "wrong_2_002.py", "Logic Error", "algorithm_logic", "Check whether contains_unique_day should require exactly one unique day or at least one unique day.", "The code returns len(days) == 1, which rejects months that contain more than one uniquely identifying day."),
    RefactoryRecord(2, "wrong_2_003.py", "Logic Error", "algorithm_logic", "Revisit the Boolean condition used after collecting candidate days.", "The implementation is structurally valid but uses the wrong aggregate condition for the final result."),
    RefactoryRecord(2, "wrong_2_004.py", "Name Error", "name_undefined_variable", "Compare the function parameter name with the variable used inside the loop condition.", "The function parameter is date, but the body reads day, causing NameError."),
    RefactoryRecord(2, "wrong_2_005.py", "Name Error", "name_undefined_variable", "Check whether the variable inside unique_day matches the parameter name.", "The unique_day body references day even though the parameter is named date."),
    RefactoryRecord(2, "wrong_2_006.py", "Name Error", "name_undefined_variable", "Trace the counter variable names used in unique_day and unique_month.", "The code mixes days, day, and month counters, leading to an undefined variable at runtime."),
    RefactoryRecord(2, "wrong_2_007.py", "Name Error", "name_undefined_variable", "Check all counter names before using them in conditions.", "A counter is initialised with one name but updated or checked using a different name."),
    RefactoryRecord(2, "wrong_2_008.py", "Logic Error", "algorithm_logic", "Check whether unique_day compares the target day with the tuple day field.", "The function compares possible_birthdays[i][1] to the counter variable days instead of the input date/day."),
    RefactoryRecord(2, "wrong_2_009.py", "Logic Error", "algorithm_logic", "Trace the value being counted in unique_day.", "The day-counting loop is syntactically valid but compares the date field to the wrong variable."),
    RefactoryRecord(2, "wrong_2_010.py", "Logic Error", "algorithm_logic", "Check whether the helper result depends on the correct argument value or on a counter.", "The unique_day helper increments/checks counters but does not correctly test the requested day."),
    RefactoryRecord(2, "wrong_2_011.py", "Name Error", "name_undefined_variable", "Check variable names in the comparison expression inside unique_day.", "The body reads day even though the available local variable is days/date."),
    RefactoryRecord(3, "wrong_3_001.py", "Logic Error", "algorithm_logic", "Check whether new elements should be appended when they are already in the output or not yet in it.", "The membership condition is reversed, so the result starts empty and never collects first occurrences."),
    RefactoryRecord(3, "wrong_3_002.py", "Name Error", "name_undefined_variable", "Look for spelling consistency between occurrences and occurences/new_list.", "The code uses misspelled or undefined list/counter names during the loop."),
    RefactoryRecord(3, "wrong_3_003.py", "Name Error", "name_undefined_variable", "Check whether the list that is appended to has the same name as the list that was created.", "new_lst is initialised, but new_list is appended to."),
    RefactoryRecord(3, "wrong_3_004.py", "Name Error", "name_undefined_variable", "Trace the output-list variable from initialisation to return.", "The append target and the returned variable do not use the same name."),
    RefactoryRecord(3, "wrong_3_005.py", "Index Error", "list_indexing", "Check what happens when the input list is empty before reading lst[0].", "The code immediately creates result = [lst[0]], which fails for an empty list."),
    RefactoryRecord(3, "wrong_3_006.py", "Type Error", "type_operation", "Check whether the loop iterates over the input variable or over Python's list type.", "The loop uses for number in list, which tries to iterate over the built-in type rather than lst."),
    RefactoryRecord(3, "wrong_3_007.py", "Function Error", "function_return", "Check the difference between referencing a method and calling it.", "The code stores lst.reverse instead of lst.reverse(), then tries to use it like a list."),
    RefactoryRecord(3, "wrong_3_008.py", "Function Error", "function_return", "Check whether reverse has been called and whether the result is a list.", "The method object lst.reverse is treated as a mutable list, causing an attribute/method-use failure."),
    RefactoryRecord(3, "wrong_3_009.py", "Type Error", "type_operation", "Check what type range() expects as its argument.", "The code passes the whole list to range instead of passing its length."),
    RefactoryRecord(3, "wrong_3_010.py", "Index Error", "list_indexing", "Avoid changing list length while iterating over indexes based on the original length.", "The code pops elements while iterating over range(len(lst)), so later indexes can become invalid."),
    RefactoryRecord(3, "wrong_3_011.py", "Index Error", "list_indexing", "Trace the indexes after each pop operation.", "Even with len(lst) - 1, mutating the list inside the loop can still invalidate later indexes."),
    RefactoryRecord(4, "wrong_4_001.py", "Type Error", "type_operation", "Check whether pop is being called with parentheses or indexed with brackets.", "The code uses lst.pop[index], treating the pop method as a subscriptable object."),
    RefactoryRecord(4, "wrong_4_002.py", "Name Error", "name_undefined_variable", "Check the variable names used when removing and appending the selected tuple.", "The code tries to remove from a and append smallest, but those names are not defined."),
    RefactoryRecord(4, "wrong_4_003.py", "Name Error", "name_undefined_variable", "Trace whether the list variable being removed from is the function parameter.", "The code calls a.remove even though the working list variable is lst."),
    RefactoryRecord(4, "wrong_4_004.py", "Name Error", "name_undefined_variable", "Check whether all variables used after the loop were created in the function.", "The code references a even though it has never been initialised."),
    RefactoryRecord(4, "wrong_4_005.py", "Function Error", "function_return", "Check whether the function returns the sorted list or only prints an intermediate value.", "The code prints and falls through without returning the expected sorted list."),
    RefactoryRecord(4, "wrong_4_006.py", "Logic Error", "algorithm_logic", "Check whether oldest is updated when a larger age is found.", "The assignment direction is reversed inside the comparison, so the selected tuple does not become the oldest."),
    RefactoryRecord(4, "wrong_4_007.py", "Index Error", "list_indexing", "Check whether deleting an element changes the indexes still used in the nested loop.", "The code deletes from lst while continuing to use indexes from the old list length."),
    RefactoryRecord(4, "wrong_4_008.py", "Logic Error", "algorithm_logic", "Trace the inserted tuple after deletion and reconstruction of the list.", "The list reconstruction duplicates selected tuples instead of producing a full sorted order."),
    RefactoryRecord(4, "wrong_4_009.py", "Logic Error", "algorithm_logic", "Check whether one pass of moving an item is enough to sort all tuples.", "The algorithm stops or moves values in a way that leaves some ages out of descending order."),
    RefactoryRecord(4, "wrong_4_010.py", "Logic Error", "algorithm_logic", "Trace the item selected as this and the splice positions used to rebuild the list.", "The algorithm compares and inserts around the wrong current element, leaving the list unsorted."),
    RefactoryRecord(4, "wrong_4_011.py", "Name Error", "name_undefined_variable", "Check whether largest_tup is assigned before it is removed.", "For a one-element list, largest_tup is never assigned before lst.remove(largest_tup)."),
    RefactoryRecord(5, "wrong_5_001.py", "Loop Boundary Error", "loop_boundary_off_by_one", "Check whether the loop should run while k is greater than zero or greater than or equal to zero.", "The loop condition k >= 0 selects one extra item."),
    RefactoryRecord(5, "wrong_5_002.py", "Name Error", "name_undefined_variable", "Check the variable used in the comparison inside the for loop.", "The loop variable is elements, but the comparison uses element."),
    RefactoryRecord(5, "wrong_5_003.py", "Logic Error", "algorithm_logic", "Check whether the slice length uses the parameter k or a hard-coded number.", "The function always returns tmp[:5], so it fails when k is not 5."),
    RefactoryRecord(5, "wrong_5_004.py", "Name Error", "name_undefined_variable", "Check whether the comparison variable matches the loop variable.", "The code uses ele in the comparison, but only element is defined."),
    RefactoryRecord(5, "wrong_5_005.py", "Logic Error", "algorithm_logic", "Check whether the code removes and appends the largest value it found.", "The code tracks biggest but removes/appends element, which is just the final loop value."),
    RefactoryRecord(5, "wrong_5_006.py", "Loop Boundary Error", "loop_boundary_off_by_one", "Check the stopping condition when k is zero.", "The loop can still run through the whole list when k is 0 because the break condition is never reached."),
    RefactoryRecord(5, "wrong_5_007.py", "Value Error", "type_operation", "Check whether the value removed from lst1 actually exists in lst1.", "The algorithm mixes values from lst and lst1, then tries to remove a value that is not present."),
    RefactoryRecord(5, "wrong_5_008.py", "Loop Boundary Error", "loop_boundary_off_by_one", "Check the final slice length against the required number k.", "The return expression uses k + 1, so it produces one extra result."),
    RefactoryRecord(5, "wrong_5_009.py", "Name Error", "name_undefined_variable", "Check whether sort_list and sort_lst refer to the same list variable.", "The code initialises sort_list but appends to sort_lst."),
    RefactoryRecord(5, "wrong_5_010.py", "Logic Error", "algorithm_logic", "Check whether the number of removed smallest values should be k or len(lst) - k.", "The loop removes k smallest values, leaving too few values to return for top_k."),
    RefactoryRecord(5, "wrong_5_011.py", "Type Error", "type_operation", "Check whether the helper sort_age expects tuples while top_k passes integers.", "The helper indexes i[1], but top_k passes a list of integers."),
]

HAND_CRAFTED_BOUNDARY_RECORDS = [
    HandCraftedRecord(
        sample_id="boundary-syntax-missing-colon",
        ground_truth_category="Syntax Error",
        taxonomy_group="syntax_indentation",
        problem_statement="Print the integers from 1 to 3, one number per line.",
        lecture_objective="Write a for loop with correct Python syntax.",
        student_code="for i in range(1, 4)\n    print(i)\n",
        expected_output="1\n2\n3\n",
        expected_feedback_focus="Check the punctuation required at the end of a for statement.",
        annotation_note="Designed boundary case: the code cannot parse because the for statement is missing a colon.",
    ),
    HandCraftedRecord(
        sample_id="boundary-indentation-missing-block",
        ground_truth_category="Indentation Error",
        taxonomy_group="syntax_indentation",
        problem_statement="Define a function named greet that prints Hello.",
        lecture_objective="Use indentation to mark the body of a Python function.",
        student_code="def greet():\nprint('Hello')\ngreet()\n",
        expected_output="Hello\n",
        expected_feedback_focus="Check which line belongs inside the function body.",
        annotation_note="Designed boundary case: the function body is not indented.",
    ),
    HandCraftedRecord(
        sample_id="boundary-timeout-infinite-loop",
        ground_truth_category="Timeout",
        taxonomy_group="timeout_infinite_loop",
        problem_statement="Print Done once and stop.",
        lecture_objective="Write loop conditions that eventually terminate.",
        student_code="while True:\n    pass\nprint('Done')\n",
        expected_output="Done\n",
        expected_feedback_focus="Check whether the loop condition can ever become false.",
        annotation_note="Designed boundary case: the program never terminates and should be handled by the sandbox timeout.",
    ),
    HandCraftedRecord(
        sample_id="boundary-input-missing-line",
        ground_truth_category="Input Error",
        taxonomy_group="input_handling",
        problem_statement="Read a name and an age, then print them on one line.",
        lecture_objective="Match the number of input() calls to the available sample input.",
        student_code="name = input()\nage = input()\nprint(name, age)\n",
        sample_input="Lu\n",
        expected_output="Lu 20\n",
        expected_feedback_focus="Count how many input() calls the program reaches compared with the sample input.",
        annotation_note="Designed boundary case: the second input() call receives no line and raises EOFError.",
    ),
    HandCraftedRecord(
        sample_id="boundary-value-invalid-int",
        ground_truth_category="Value Error",
        taxonomy_group="input_handling",
        problem_statement="Read an integer age and print the age next year.",
        lecture_objective="Convert numeric input only after considering the input format.",
        student_code="age = int(input())\nprint(age + 1)\n",
        sample_input="twenty\n",
        expected_output="21\n",
        expected_feedback_focus="Check whether the sample input can be converted with int().",
        annotation_note="Designed boundary case: int() receives a non-numeric string.",
    ),
    HandCraftedRecord(
        sample_id="boundary-output-format-strict",
        ground_truth_category="Output Format Error",
        taxonomy_group="output_formatting",
        problem_statement="Print exactly: Hello, Lu!",
        lecture_objective="Follow exact output formatting when the task requires strict matching.",
        student_code="print('hello lu')\n",
        expected_output="Hello, Lu!\n",
        expected_feedback_focus="Compare capitalization, comma, spacing, and punctuation with the expected output.",
        annotation_note="Designed boundary case: the code runs but strict output formatting is wrong.",
        comparison_mode=COMPARISON_MODE_STRICT,
    ),
    HandCraftedRecord(
        sample_id="boundary-condition-wrong-branch",
        ground_truth_category="Condition Error",
        taxonomy_group="conditional_boundary",
        problem_statement="Read a score and print Pass when the score is at least 50, otherwise print Fail.",
        lecture_objective="Use if/else conditions that match the problem boundary.",
        student_code="score = int(input())\nif score > 50:\n    print('Pass')\nelse:\n    print('Fail')\n",
        sample_input="50\n",
        expected_output="Pass\n",
        expected_feedback_focus="Check whether the pass boundary includes exactly 50.",
        annotation_note="Designed boundary case: the condition uses > instead of >= at the decision boundary.",
    ),
    HandCraftedRecord(
        sample_id="boundary-loop-off-by-one",
        ground_truth_category="Loop Boundary Error",
        taxonomy_group="loop_boundary_off_by_one",
        problem_statement="Read n and print the sum from 1 to n inclusive.",
        lecture_objective="Choose range boundaries that include the final value when required.",
        student_code="n = int(input())\ntotal = 0\nfor i in range(1, n):\n    total += i\nprint(total)\n",
        sample_input="5\n",
        expected_output="15\n",
        expected_feedback_focus="Check whether range() includes n itself.",
        annotation_note="Designed boundary case: range(1, n) stops before the required final value.",
    ),
    HandCraftedRecord(
        sample_id="boundary-module-import-misspelled",
        ground_truth_category="Module Import Error",
        taxonomy_group="module_import",
        problem_statement="Use the math module to print the square root of 9.",
        lecture_objective="Import standard library modules with the correct module name.",
        student_code="import maths\nprint(maths.sqrt(9))\n",
        expected_output="3.0\n",
        expected_feedback_focus="Check the exact module name being imported.",
        annotation_note="Designed boundary case: a misspelled import raises ModuleNotFoundError.",
    ),
    HandCraftedRecord(
        sample_id="boundary-type-string-int-concat",
        ground_truth_category="Type Error",
        taxonomy_group="type_operation",
        problem_statement="Print the label Total: followed by the number 5.",
        lecture_objective="Convert values or use comma-separated print arguments when mixing strings and numbers.",
        student_code="print('Total: ' + 5)\n",
        expected_output="Total: 5\n",
        expected_feedback_focus="Check the types on both sides of the + operator.",
        annotation_note="Designed boundary case: string concatenation is attempted with an integer.",
    ),
    HandCraftedRecord(
        sample_id="boundary-function-print-not-return",
        ground_truth_category="Function Error",
        taxonomy_group="function_return",
        problem_statement="Define square(n) so that it returns n multiplied by itself.",
        lecture_objective="Distinguish printing inside a function from returning a value to the caller.",
        student_code="def square(n):\n    print(n * n)\n",
        expected_output="9\n",
        test_harness="print(square(3))\n",
        expected_feedback_focus="Check whether the function returns a value or only prints inside the function.",
        annotation_note="Designed boundary case: the function prints 9, then the harness prints None because no value is returned.",
    ),
    HandCraftedRecord(
        sample_id="boundary-index-empty-list",
        ground_truth_category="Index Error",
        taxonomy_group="list_indexing",
        problem_statement="Print the first number in the list only when the list is not empty.",
        lecture_objective="Check list length before accessing an index.",
        student_code="numbers = []\nprint(numbers[0])\n",
        expected_output="No numbers\n",
        expected_feedback_focus="Check whether index 0 exists before reading it.",
        annotation_note="Designed boundary case: the code reads the first item of an empty list.",
    ),
]

REQUIRED_SAMPLE_FIELDS = [
    "sample_id",
    "sample_origin",
    "source_dataset",
    "source_record_path",
    "source_question_path",
    "source_test_input_path",
    "source_test_output_path",
    "source_citations",
    "source_basis",
    "annotation_method",
    "annotation_note",
    "taxonomy_group",
    "problem_statement",
    "lecture_objective",
    "support_code",
    "student_code",
    "sample_input",
    "expected_output",
    "actual_output",
    "actual_stderr",
    "test_harness",
    "comparison_mode",
    "output_comparison_status",
    "ground_truth_category",
    "expected_feedback_focus",
    "requires_input",
    "requires_test_harness",
    "expected_timeout",
    "expected_execution_status",
]


def _natural_key(path):
    return [int(part) if part.isdigit() else part for part in path.stem.split("_")]


def _read_text(path):
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def _question_dir(refactory_data_dir, question_id):
    return Path(refactory_data_dir) / f"question_{question_id}"


def _support_code(question_dir):
    path = question_dir / "code" / "global.py"
    if not path.exists():
        return ""
    return _read_text(path).strip()


def _first_failing_case(question_dir, runnable_code, timeout):
    ans_dir = question_dir / "ans"
    input_paths = sorted(ans_dir.glob("input_*.txt"), key=_natural_key)

    for input_path in input_paths:
        case_id = input_path.stem.split("_", 1)[1]
        output_path = ans_dir / f"output_{case_id}.txt"
        expression = _read_text(input_path).strip()
        expected_output = _read_text(output_path)
        test_harness = f"print({expression})\n"
        result = run_python_code(runnable_code, timeout=timeout, test_harness=test_harness)
        comparison_status = compare_outputs(
            result["stdout"],
            expected_output,
            result["execution_status"],
            mode=COMPARISON_MODE_NORMALIZED,
        )

        if comparison_status in {MISMATCH, EXECUTION_ERROR, TIMEOUT}:
            return {
                "test_case_id": case_id,
                "source_test_input_path": str(
                    Path("data")
                    / question_dir.name
                    / "ans"
                    / f"input_{case_id}.txt"
                ),
                "source_test_output_path": str(
                    Path("data")
                    / question_dir.name
                    / "ans"
                    / f"output_{case_id}.txt"
                ),
                "test_harness": test_harness,
                "expected_output": expected_output,
                "actual_output": result["stdout"],
                "actual_stderr": result["stderr"],
                "output_comparison_status": comparison_status,
                "expected_execution_status": result["execution_status"],
                "expected_timeout": result["timed_out"],
            }

    raise ValueError(f"No failing test case found for {question_dir.name}")


def _build_hand_crafted_sample(record, timeout):
    runnable_code = "\n\n".join(
        part for part in [record.support_code, record.student_code] if part.strip()
    )
    result = run_python_code(
        runnable_code,
        sample_input=record.sample_input,
        timeout=timeout,
        test_harness=record.test_harness,
    )
    comparison_status = compare_outputs(
        result["stdout"],
        record.expected_output,
        result["execution_status"],
        mode=record.comparison_mode,
    )

    return {
        "sample_id": record.sample_id,
        "sample_origin": SAMPLE_ORIGIN_HAND_CRAFTED,
        "source_dataset": "FYP supplemental boundary samples",
        "source_record_path": record.relative_code_path,
        "source_question_path": f"hand_crafted/{record.sample_id}_question.md",
        "source_test_input_path": f"hand_crafted/{record.sample_id}_input.txt",
        "source_test_output_path": f"hand_crafted/{record.sample_id}_expected_output.txt",
        "source_citations": [
            "FYP Day 10 coverage-gap analysis after selecting Refactory records.",
            "Supervisor requirement: evaluate common beginner mistakes beyond code feedback only.",
        ],
        "source_basis": (
            "Supplemental hand-crafted boundary case. This is not a real student "
            "submission and must not be used as frequency evidence; it is included "
            "to test system handling of error types not covered by the selected "
            "Refactory subset."
        ),
        "annotation_method": (
            "FYP designed boundary-case annotation based on the intended runtime "
            "failure or output-comparison failure."
        ),
        "annotation_note": record.annotation_note,
        "taxonomy_group": record.taxonomy_group,
        "problem_statement": record.problem_statement,
        "lecture_objective": record.lecture_objective,
        "support_code": record.support_code,
        "student_code": record.student_code,
        "sample_input": record.sample_input,
        "expected_output": record.expected_output,
        "actual_output": result["stdout"],
        "actual_stderr": result["stderr"],
        "test_harness": record.test_harness,
        "comparison_mode": record.comparison_mode,
        "output_comparison_status": comparison_status,
        "ground_truth_category": record.ground_truth_category,
        "expected_feedback_focus": record.expected_feedback_focus,
        "requires_input": bool(record.sample_input),
        "requires_test_harness": bool(record.test_harness.strip()),
        "expected_timeout": result["timed_out"],
        "expected_execution_status": result["execution_status"],
    }


def build_evaluation_samples(
    refactory_data_dir=None,
    *,
    records=None,
    timeout=1,
    include_hand_crafted=True,
):
    data_dir = Path(refactory_data_dir or DEFAULT_REFACTORY_DATA_DIR)
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Refactory data directory not found: {data_dir}. "
            "Download/extract https://github.com/githubhuyang/refactory/blob/master/data.zip "
            "or pass --refactory-data-dir."
        )

    samples = []
    selected_records = records or SELECTED_REFACTORY_RECORDS
    for record in selected_records:
        question_dir = _question_dir(data_dir, record.question_id)
        code_path = question_dir / "code" / "wrong" / record.filename
        description_path = question_dir / "description.txt"
        if not code_path.exists():
            raise FileNotFoundError(f"Missing Refactory record: {code_path}")

        support_code = _support_code(question_dir)
        student_code = _read_text(code_path)
        runnable_code = "\n\n".join(part for part in [support_code, student_code] if part.strip())
        failing_case = _first_failing_case(question_dir, runnable_code, timeout)
        source_citations = [
            REFACTORY_SOURCE_METADATA["user_reference"],
            REFACTORY_SOURCE_METADATA["original_paper"],
            REFACTORY_SOURCE_METADATA["dataset_repository"],
        ]

        samples.append(
            {
                "sample_id": record.sample_id,
                "sample_origin": SAMPLE_ORIGIN_REFACTORY,
                "source_dataset": REFACTORY_SOURCE_METADATA["dataset_name"],
                "source_record_path": record.relative_code_path,
                "source_question_path": f"data/question_{record.question_id}/description.txt",
                "source_test_input_path": failing_case["source_test_input_path"],
                "source_test_output_path": failing_case["source_test_output_path"],
                "source_citations": source_citations,
                "source_basis": REFACTORY_SOURCE_METADATA["original_paper_dataset_note"],
                "annotation_method": (
                    "FYP manual taxonomy annotation based on the real source code, "
                    "the first failing Refactory test case, runtime status, and output comparison."
                ),
                "annotation_note": record.annotation_note,
                "taxonomy_group": record.taxonomy_group,
                "problem_statement": _read_text(description_path).strip(),
                "lecture_objective": QUESTION_OBJECTIVES[record.question_id],
                "support_code": support_code + ("\n" if support_code else ""),
                "student_code": student_code,
                "sample_input": "",
                "expected_output": failing_case["expected_output"],
                "actual_output": failing_case["actual_output"],
                "actual_stderr": failing_case["actual_stderr"],
                "test_harness": failing_case["test_harness"],
                "comparison_mode": COMPARISON_MODE_NORMALIZED,
                "output_comparison_status": failing_case["output_comparison_status"],
                "ground_truth_category": record.ground_truth_category,
                "expected_feedback_focus": record.expected_feedback_focus,
                "requires_input": False,
                "requires_test_harness": True,
                "expected_timeout": failing_case["expected_timeout"],
                "expected_execution_status": failing_case["expected_execution_status"],
            }
        )

    if include_hand_crafted and records is None:
        samples.extend(
            _build_hand_crafted_sample(record, timeout)
            for record in HAND_CRAFTED_BOUNDARY_RECORDS
        )

    return samples


def validate_evaluation_samples(samples):
    errors = []
    seen_ids = set()
    for sample in samples:
        sample_id = sample.get("sample_id", "<missing sample_id>")

        if sample_id in seen_ids:
            errors.append(f"{sample_id}: duplicate sample_id")
        seen_ids.add(sample_id)

        for field in REQUIRED_SAMPLE_FIELDS:
            if field not in sample:
                errors.append(f"{sample_id}: missing {field}")

        sample_origin = sample.get("sample_origin")
        if sample_origin not in ALLOWED_SAMPLE_ORIGINS:
            errors.append(
                f"{sample_id}: sample_origin must be one of {sorted(ALLOWED_SAMPLE_ORIGINS)}"
            )

        if sample.get("ground_truth_category") not in ERROR_CATEGORIES:
            errors.append(f"{sample_id}: unknown ground_truth_category")

        if sample.get("taxonomy_group") not in TAXONOMY_BY_ID:
            errors.append(f"{sample_id}: unknown taxonomy_group")

        if sample_origin == SAMPLE_ORIGIN_REFACTORY and "code/wrong/wrong_" not in sample.get(
            "source_record_path",
            "",
        ):
            errors.append(
                f"{sample_id}: source_record_path must point to a Refactory wrong_*.py record"
            )

        if sample_origin == SAMPLE_ORIGIN_HAND_CRAFTED and not sample.get(
            "source_record_path",
            "",
        ).startswith("hand_crafted/"):
            errors.append(f"{sample_id}: hand-crafted samples must use a virtual hand_crafted path")

        if not sample.get("source_test_input_path", "").endswith(".txt"):
            errors.append(f"{sample_id}: missing source test input path")

        if not sample.get("source_test_output_path", "").endswith(".txt"):
            errors.append(f"{sample_id}: missing source test output path")

        if not str(sample.get("student_code", "")).strip():
            errors.append(f"{sample_id}: empty student_code")

        if sample_origin == SAMPLE_ORIGIN_REFACTORY and not str(
            sample.get("test_harness", "")
        ).strip():
            errors.append(f"{sample_id}: empty test_harness")

        if sample.get("output_comparison_status") not in {MISMATCH, EXECUTION_ERROR, TIMEOUT}:
            errors.append(f"{sample_id}: selected record must fail the stored Refactory test")

    return errors


def summarise_evaluation_samples(samples):
    def sample_question_key(sample):
        path = sample["source_record_path"]
        if sample["sample_origin"] == SAMPLE_ORIGIN_REFACTORY:
            return path.split("/")[1]
        return "hand_crafted_boundary"

    return {
        "total": len(samples),
        "origin_counts": dict(Counter(sample["sample_origin"] for sample in samples)),
        "group_counts": dict(Counter(sample["taxonomy_group"] for sample in samples)),
        "category_counts": dict(Counter(sample["ground_truth_category"] for sample in samples)),
        "question_counts": dict(
            Counter(sample_question_key(sample) for sample in samples)
        ),
        "runtime_status_counts": dict(
            Counter(sample["expected_execution_status"] for sample in samples)
        ),
        "comparison_counts": dict(
            Counter(sample["output_comparison_status"] for sample in samples)
        ),
        "real_refactory_records": sum(
            1 for sample in samples if sample["sample_origin"] == SAMPLE_ORIGIN_REFACTORY
        ),
        "hand_crafted_boundary_cases": sum(
            1 for sample in samples if sample["sample_origin"] == SAMPLE_ORIGIN_HAND_CRAFTED
        ),
        "requires_test_harness_count": sum(
            1 for sample in samples if sample["requires_test_harness"]
        ),
        "requires_input_count": sum(1 for sample in samples if sample["requires_input"]),
        "expected_timeout_count": sum(
            1 for sample in samples if sample["expected_timeout"]
        ),
    }


def render_source_report(samples):
    summary = summarise_evaluation_samples(samples)
    lines = [
        "# FYP Evaluation Dataset Sources",
        "",
        "## Source Chain",
        "",
        f"- User reference: {REFACTORY_SOURCE_METADATA['user_reference']}",
        f"- Original paper: {REFACTORY_SOURCE_METADATA['original_paper']}",
        f"- Repository: {REFACTORY_SOURCE_METADATA['dataset_repository']}",
        f"- Archive: {REFACTORY_SOURCE_METADATA['dataset_archive']}",
        f"- Dataset note: {REFACTORY_SOURCE_METADATA['repository_dataset_note']}",
        f"- License note: {REFACTORY_SOURCE_METADATA['license']}",
        "",
        "## Important Provenance Boundary",
        "",
        (
            "Most student programs in this export are copied from the real Refactory "
            "wrong_*.py submissions. The ground_truth_category values are not labels "
            "provided by Refactory; they are FYP manual annotations based on code "
            "inspection, the first failing test case, runtime status, and output comparison. "
            "The hand-crafted boundary cases are explicitly marked as supplemental system "
            "tests and must not be reported as real student submissions."
        ),
        "",
        "## Summary",
        "",
        f"- Total selected records: {summary['total']}",
        f"- Real Refactory records: {summary['real_refactory_records']}",
        f"- Hand-crafted boundary cases: {summary['hand_crafted_boundary_cases']}",
        f"- Questions: {json.dumps(summary['question_counts'], sort_keys=True)}",
        f"- Origins: {json.dumps(summary['origin_counts'], sort_keys=True)}",
        f"- Ground-truth categories: {json.dumps(summary['category_counts'], sort_keys=True)}",
        f"- Runtime statuses: {json.dumps(summary['runtime_status_counts'], sort_keys=True)}",
        f"- Requires input: {summary['requires_input_count']}",
        f"- Expected timeout cases: {summary['expected_timeout_count']}",
        "",
        "## Supplemental Boundary Samples",
        "",
        (
            "These records were added after the Refactory export revealed coverage gaps: "
            "the selected real records do not include syntax errors, indentation errors, "
            "timeouts, or stdin/input failures. They are intentionally separated through "
            f"`sample_origin={SAMPLE_ORIGIN_HAND_CRAFTED}`."
        ),
        "",
        "## Selected Records",
        "",
        "| Sample ID | Origin | Source record | Failing test input | Failing test output | Ground truth |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for sample in samples:
        lines.append(
            "| {sample_id} | {origin} | {record} | {input_path} | {output_path} | {category} |".format(
                sample_id=sample["sample_id"],
                origin=sample["sample_origin"],
                record=sample["source_record_path"],
                input_path=sample["source_test_input_path"],
                output_path=sample["source_test_output_path"],
                category=sample["ground_truth_category"],
            )
        )

    return "\n".join(lines) + "\n"


def export_evaluation_files(
    refactory_data_dir=None,
    *,
    output_dir=None,
    timeout=1,
    include_hand_crafted=True,
):
    samples = build_evaluation_samples(
        refactory_data_dir,
        timeout=timeout,
        include_hand_crafted=include_hand_crafted,
    )
    errors = validate_evaluation_samples(samples)
    if errors:
        raise ValueError("\n".join(errors))

    base_dir = Path(output_dir or settings.BASE_DIR)
    dataset_path = base_dir / EVALUATION_DATASET_FILENAME
    source_report_path = base_dir / EVALUATION_SOURCE_REPORT_FILENAME

    payload = {
        "metadata": REFACTORY_SOURCE_METADATA,
        "taxonomy": EVALUATION_TAXONOMY,
        "summary": summarise_evaluation_samples(samples),
        "samples": samples,
    }
    dataset_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    source_report_path.write_text(render_source_report(samples), encoding="utf-8")
    return dataset_path, source_report_path, samples
