import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from feedback_app.feedback_schema import FEEDBACK_SCHEMA_VERSION
from feedback_app.models import CodeFeedbackRecord, Question
from feedback_app.output_comparison import COMPARISON_MODE_NORMALIZED, COMPARISON_MODE_STRICT
from feedback_app.taxonomy import (
    PECI_ERROR_TAXONOMY,
    TOPIC_TAXONOMY,
    peci_error_display,
    peci_error_label,
    serialize_topic_tags,
)


DEMO_USERS = [
    {
        "username": "student1",
        "password": "student123",
        "email": "student1@example.com",
        "first_name": "Student 1",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "username": "student2",
        "password": "student123",
        "email": "student2@example.com",
        "first_name": "Student 2",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "username": "instructor",
        "password": "instructor123",
        "email": "instructor@example.com",
        "first_name": "Instructor",
        "is_staff": True,
        "is_superuser": True,
    },
]


DEMO_QUESTIONS = [
    {
        "title": "Sum from 1 to 10",
        "problem_statement": "Write a Python program that prints the sum of integers from 1 to 10.",
        "lecture_objective": "Use for loops, range boundaries, accumulator variables, and print output.",
        "sample_input": "",
        "expected_output": "55\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "variables_assignment,iteration_range",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Greeting with input",
        "problem_statement": "Read a name from input and print Hello followed by the name.",
        "lecture_objective": "Use input(), variables, string construction, and print output.",
        "sample_input": "Ada\n",
        "expected_output": "Hello Ada\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "variables_assignment,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Even or odd",
        "problem_statement": "Read an integer and print Even if it is divisible by 2; otherwise print Odd.",
        "lecture_objective": "Use input conversion, modulo, conditionals, and Boolean expressions.",
        "sample_input": "7\n",
        "expected_output": "Odd\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "expressions_operators,conditionals_boolean,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Average of a list",
        "problem_statement": "Given the list [1, 2, 3, 4, 5], print the average value.",
        "lecture_objective": "Use list values, sum(), len(), arithmetic operators, and float output.",
        "sample_input": "",
        "expected_output": "3.0\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "expressions_operators,collections_indexing",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Function square",
        "problem_statement": "Define a function square(n) that returns n multiplied by itself.",
        "lecture_objective": "Use function definition, parameters, return values, and local scope.",
        "sample_input": "",
        "expected_output": "25\n",
        "test_harness": "\nprint(square(5))\n",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Beginner",
        "topic_tags": "expressions_operators,functions_returns",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Rectangle helper functions",
        "problem_statement": "Define area(width, height) and perimeter(width, height) for a rectangle.",
        "lecture_objective": "Use multiple function definitions, parameters, return values, and arithmetic expressions.",
        "sample_input": "",
        "expected_output": "12\n14\n",
        "test_harness": "\nprint(area(3, 4))\nprint(perimeter(3, 4))\n",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "expressions_operators,functions_returns",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Celsius to Fahrenheit",
        "problem_statement": "Read a Celsius temperature and print its Fahrenheit value using C * 9 / 5 + 32.",
        "lecture_objective": "Use input conversion, variables, arithmetic expressions, and print output.",
        "sample_input": "0\n",
        "expected_output": "32.0\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "variables_assignment,expressions_operators,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Positive, zero, or negative",
        "problem_statement": "Read an integer and print Positive, Zero, or Negative.",
        "lecture_objective": "Use input conversion and an if/elif/else decision.",
        "sample_input": "-3\n",
        "expected_output": "Negative\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "conditionals_boolean,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Countdown from three",
        "problem_statement": "Use a loop to print 3, 2, and 1 on separate lines, then print Go!.",
        "lecture_objective": "Use loop boundaries, statement order, and output sequencing.",
        "sample_input": "",
        "expected_output": "3\n2\n1\nGo!\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Beginner",
        "topic_tags": "program_structure,iteration_range,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Five multiples",
        "problem_statement": "Read an integer n and print its first five positive multiples on one line separated by spaces.",
        "lecture_objective": "Use a loop, range, multiplication, and controlled output formatting.",
        "sample_input": "4\n",
        "expected_output": "4 8 12 16 20\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Beginner",
        "topic_tags": "expressions_operators,iteration_range,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Largest of three numbers",
        "problem_statement": "Read three integers and print the largest value.",
        "lecture_objective": "Store input values and use comparisons and conditional branches.",
        "sample_input": "3\n9\n5\n",
        "expected_output": "9\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Beginner",
        "topic_tags": "variables_assignment,expressions_operators,conditionals_boolean,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Count vowels",
        "problem_statement": "Read a word and print how many vowels it contains. Treat upper- and lower-case vowels equally.",
        "lecture_objective": "Traverse a string, use membership tests, and update a counter.",
        "sample_input": "Education\n",
        "expected_output": "5\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Intermediate",
        "topic_tags": "conditionals_boolean,iteration_range,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Reverse a word",
        "problem_statement": "Read a word and print its characters in reverse order.",
        "lecture_objective": "Use string indexing or traversal to construct reversed output.",
        "sample_input": "Python\n",
        "expected_output": "nohtyP\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Intermediate",
        "topic_tags": "strings_io,collections_indexing",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Maximum list value",
        "problem_statement": "Given [4, 1, 9, 3], find and print the largest value without changing the list.",
        "lecture_objective": "Traverse a list, compare values, and update a tracking variable.",
        "sample_input": "",
        "expected_output": "9\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Intermediate",
        "topic_tags": "variables_assignment,conditionals_boolean,iteration_range,collections_indexing",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Count even list values",
        "problem_statement": "Given [1, 2, 4, 7, 8], print the number of even values.",
        "lecture_objective": "Traverse a list, test divisibility, and update a counter.",
        "sample_input": "",
        "expected_output": "3\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Intermediate",
        "topic_tags": "expressions_operators,conditionals_boolean,iteration_range,collections_indexing",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Safe division function",
        "problem_statement": "Define safe_divide(a, b). Return a / b when b is non-zero; otherwise return the text Cannot divide by zero.",
        "lecture_objective": "Combine a function return value, division, and a zero-denominator condition.",
        "sample_input": "",
        "expected_output": "5.0\nCannot divide by zero\n",
        "test_harness": "\nprint(safe_divide(10, 2))\nprint(safe_divide(5, 0))\n",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Intermediate",
        "topic_tags": "expressions_operators,conditionals_boolean,functions_returns",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "First and last list items",
        "problem_statement": "Given [10, 20, 30, 40], print the first item and then the last item on separate lines.",
        "lecture_objective": "Use positive and negative list indices.",
        "sample_input": "",
        "expected_output": "10\n40\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Beginner",
        "topic_tags": "program_structure,collections_indexing",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Pass or fail message",
        "problem_statement": "Read a mark and print Pass when it is at least 50; otherwise print Fail.",
        "lecture_objective": "Use input conversion, comparison, branch structure, and exact output.",
        "sample_input": "76\n",
        "expected_output": "Pass\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Beginner",
        "topic_tags": "program_structure,conditionals_boolean,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Running totals function",
        "problem_statement": "Define running_totals(numbers) that returns a list containing the cumulative total after each input value.",
        "lecture_objective": "Use a function, accumulator loop, list traversal, and returned collection.",
        "sample_input": "",
        "expected_output": "[1, 3, 6, 10]\n",
        "test_harness": "\nprint(running_totals([1, 2, 3, 4]))\n",
        "comparison_mode": COMPARISON_MODE_NORMALIZED,
        "difficulty": "Intermediate",
        "topic_tags": "variables_assignment,iteration_range,functions_returns,collections_indexing",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
    {
        "title": "Menu choice",
        "problem_statement": "Read 1, 2, or 3 and print Start, Settings, or Quit. Print Invalid choice for any other value.",
        "lecture_objective": "Organise a multi-branch program with input conversion and exact messages.",
        "sample_input": "2\n",
        "expected_output": "Settings\n",
        "test_harness": "",
        "comparison_mode": COMPARISON_MODE_STRICT,
        "difficulty": "Beginner",
        "topic_tags": "program_structure,conditionals_boolean,strings_io",
        "default_llm_provider": Question.PROVIDER_DEEPSEEK,
        "is_active": True,
    },
]


DEMO_HISTORY = [
    {
        "trajectory_id": "demo-student1-sum",
        "username": "student1",
        "question_title": "Sum from 1 to 10",
        "concept_reference": "Iteration and Range",
        "start_days_ago": 20,
        "attempts": [
            {
                "attempt_number": 1,
                "code": "total = 0\nfor i in range(1, 11)\n    total += i\nprint(total)\n",
                "error_type": "Missing colon, comma or operator",
                "misconception": "The student has not yet applied the colon required to open a Python loop block.",
                "output": "",
                "solved": False,
                "execution_status": "syntax_error",
                "execution_stderr": "SyntaxError: expected ':'",
                "comparison": "execution_error",
                "classification_outcome": "peci_error",
                "peci_error_code": "S",
                "feedback": "The loop cannot run because the for statement is missing required punctuation.",
                "next_step": "Check the end of the for line before debugging the calculation.",
            },
            {
                "attempt_number": 2,
                "code": "total = 0\nfor i in range(1, 11):\n    total += i\n    print(total)\n",
                "error_type": "Incorrect structure",
                "misconception": "The student treats intermediate loop output as the single final answer required by the question.",
                "output": "1\n3\n6\n10\n15\n21\n28\n36\n45\n55\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "L",
                "feedback": "The accumulator reaches 55, but print is inside the loop and produces ten lines.",
                "next_step": "Decide whether printing belongs inside or after the repeated block.",
            },
            {
                "attempt_number": 3,
                "code": "total = 0\nfor i in range(1, 11):\n    total =+ i\nprint(total)\n",
                "error_type": "Misspelled operators",
                "misconception": "The student confuses the accumulate operator += with the valid but different assignment expression =+.",
                "output": "10\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "Q",
                "feedback": "The loop now prints once, but the update operator replaces total instead of accumulating it.",
                "next_step": "Compare =+ with the operator used to add into an existing value.",
            },
            {
                "attempt_number": 4,
                "code": "total = 0\nfor i in range(1, 10):\n    total += i\nprint(total)\n",
                "error_type": "Outside PECI Scope: off-by-one loop boundary",
                "misconception": "The student does not yet recognise that the stop value of range is excluded.",
                "output": "45\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "outside_peci_scope",
                "peci_error_code": "",
                "feedback": "The structure and accumulation are correct, but range(1, 10) stops before 10.",
                "next_step": "List the values produced by range and adjust its excluded stop value.",
            },
            {
                "attempt_number": 5,
                "code": "total = 0\nfor i in range(1, 11):\n    total += i\nprint(total)\n",
                "error_type": "No Error",
                "misconception": "No remaining misconception is supported by the question and runtime evidence.",
                "output": "55\n",
                "solved": True,
                "comparison": "exact_match",
                "classification_outcome": "no_error",
                "peci_error_code": "",
                "feedback": "The loop includes 10, accumulates every value, and prints one matching result.",
                "next_step": "Try generalising the same pattern to a user-provided upper limit.",
            },
        ],
    },
    {
        "trajectory_id": "demo-student1-greeting",
        "username": "student1",
        "question_title": "Greeting with input",
        "concept_reference": "Strings, Input, and Output",
        "start_days_ago": 15,
        "attempts": [
            {
                "attempt_number": 1,
                "code": "name = input()\nprint('Hello + name)\n",
                "error_type": "Unterminated string literal",
                "misconception": "The student has not paired the quotation marks that delimit the greeting string.",
                "output": "",
                "solved": False,
                "execution_status": "syntax_error",
                "execution_stderr": "SyntaxError: unterminated string literal",
                "comparison": "execution_error",
                "classification_outcome": "peci_error",
                "peci_error_code": "R",
                "feedback": "Python cannot parse the print expression because the string is not closed.",
                "next_step": "Match the opening and closing quotation marks before combining values.",
            },
            {
                "attempt_number": 2,
                "code": "name = input()\nprint('Hello ' + user_name)\n",
                "error_type": "Misspelled names or keywords",
                "misconception": "The student assumes user_name refers to the value stored under the different identifier name.",
                "output": "",
                "solved": False,
                "execution_status": "name_error",
                "execution_stderr": "NameError: name 'user_name' is not defined",
                "comparison": "execution_error",
                "classification_outcome": "peci_error",
                "peci_error_code": "N",
                "feedback": "The input is stored in name, but the print statement refers to user_name.",
                "next_step": "Use one consistent identifier for the stored input value.",
            },
            {
                "attempt_number": 3,
                "code": "name = input()\nprint('Hello' + name)\n",
                "error_type": "Extra or missing spaces",
                "misconception": "The student treats whitespace in the required output as optional.",
                "output": "HelloAda\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "F",
                "feedback": "The input is used correctly, but the required space after Hello is missing.",
                "next_step": "Compare each visible character with the expected output.",
            },
            {
                "attempt_number": 4,
                "code": "name = input()\nprint('Hello Ada')\n",
                "error_type": "Literal values instead of variables",
                "misconception": "The student hard-codes the sample name instead of using the value read from input.",
                "output": "Hello Ada\n",
                "solved": False,
                "comparison": "exact_match",
                "classification_outcome": "peci_error",
                "peci_error_code": "E",
                "feedback": "This passes the Ada sample, but it ignores the value stored in name.",
                "next_step": "Use the input variable so the program also works for another name.",
            },
            {
                "attempt_number": 5,
                "code": "name = input()\nprint('Hello ' + name)\n",
                "error_type": "No Error",
                "misconception": "No remaining misconception is supported by the question and runtime evidence.",
                "output": "Hello Ada\n",
                "solved": True,
                "comparison": "exact_match",
                "classification_outcome": "no_error",
                "peci_error_code": "",
                "feedback": "The program now uses the input variable and matches the required greeting format.",
                "next_step": "Test a second name to confirm the output is not tied to the sample.",
            },
        ],
    },
    {
        "trajectory_id": "demo-student2-even",
        "username": "student2",
        "question_title": "Even or odd",
        "concept_reference": "Conditionals and Boolean Logic",
        "start_days_ago": 20,
        "attempts": [
            {
                "attempt_number": 1,
                "code": "n = input()\nif n % 2 == 0:\n    print('Even')\nelse:\n    print('Odd')\n",
                "error_type": "Division and modulo",
                "misconception": "The student applies modulo directly to the text returned by input without integer conversion.",
                "output": "",
                "solved": False,
                "execution_status": "type_error",
                "execution_stderr": "TypeError: not all arguments converted during string formatting",
                "comparison": "execution_error",
                "classification_outcome": "peci_error",
                "peci_error_code": "I",
                "feedback": "The modulo test receives text rather than an integer.",
                "next_step": "Convert the input value before applying an arithmetic operator.",
            },
            {
                "attempt_number": 2,
                "code": "n = int(input())\nif n / 2 == 0:\n    print('Even')\nelse:\n    print('Odd')\n",
                "error_type": "Division and modulo",
                "misconception": "The student confuses division with the remainder operation needed to test divisibility.",
                "output": "Odd\n",
                "solved": False,
                "comparison": "exact_match",
                "classification_outcome": "peci_error",
                "peci_error_code": "I",
                "feedback": "The result happens to match for 7, but division does not test whether a remainder exists.",
                "next_step": "Test an even value and compare division with modulo.",
            },
            {
                "attempt_number": 3,
                "code": "n = int(input())\nif n % 2 != 0:\n    print('Even')\nelse:\n    print('Odd')\n",
                "error_type": "Misspelled operators",
                "misconception": "The student uses not-equal where equality is required for the Even branch.",
                "output": "Even\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "Q",
                "feedback": "Modulo is now appropriate, but the comparison sends odd values to the Even branch.",
                "next_step": "State the remainder that an even number should have, then choose the matching comparison.",
            },
            {
                "attempt_number": 4,
                "code": "n = int(input())\nprint('Odd')\n",
                "error_type": "Literal values instead of variables",
                "misconception": "The student hard-codes the sample result instead of making output depend on n.",
                "output": "Odd\n",
                "solved": False,
                "comparison": "exact_match",
                "classification_outcome": "peci_error",
                "peci_error_code": "E",
                "feedback": "The sample passes, but no condition uses the input value, so even inputs will fail.",
                "next_step": "Restore a condition whose result controls which label is printed.",
            },
            {
                "attempt_number": 5,
                "code": "n = int(input())\nif n % 2 == 0:\n    print('Even')\nelse:\n    print('Odd')\n",
                "error_type": "No Error",
                "misconception": "No remaining misconception is supported by the question and runtime evidence.",
                "output": "Odd\n",
                "solved": True,
                "comparison": "exact_match",
                "classification_outcome": "no_error",
                "peci_error_code": "",
                "feedback": "The input is converted and modulo now selects the correct branch.",
                "next_step": "Test one even and one odd value to confirm both branches.",
            },
        ],
    },
    {
        "trajectory_id": "demo-student2-average",
        "username": "student2",
        "question_title": "Average of a list",
        "concept_reference": "Collections and Indexing",
        "start_days_ago": 15,
        "attempts": [
            {
                "attempt_number": 1,
                "code": "numbers = [1, 2, 3, 4, 5]\nprint(sum(number) / len(numbers))\n",
                "error_type": "Misspelled names or keywords",
                "misconception": "The student treats number and numbers as the same identifier.",
                "output": "",
                "solved": False,
                "execution_status": "name_error",
                "execution_stderr": "NameError: name 'number' is not defined",
                "comparison": "execution_error",
                "classification_outcome": "peci_error",
                "peci_error_code": "N",
                "feedback": "The list is named numbers, but sum receives the undefined name number.",
                "next_step": "Use the same identifier wherever the list is referenced.",
            },
            {
                "attempt_number": 2,
                "code": "numbers = [1, 2, 3, 4, 5]\nprint(sum(numbers) / 4)\n",
                "error_type": "Literal values instead of variables",
                "misconception": "The student hard-codes a denominator rather than deriving the number of list elements.",
                "output": "3.75\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "E",
                "feedback": "The sum is correct, but 4 does not represent the list length.",
                "next_step": "Use information from the list to determine the denominator.",
            },
            {
                "attempt_number": 3,
                "code": "numbers = [1, 2, 3, 4, 5]\nprint(sum(numbers) // len(numbers))\n",
                "error_type": "Division and modulo",
                "misconception": "The student uses floor division even though the required average may contain a fractional part.",
                "output": "3\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "I",
                "feedback": "The denominator is now correct, but floor division removes fractional information.",
                "next_step": "Choose the division operator that preserves a numeric average.",
            },
            {
                "attempt_number": 4,
                "code": "numbers = [1, 2, 3, 4, 5]\nprint('Average:', sum(numbers) / len(numbers))\n",
                "error_type": "Extra or missing spaces",
                "misconception": "The student adds explanatory text even though the required output is only the numeric value.",
                "output": "Average: 3.0\n",
                "solved": False,
                "comparison": "mismatch",
                "classification_outcome": "peci_error",
                "peci_error_code": "F",
                "feedback": "The calculation is correct, but the extra label does not match the required output form.",
                "next_step": "Print only the value requested by the expected output.",
            },
            {
                "attempt_number": 5,
                "code": "numbers = [1, 2, 3, 4, 5]\nprint(sum(numbers) / len(numbers))\n",
                "error_type": "No Error",
                "misconception": "No remaining misconception is supported by the question and runtime evidence.",
                "output": "3.0\n",
                "solved": True,
                "comparison": "exact_match",
                "classification_outcome": "no_error",
                "peci_error_code": "",
                "feedback": "The code derives both the sum and item count and prints the required numeric average.",
                "next_step": "Try a list whose average is not an integer.",
            },
        ],
    },
]


def _trajectory_sample_id(trajectory, attempt):
    return f"{trajectory['trajectory_id']}-{attempt['attempt_number']:03d}"


def _validate_demo_trajectory(trajectory):
    attempts = trajectory["attempts"]
    attempt_numbers = [attempt["attempt_number"] for attempt in attempts]
    if attempt_numbers != [1, 2, 3, 4, 5]:
        raise CommandError(
            f"Trajectory {trajectory['trajectory_id']} must contain attempts 1-5 in order."
        )

    for attempt in attempts:
        expected_solved = attempt["classification_outcome"] == "no_error"
        if attempt["solved"] != expected_solved:
            raise CommandError(
                f"Trajectory {trajectory['trajectory_id']} attempt "
                f"{attempt['attempt_number']} has inconsistent solved metadata."
            )
        code = attempt["peci_error_code"]
        if code and code not in PECI_ERROR_TAXONOMY:
            raise CommandError(
                f"Trajectory {trajectory['trajectory_id']} uses unknown PECI code {code}."
            )


def _upsert_record(trajectory, attempt, users_by_username, questions_by_title):
    sample_id = _trajectory_sample_id(trajectory, attempt)
    existing = CodeFeedbackRecord.objects.filter(evaluation_sample_id=sample_id).first()
    user = users_by_username[trajectory["username"]]
    question = questions_by_title[trajectory["question_title"]]
    classification_outcome = attempt["classification_outcome"]
    peci_error_code = attempt["peci_error_code"]
    peci_label = peci_error_label(peci_error_code)
    outcome_labels = {
        "no_error": "No Error",
        "outside_peci_scope": "Outside PECI Scope",
        "unknown": "Unknown",
    }
    error_category = peci_error_display(peci_error_code) or outcome_labels.get(
        classification_outcome,
        "Unknown",
    )
    execution_status = attempt.get("execution_status", "success")
    execution_return_code = attempt.get("execution_return_code")
    if execution_return_code is None:
        execution_return_code = 0 if execution_status == "success" else 1
    feedback_level = attempt.get("feedback_level", "Level 2")
    confidence = attempt.get("confidence", "medium")
    raw_payload = {
        "trajectory_id": trajectory["trajectory_id"],
        "attempt_number": attempt["attempt_number"],
        "misconception": attempt["misconception"],
        "solved": attempt["solved"],
        "classification_outcome": classification_outcome,
        "peci_error_code": peci_error_code,
        "feedback_level": feedback_level,
        "concept_reference": trajectory["concept_reference"],
        "feedback": attempt["feedback"],
        "does_reveal_solution": False,
        "uses_runtime_evidence": True,
        "suggested_next_step": attempt["next_step"],
        "confidence": confidence,
    }
    defaults = {
        "user": user,
        "question": question,
        "problem_statement": question.problem_statement,
        "lecture_objective": question.lecture_objective,
        "student_code": attempt["code"],
        "sample_input": question.sample_input,
        "expected_output": question.expected_output,
        "execution_status": execution_status,
        "execution_stdout": attempt["output"],
        "execution_stderr": attempt.get("execution_stderr", ""),
        "execution_return_code": execution_return_code,
        "execution_timed_out": attempt.get("execution_timed_out", execution_status == "timeout"),
        "execution_time_ms": attempt.get("execution_time_ms", 12),
        "actual_output": attempt["output"],
        "output_comparison_status": attempt["comparison"],
        "comparison_mode": question.comparison_mode,
        "error_category": error_category,
        "classification_outcome": classification_outcome,
        "peci_error_code": peci_error_code,
        "peci_error_label": peci_label,
        "legacy_error_category": "",
        "feedback_level": feedback_level,
        "concept_reference": trajectory["concept_reference"],
        "feedback_text": attempt["feedback"],
        "does_reveal_solution": False,
        "uses_runtime_evidence": True,
        "suggested_next_step": attempt["next_step"],
        "confidence": confidence,
        "prompt_version": "seed_demo",
        "prompt_text": "Seeded demonstration record; no LLM call was made.",
        "feedback_schema_version": FEEDBACK_SCHEMA_VERSION,
        "raw_ai_response": json.dumps(raw_payload, indent=2),
        "ai_error": "",
        "llm_model_name": "seeded-demo",
        "llm_latency_ms": 0,
        "llm_token_usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        "estimated_cost": Decimal("0.000000"),
        "trajectory_id": trajectory["trajectory_id"],
        "trajectory_attempt_number": attempt["attempt_number"],
        "misconception": attempt["misconception"],
        "solved": attempt["solved"],
        "ground_truth_category": attempt["error_type"],
        "json_compliance": True,
        "schema_validation_status": "valid_schema",
        "schema_validation_notes": "",
        "solution_leakage_flag": False,
        "llm_used": Question.PROVIDER_DEEPSEEK,
    }

    if existing:
        for field_name, value in defaults.items():
            setattr(existing, field_name, value)
        existing.save()
        record = existing
        created = False
    else:
        record = CodeFeedbackRecord.objects.create(
            evaluation_sample_id=sample_id,
            **defaults,
        )
        created = True

    days_ago = trajectory["start_days_ago"] - (attempt["attempt_number"] - 1)
    target_created_at = timezone.now() - timedelta(days=days_ago)
    CodeFeedbackRecord.objects.filter(pk=record.pk).update(created_at=target_created_at)
    return created


class Command(BaseCommand):
    help = "Seed reproducible demo users, questions, and optional submission history."

    def _write(self, message):
        if self.verbosity > 0:
            self.stdout.write(message)

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-history",
            action="store_true",
            help="Also seed deterministic multi-attempt demo history for analytics charts.",
        )
        parser.add_argument(
            "--reset-demo-history",
            action="store_true",
            help=(
                "Delete existing submissions for the demo students before rebuilding "
                "the deterministic trajectory history. Requires --with-history."
            ),
        )

    def handle(self, *args, **options):
        self.verbosity = int(options.get("verbosity", 1))
        User = get_user_model()

        users_by_username = {}
        for data in DEMO_USERS:
            password = data["password"]
            user, created = User.objects.get_or_create(username=data["username"])
            user.email = data["email"]
            user.first_name = data["first_name"]
            user.is_staff = data["is_staff"]
            user.is_superuser = data["is_superuser"]
            user.is_active = True
            user.set_password(password)
            user.save()
            users_by_username[user.username] = user
            status = "created" if created else "updated"
            self._write(f"{status}: user {user.username}")

        questions_by_title = {}
        for data in DEMO_QUESTIONS:
            raw_topic_ids = [value.strip() for value in data["topic_tags"].split(",")]
            unknown_topic_ids = sorted(set(raw_topic_ids) - set(TOPIC_TAXONOMY))
            if unknown_topic_ids:
                raise CommandError(
                    f"Question {data['title']!r} uses unknown topic ids: "
                    + ", ".join(unknown_topic_ids)
                )
            canonical_data = {**data, "topic_tags": serialize_topic_tags(raw_topic_ids)}
            title = canonical_data["title"]
            question, created = Question.objects.update_or_create(
                title=title,
                defaults=canonical_data,
            )
            questions_by_title[question.title] = question
            status = "created" if created else "updated"
            self._write(f"{status}: question {question.title}")

        topic_coverage = {topic_id: 0 for topic_id in TOPIC_TAXONOMY}
        for question in questions_by_title.values():
            for topic_id in question.topic_tags.split(","):
                topic_coverage[topic_id] += 1
        under_covered = {
            topic_id: total for topic_id, total in topic_coverage.items() if total < 2
        }
        if under_covered:
            raise CommandError(f"Demo question topic coverage is below two: {under_covered}")

        if options["reset_demo_history"] and not options["with_history"]:
            raise CommandError("--reset-demo-history requires --with-history.")

        if options["reset_demo_history"]:
            demo_student_usernames = [
                data["username"] for data in DEMO_USERS if not data["is_staff"]
            ]
            deleted_count, _ = CodeFeedbackRecord.objects.filter(
                user__username__in=demo_student_usernames
            ).delete()
            self._write(
                self.style.WARNING(
                    f"Reset demo history: {deleted_count} existing records deleted."
                )
            )

        if options["with_history"]:
            created_count = 0
            updated_count = 0
            expected_sample_ids = set()
            for trajectory in DEMO_HISTORY:
                _validate_demo_trajectory(trajectory)
                for attempt in trajectory["attempts"]:
                    expected_sample_ids.add(_trajectory_sample_id(trajectory, attempt))
                    created = _upsert_record(
                        trajectory,
                        attempt,
                        users_by_username,
                        questions_by_title,
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            stale_records = CodeFeedbackRecord.objects.filter(
                evaluation_sample_id__startswith="demo-"
            ).exclude(evaluation_sample_id__in=expected_sample_ids)
            deleted_count, _ = stale_records.delete()
            self._write(
                self.style.SUCCESS(
                    f"Seeded demo history: {created_count} created, "
                    f"{updated_count} updated, {deleted_count} stale deleted."
                )
            )

        self._write(self.style.SUCCESS("Demo seed data is ready."))
