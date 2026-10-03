# Day 14 Supplemental Boundary Evaluation

Revision: 2026-09-11 22:51:01 CST

This file summarises the separate real-LLM evaluation for the 12 hand-crafted boundary cases. It is a supplemental system-coverage check and must not be mixed into the Day 12 headline Refactory results.

## Scope

- Dataset: 12 hand-crafted boundary cases covering syntax, indentation, timeout, stdin/input, value conversion, output formatting, condition, loop boundary, module import, type, function-return, and index-error cases.
- Design: 12 samples × 2 providers × 3 prompt versions = 72 real LLM outputs.
- Providers: DeepSeek and Kimi.
- Prompt versions: baseline, context-aware, strict-scaffolded.
- Source runs: #37, #38, and #39. Run #38 was a slow Kimi rerun after RPM errors; run #39 fixed one remaining Kimi JSON failure. The final aggregate deduplicates by sample/provider/prompt key and keeps the latest successful rerun where applicable.

## Automatic Metrics

- Total final results: 72
- Overall category accuracy: 83.33%
- JSON compliance rate: 100.00%
- Usable schema rate: 100.00%
- Solution leakage rate: 0.00%
- Runtime evidence usage rate: 66.67%
- Average latency: 3412.61 ms
- Final AI/API error count: 0
- Schema status counts: 70 repaired schema, 2 valid schema

## Accuracy By Condition

| Provider × Prompt | Accuracy | JSON Compliance | Leakage | Runtime Evidence |
| --- | ---: | ---: | ---: | ---: |
| DeepSeek baseline | 58.33% | 100.00% | 0.00% | 0.00% |
| DeepSeek context-aware | 91.67% | 100.00% | 0.00% | 100.00% |
| DeepSeek strict-scaffolded | 91.67% | 100.00% | 0.00% | 100.00% |
| Kimi baseline | 75.00% | 100.00% | 0.00% | 0.00% |
| Kimi context-aware | 91.67% | 100.00% | 0.00% | 100.00% |
| Kimi strict-scaffolded | 91.67% | 100.00% | 0.00% | 100.00% |

## Reporting Note

Use this result as a supplemental boundary evaluation only. The main Day 12 result remains the 55-sample Refactory real-student evaluation with 330 model outputs. In the final report, describe these 12 samples as hand-crafted boundary/system tests, not as real student submissions.

No separate human review is imported for this supplemental boundary run. Feedback-quality evidence should cite the Day 12 AI-assisted human review spot-check file: `evaluation_reports/day12_ai_assisted_human_review_final_20.csv`.

## Artifacts

- Summary JSON: `/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day14_boundary_cases_real_llm_final_summary.json`
- Results JSON: `/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day14_boundary_cases_real_llm_final_results.json`
- Accuracy chart: `/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day14_boundary_cases_real_llm_final_accuracy_by_condition.svg`
- Quality rates chart: `/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day14_boundary_cases_real_llm_final_quality_rates.svg`
- Ground-truth distribution chart: `/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day14_boundary_cases_real_llm_final_ground_truth_distribution.svg`
- Confusion matrix chart: `/Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day14_boundary_cases_real_llm_final_confusion_matrix.svg`
