# Revised Taxonomy Strict-Scaffolded Evaluation

## Scope and Ground Truth

- Ground truth source: researcher-confirmed revised taxonomy labels.
- Scope: 55 Refactory samples x 2 providers x 1 strict_scaffolded prompt.
- The label space contains the 24 PECI A-X categories and four researcher-defined project categories. Project categories are not PECI labels.
- This is separate from both the Day 12 legacy-taxonomy evaluation and the earlier frozen A-X evaluation; their accuracies are not results for this revised label space.

## Metrics

- Samples: 55
- Total model outputs: 110
- Overall accuracy: 0.5273
- AI/API error count: 3
- Provider/API failures: 0
- Invalid or unparseable responses after repair: 3
- JSON repair retries: 5
- Successful JSON repairs: 5
- Solution leakage rate: 0.0

| Provider | Results | Correct | Accuracy | API failures | Invalid responses | Repair retries | Repaired | Leakage rate | Average latency ms | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deepseek | 55 | 27 | 0.4909 | 0 | 0 | 0 | 0 | 0.0 | 3814.2 | None |
| kimi | 55 | 31 | 0.5636 | 0 | 3 | 5 | 5 | 0.0 | 13769.38 | None |

## Confusion Matrix

Rows are researcher-confirmed labels; columns are predicted PECI codes or explicit project/non-PECI outcomes.

| Ground truth \ Predicted | A | B | D | E | L | N | V | W | condition_error | loop_boundary_error | logical_error | runtime_error | invalid_output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| B | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 0 |
| D | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| E | 0 | 0 | 0 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 4 | 0 | 2 |
| L | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| N | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| V | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 1 | 0 |
| W | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 2 | 1 | 0 | 0 |
| condition_error | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| loop_boundary_error | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| logical_error | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 5 | 12 | 2 | 0 |
| runtime_error | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 16 | 1 |

## Accuracy by Ground-truth Category

| Category | Results | Correct | Accuracy |
| --- | ---: | ---: | ---: |
| A | 12 | 3 | 0.25 |
| B | 4 | 1 | 0.25 |
| D | 2 | 1 | 0.5 |
| E | 10 | 3 | 0.3 |
| L | 4 | 0 | 0.0 |
| N | 18 | 12 | 0.6667 |
| V | 6 | 5 | 0.8333 |
| W | 4 | 1 | 0.25 |
| condition_error | 2 | 2 | 1.0 |
| logical_error | 26 | 12 | 0.4615 |
| loop_boundary_error | 2 | 2 | 1.0 |
| runtime_error | 20 | 16 | 0.8 |

## Retention and Reliability

All 104 usable source outputs retained unchanged, including wrong predictions; only the 6 failed responses replaced by their technical retries. No accuracy-based selection.

Overall accuracy counts every scheduled sample-provider pair; technical failures count as unsuccessful outputs. Usable-response accuracy is a secondary measure with its smaller denominator disclosed. Per-category accuracy is recall on that confirmed category, not precision.

## Per-provider Per-category Metrics

| Provider | Category | Support | Correct | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| deepseek | A | 6 | 0 | None | 0.0 | 0.0 |
| deepseek | B | 2 | 0 | None | 0.0 | 0.0 |
| deepseek | D | 1 | 0 | None | 0.0 | 0.0 |
| deepseek | E | 5 | 1 | 1.0 | 0.2 | 0.3333 |
| deepseek | L | 2 | 0 | None | 0.0 | 0.0 |
| deepseek | N | 9 | 4 | 0.6667 | 0.4444 | 0.5333 |
| deepseek | V | 3 | 2 | 1.0 | 0.6667 | 0.8 |
| deepseek | W | 2 | 0 | None | 0.0 | 0.0 |
| deepseek | condition_error | 1 | 1 | 0.5 | 1.0 | 0.6667 |
| deepseek | logical_error | 13 | 8 | 0.5 | 0.6154 | 0.5517 |
| deepseek | loop_boundary_error | 1 | 1 | 0.2 | 1.0 | 0.3333 |
| deepseek | runtime_error | 10 | 10 | 0.4348 | 1.0 | 0.6061 |
| kimi | A | 6 | 3 | 1.0 | 0.5 | 0.6667 |
| kimi | B | 2 | 1 | 1.0 | 0.5 | 0.6667 |
| kimi | D | 1 | 1 | 1.0 | 1.0 | 1.0 |
| kimi | E | 5 | 2 | 1.0 | 0.4 | 0.5714 |
| kimi | L | 2 | 0 | 0.0 | 0.0 | 0.0 |
| kimi | N | 9 | 8 | 0.8 | 0.8889 | 0.8421 |
| kimi | V | 3 | 3 | 1.0 | 1.0 | 1.0 |
| kimi | W | 2 | 1 | 0.5 | 0.5 | 0.5 |
| kimi | condition_error | 1 | 1 | 0.125 | 1.0 | 0.2222 |
| kimi | logical_error | 13 | 4 | 0.5714 | 0.3077 | 0.4 |
| kimi | loop_boundary_error | 1 | 1 | 0.2 | 1.0 | 0.3333 |
| kimi | runtime_error | 10 | 6 | 0.6667 | 0.6 | 0.6316 |

Macro scores average only the 12 ground-truth categories represented in these selected samples. They are not coverage estimates across all 28 supported error categories. Undefined precision (no predictions) is recorded as null/None.
