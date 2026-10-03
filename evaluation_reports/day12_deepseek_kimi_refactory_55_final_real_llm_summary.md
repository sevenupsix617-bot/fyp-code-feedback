# Day 12 Evaluation Analysis

Revision: 2026-09-11 22:52:59 CST

- Run: Day 12 DeepSeek and Kimi Refactory 55-sample final aggregate (#aggregate:22,10,12,13,14,23,16,17,18,20,21,11,24,25,26,27,28,29,30,31,32,33,34,35)
- Mode: llm
- Dataset: Refactory (55 samples)
- Providers: deepseek, kimi
- Prompt versions: baseline, context_aware, strict_scaffolded
- Notes: Aggregated EvaluationRun ids: [22, 10, 12, 13, 14, 23, 16, 17, 18, 20, 21, 11, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]. Result filters: providers=all, prompt_versions=all. Duplicate result keys detected and deduplicated by latest run id: 80.
- Caveat: This run contains real LLM API results.

## Automatic Metrics

- Total results: 330
- Category accuracy: 0.7788
- JSON compliance rate: 0.997
- Usable schema rate: 0.997
- Solution leakage rate: 0.0
- Runtime evidence usage rate: 0.6667
- Average latency ms: 6472.02
- Estimated total cost: see `evaluation_reports/day12_api_cost_estimate.md` (approximately USD 1.38-1.72 for retained final runs)
- AI/API error count: 1
- Schema status counts: {"invalid_json": 1, "repaired_schema": 306, "valid_schema": 23}

## AI-Assisted Human Review Spot-Check Metrics

- Reviewed count: 20 / 330 outputs
- Review coverage rate: 0.0606
- Average helpfulness score: 4.2
- Average lecture alignment score: 4.2
- Average actionability score: 4.45
- Human-marked solution leakage rate: 0.0
- Review method note: these are AI-assisted draft scores that were checked and confirmed/adjusted by the reviewer. Report this as a 20-sample spot-check, not as independent or large-scale human evaluation.

## Artifacts

- summary_json: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_summary.json
- summary_markdown: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_summary.md
- results_json: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_results.json
- canonical_ai_assisted_human_review_csv: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_ai_assisted_human_review_final_20.csv
- manual_review_template_csv: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_manual_review_template.csv
- reference_review_suggestions_csv: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_reference_review_suggestions.csv
- accuracy_chart_svg: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_accuracy_by_condition.svg
- quality_rates_svg: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_quality_rates.svg
- ground_truth_distribution_svg: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_ground_truth_distribution.svg
- confusion_matrix_svg: /Users/a77777/Desktop/fyp-code-feedback/evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_confusion_matrix.svg
