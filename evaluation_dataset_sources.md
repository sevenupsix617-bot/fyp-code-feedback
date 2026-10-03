# FYP Evaluation Dataset Sources

Revision: 2026-09-17 20:17:22 CST (Asia/Macau)

## Taxonomy Literature Source

The fixed topic taxonomy and the literature-grounded part of the error taxonomy
use Table 1 of the following paper as their principal source:

> Cooke, N., Hawwash, K. and Smith, B. (2019) 'Python for Engineers Concept
> Inventory (PECI): Contextualized assessment of programming skills for
> engineering undergraduates', *Proceedings of the 47th SEFI Annual
> Conference*, pp. 270-279. doi:10.5281/zenodo.14656194.

- Local source PDF: `/Users/a77777/Downloads/SEFI2019_022.pdf`
- DOI: https://doi.org/10.5281/zenodo.14656194
- Relevant location: Table 1, `PECI structure`, which separates Programming
  Concepts, Programming Errors, and Engineering Contextualisation.
- System implementation: `feedback_app/taxonomy.py`.

### Citation Boundary

PECI provides the human-knowledge framework and the exact A-X Programming Error
labels. The current v3 system uses those A-X labels directly:

- The eight topics select and combine PECI concepts that match the project's
  introductory Python scope. Recursion, files, and classes are currently out of
  scope.
- Each A-X label has a researcher-written operational definition in
  `feedback_app/taxonomy.py`. These definitions explain how the label is applied
  in this prototype; they are not presented as verbatim text from the paper.
- Runtime statuses such as type, value, index, import, input, and timeout
  failures are stored as deterministic execution evidence, not added to A-X.
- `No Error`, `Outside PECI Scope`, and `Unknown` are system outcomes, not PECI
  mistake types.

The completed Day 12/14 data uses the earlier 17-label v1/v2 taxonomy. It remains
valid historical evidence for comparing prompt conditions, but it is not an
evaluation of the new A-X taxonomy. Do not convert those labels automatically:
many mappings are not one-to-one. A separate v3 run is required for A-X accuracy.

## Source Chain

- User reference: 6hao.pdf / Haque et al. (2025), Section 3.1 Datasets: uses Refactory as a faulty Python student-program dataset.
- Original paper: Hu et al. (2019), Refactory: A Tool for Refactoring Python Programs, ASE 2019, Section V and Table II.
- Repository: https://github.com/githubhuyang/refactory
- Archive: https://github.com/githubhuyang/refactory/blob/master/data.zip
- Dataset note: The repository README states that data.zip contains 2,442 correct and 1,783 buggy program attempts by 361 NUS undergraduate students.
- License note: LGPL-3.0 license in the Refactory GitHub repository.

## Important Provenance Boundary

Most student programs in this export are copied from the real Refactory wrong_*.py submissions. The ground_truth_category values are not labels provided by Refactory; they are FYP manual annotations based on code inspection, the first failing test case, runtime status, and output comparison. The hand-crafted boundary cases are explicitly marked as supplemental system tests and must not be reported as real student submissions.

## Summary

- Total selected records: 67
- Real Refactory records: 55
- Hand-crafted boundary cases: 12
- Questions: {"hand_crafted_boundary": 12, "question_1": 11, "question_2": 11, "question_3": 11, "question_4": 11, "question_5": 11}
- Origins: {"hand_crafted_boundary_case": 12, "real_student_submission_refactory": 55}
- Ground-truth categories: {"Condition Error": 4, "Function Error": 4, "Indentation Error": 1, "Index Error": 8, "Input Error": 1, "Logic Error": 17, "Loop Boundary Error": 5, "Module Import Error": 1, "Name Error": 16, "Output Format Error": 1, "Syntax Error": 1, "Timeout": 1, "Type Error": 5, "Value Error": 2}
- Runtime statuses: {"eof_error": 1, "indentation_error": 1, "index_error": 8, "module_not_found": 1, "name_error": 16, "runtime_error": 2, "success": 29, "syntax_error": 1, "timeout": 1, "type_error": 5, "value_error": 2}
- Requires input: 4
- Expected timeout cases: 1

## Supplemental Boundary Samples

These records were added after the Refactory export revealed coverage gaps: the selected real records do not include syntax errors, indentation errors, timeouts, or stdin/input failures. They are intentionally separated through `sample_origin=hand_crafted_boundary_case`.

## Selected Records

| Sample ID | Origin | Source record | Failing test input | Failing test output | Ground truth |
| --- | --- | --- | --- | --- | --- |
| refactory-q1-wrong-001 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_001.py | data/question_1/ans/input_003.txt | data/question_1/ans/output_003.txt | Condition Error |
| refactory-q1-wrong-002 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_002.py | data/question_1/ans/input_010.txt | data/question_1/ans/output_010.txt | Name Error |
| refactory-q1-wrong-003 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_003.py | data/question_1/ans/input_010.txt | data/question_1/ans/output_010.txt | Loop Boundary Error |
| refactory-q1-wrong-004 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_004.py | data/question_1/ans/input_010.txt | data/question_1/ans/output_010.txt | Index Error |
| refactory-q1-wrong-005 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_005.py | data/question_1/ans/input_010.txt | data/question_1/ans/output_010.txt | Index Error |
| refactory-q1-wrong-006 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_006.py | data/question_1/ans/input_007.txt | data/question_1/ans/output_007.txt | Index Error |
| refactory-q1-wrong-007 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_007.py | data/question_1/ans/input_003.txt | data/question_1/ans/output_003.txt | Logic Error |
| refactory-q1-wrong-008 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_008.py | data/question_1/ans/input_001.txt | data/question_1/ans/output_001.txt | Condition Error |
| refactory-q1-wrong-009 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_009.py | data/question_1/ans/input_001.txt | data/question_1/ans/output_001.txt | Logic Error |
| refactory-q1-wrong-010 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_010.py | data/question_1/ans/input_001.txt | data/question_1/ans/output_001.txt | Condition Error |
| refactory-q1-wrong-011 | real_student_submission_refactory | data/question_1/code/wrong/wrong_1_011.py | data/question_1/ans/input_001.txt | data/question_1/ans/output_001.txt | Logic Error |
| refactory-q2-wrong-001 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_001.py | data/question_2/ans/input_007.txt | data/question_2/ans/output_007.txt | Logic Error |
| refactory-q2-wrong-002 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_002.py | data/question_2/ans/input_004.txt | data/question_2/ans/output_004.txt | Logic Error |
| refactory-q2-wrong-003 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_003.py | data/question_2/ans/input_004.txt | data/question_2/ans/output_004.txt | Logic Error |
| refactory-q2-wrong-004 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_004.py | data/question_2/ans/input_001.txt | data/question_2/ans/output_001.txt | Name Error |
| refactory-q2-wrong-005 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_005.py | data/question_2/ans/input_001.txt | data/question_2/ans/output_001.txt | Name Error |
| refactory-q2-wrong-006 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_006.py | data/question_2/ans/input_002.txt | data/question_2/ans/output_002.txt | Name Error |
| refactory-q2-wrong-007 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_007.py | data/question_2/ans/input_002.txt | data/question_2/ans/output_002.txt | Name Error |
| refactory-q2-wrong-008 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_008.py | data/question_2/ans/input_004.txt | data/question_2/ans/output_004.txt | Logic Error |
| refactory-q2-wrong-009 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_009.py | data/question_2/ans/input_004.txt | data/question_2/ans/output_004.txt | Logic Error |
| refactory-q2-wrong-010 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_010.py | data/question_2/ans/input_004.txt | data/question_2/ans/output_004.txt | Logic Error |
| refactory-q2-wrong-011 | real_student_submission_refactory | data/question_2/code/wrong/wrong_2_011.py | data/question_2/ans/input_001.txt | data/question_2/ans/output_001.txt | Name Error |
| refactory-q3-wrong-001 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_001.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Logic Error |
| refactory-q3-wrong-002 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_002.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Name Error |
| refactory-q3-wrong-003 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_003.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Name Error |
| refactory-q3-wrong-004 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_004.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Name Error |
| refactory-q3-wrong-005 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_005.py | data/question_3/ans/input_003.txt | data/question_3/ans/output_003.txt | Index Error |
| refactory-q3-wrong-006 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_006.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Type Error |
| refactory-q3-wrong-007 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_007.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Function Error |
| refactory-q3-wrong-008 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_008.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Function Error |
| refactory-q3-wrong-009 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_009.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Type Error |
| refactory-q3-wrong-010 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_010.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Index Error |
| refactory-q3-wrong-011 | real_student_submission_refactory | data/question_3/code/wrong/wrong_3_011.py | data/question_3/ans/input_001.txt | data/question_3/ans/output_001.txt | Index Error |
| refactory-q4-wrong-001 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_001.py | data/question_4/ans/input_001.txt | data/question_4/ans/output_001.txt | Type Error |
| refactory-q4-wrong-002 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_002.py | data/question_4/ans/input_001.txt | data/question_4/ans/output_001.txt | Name Error |
| refactory-q4-wrong-003 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_003.py | data/question_4/ans/input_001.txt | data/question_4/ans/output_001.txt | Name Error |
| refactory-q4-wrong-004 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_004.py | data/question_4/ans/input_001.txt | data/question_4/ans/output_001.txt | Name Error |
| refactory-q4-wrong-005 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_005.py | data/question_4/ans/input_001.txt | data/question_4/ans/output_001.txt | Function Error |
| refactory-q4-wrong-006 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_006.py | data/question_4/ans/input_002.txt | data/question_4/ans/output_002.txt | Logic Error |
| refactory-q4-wrong-007 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_007.py | data/question_4/ans/input_002.txt | data/question_4/ans/output_002.txt | Index Error |
| refactory-q4-wrong-008 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_008.py | data/question_4/ans/input_002.txt | data/question_4/ans/output_002.txt | Logic Error |
| refactory-q4-wrong-009 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_009.py | data/question_4/ans/input_003.txt | data/question_4/ans/output_003.txt | Logic Error |
| refactory-q4-wrong-010 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_010.py | data/question_4/ans/input_002.txt | data/question_4/ans/output_002.txt | Logic Error |
| refactory-q4-wrong-011 | real_student_submission_refactory | data/question_4/code/wrong/wrong_4_011.py | data/question_4/ans/input_001.txt | data/question_4/ans/output_001.txt | Name Error |
| refactory-q5-wrong-001 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_001.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Loop Boundary Error |
| refactory-q5-wrong-002 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_002.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Name Error |
| refactory-q5-wrong-003 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_003.py | data/question_5/ans/input_003.txt | data/question_5/ans/output_003.txt | Logic Error |
| refactory-q5-wrong-004 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_004.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Name Error |
| refactory-q5-wrong-005 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_005.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Logic Error |
| refactory-q5-wrong-006 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_006.py | data/question_5/ans/input_005.txt | data/question_5/ans/output_005.txt | Loop Boundary Error |
| refactory-q5-wrong-007 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_007.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Value Error |
| refactory-q5-wrong-008 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_008.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Loop Boundary Error |
| refactory-q5-wrong-009 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_009.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Name Error |
| refactory-q5-wrong-010 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_010.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Logic Error |
| refactory-q5-wrong-011 | real_student_submission_refactory | data/question_5/code/wrong/wrong_5_011.py | data/question_5/ans/input_001.txt | data/question_5/ans/output_001.txt | Type Error |
| boundary-syntax-missing-colon | hand_crafted_boundary_case | hand_crafted/boundary-syntax-missing-colon.py | hand_crafted/boundary-syntax-missing-colon_input.txt | hand_crafted/boundary-syntax-missing-colon_expected_output.txt | Syntax Error |
| boundary-indentation-missing-block | hand_crafted_boundary_case | hand_crafted/boundary-indentation-missing-block.py | hand_crafted/boundary-indentation-missing-block_input.txt | hand_crafted/boundary-indentation-missing-block_expected_output.txt | Indentation Error |
| boundary-timeout-infinite-loop | hand_crafted_boundary_case | hand_crafted/boundary-timeout-infinite-loop.py | hand_crafted/boundary-timeout-infinite-loop_input.txt | hand_crafted/boundary-timeout-infinite-loop_expected_output.txt | Timeout |
| boundary-input-missing-line | hand_crafted_boundary_case | hand_crafted/boundary-input-missing-line.py | hand_crafted/boundary-input-missing-line_input.txt | hand_crafted/boundary-input-missing-line_expected_output.txt | Input Error |
| boundary-value-invalid-int | hand_crafted_boundary_case | hand_crafted/boundary-value-invalid-int.py | hand_crafted/boundary-value-invalid-int_input.txt | hand_crafted/boundary-value-invalid-int_expected_output.txt | Value Error |
| boundary-output-format-strict | hand_crafted_boundary_case | hand_crafted/boundary-output-format-strict.py | hand_crafted/boundary-output-format-strict_input.txt | hand_crafted/boundary-output-format-strict_expected_output.txt | Output Format Error |
| boundary-condition-wrong-branch | hand_crafted_boundary_case | hand_crafted/boundary-condition-wrong-branch.py | hand_crafted/boundary-condition-wrong-branch_input.txt | hand_crafted/boundary-condition-wrong-branch_expected_output.txt | Condition Error |
| boundary-loop-off-by-one | hand_crafted_boundary_case | hand_crafted/boundary-loop-off-by-one.py | hand_crafted/boundary-loop-off-by-one_input.txt | hand_crafted/boundary-loop-off-by-one_expected_output.txt | Loop Boundary Error |
| boundary-module-import-misspelled | hand_crafted_boundary_case | hand_crafted/boundary-module-import-misspelled.py | hand_crafted/boundary-module-import-misspelled_input.txt | hand_crafted/boundary-module-import-misspelled_expected_output.txt | Module Import Error |
| boundary-type-string-int-concat | hand_crafted_boundary_case | hand_crafted/boundary-type-string-int-concat.py | hand_crafted/boundary-type-string-int-concat_input.txt | hand_crafted/boundary-type-string-int-concat_expected_output.txt | Type Error |
| boundary-function-print-not-return | hand_crafted_boundary_case | hand_crafted/boundary-function-print-not-return.py | hand_crafted/boundary-function-print-not-return_input.txt | hand_crafted/boundary-function-print-not-return_expected_output.txt | Function Error |
| boundary-index-empty-list | hand_crafted_boundary_case | hand_crafted/boundary-index-empty-list.py | hand_crafted/boundary-index-empty-list_input.txt | hand_crafted/boundary-index-empty-list_expected_output.txt | Index Error |
