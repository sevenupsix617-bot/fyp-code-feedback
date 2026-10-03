# Day 12 API Cost Estimate

- Updated at: 2026-09-11 18:10:48 CST
- Scope: DeepSeek and Kimi real LLM evaluation on the 55-sample Refactory dataset.
- Final aggregate report: `day12_deepseek_kimi_refactory_55_final_real_llm_summary.md`
- DeepSeek aggregate report: `day12_deepseek_refactory_55_real_llm_summary.md`
- Kimi aggregate report: `day12_kimi_refactory_55_final_real_llm_summary.md`

## DeepSeek Completed Run

- Successful API results: 165
- API/model error results: 0
- Prompt tokens: 195,739
- Completion tokens: 39,224
- Total tokens: 234,963

Using DeepSeek cache-miss pricing assumptions:

- Off-peak lower-bound estimate: USD 0.052895
- Peak upper-bound estimate: USD 0.105790
- Mixed time-window estimate from stored result timestamps: USD 0.064066

This is an estimate because provider billing may depend on exact model routing, cached input pricing, and current account billing rules. Re-check the provider pricing page before putting the number in the final report.

Pricing source to verify:

- DeepSeek API pricing: https://api-docs.deepseek.com/quick_start/pricing/

## Kimi Completed Run

Kimi was initially blocked by quota/balance errors, then completed after account top-up and targeted cleanup reruns.

- Successful API results: 164
- API/model error results retained in final aggregate: 1
- Prompt tokens: 191,671
- Completion tokens: 155,969
- Total tokens: 347,640

Using Kimi K2.7 Code Highspeed pricing assumptions:

- Cache-hit input lower-bound estimate plus output: about USD 1.3206
- Cache-miss input upper-bound estimate plus output: about USD 1.6120

This estimate is higher than DeepSeek mainly because Kimi returned much longer completions and has a higher output-token price for the selected code model.

Pricing source to verify:

- Kimi K2.7 Code pricing: https://www.kimi.ai/resources/kimi-k2-7-code-pricing

## Final Day 12 Aggregate

- Providers: DeepSeek and Kimi
- Dataset size: 55 Refactory samples
- Total evaluation results: 330
- API/model error results retained: 1
- Combined token count: 582,603
- Estimated provider API spend for the retained final result set: about USD 1.38 to USD 1.72

This final range excludes failed discarded reruns and local dry-run checks. It should be treated as an experimental-cost estimate, not an accounting statement.
