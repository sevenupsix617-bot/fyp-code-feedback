# Context-Aware AI Programming Feedback System

Revision: 2026-09-30 11:23:28 CST (Asia/Macau)

This project is a Django prototype for Lu Jiayi's FYP. It gives beginner Python students formative feedback by combining sandbox execution evidence with LLM-generated tutoring comments. The system supports a student submission portal, an instructor dashboard, learning analytics, and a reproducible evaluation pipeline comparing DeepSeek and Kimi under multiple prompt designs.

## Current Scope

- Student workflow: login, choose from 20 fixed-taxonomy programming questions, submit Python code, receive feedback, retry the same question with the previous code preserved, jump to another question, and review submission history.
- Runtime evidence: execute code in a sandbox, support stdin sample input, compare actual and expected output, and record timeout/runtime status.
- Feedback generation: store prompt version, full prompt text, provider, model, token usage, estimated cost, JSON validity, and solution-leakage flag.
- Instructor workflow: staff-only dashboard for questions, recent submissions, common error categories, student profiles, and evaluation results.
- Analytics: fixed-topic mastery radar charts, per-topic attempt timelines, repeated errors, mastered concepts, class-level error distribution, hard questions, and teaching suggestions.
- Evaluation: the 55-sample Day 12 prompt comparison, a separate 12-sample hand-crafted boundary evaluation, and a current-taxonomy PECI A-X independent run on the same 55 Refactory samples, with provenance, confirmed ground truth, confusion matrices, and an AI-assisted human review spot-check.
- Reproducible demo data: four human-authored trajectories with five attempts on the same question, explicit attempt numbers, misconceptions, runtime outcomes, and a final solved attempt. Seed generation makes no external API call.

## Human-Guided Taxonomies

The LLM is not allowed to invent question topics or error-category names. The
project fixes both taxonomies before classification, following the supervisor's
2026-09-16 review and adapting Table 1 of Cooke, Hawwash, and Smith's *Python
for Engineers Concept Inventory (PECI)* to the introductory Python scope used
by this FYP (DOI: `10.5281/zenodo.14656194`).

The eight fixed question topics are:

- Program Structure and Statements
- Variables and Assignment
- Expressions and Operators
- Conditionals and Boolean Logic
- Iteration and Range
- Functions and Return Values
- Strings, Input, and Output
- Collections and Indexing

The primary error taxonomy now uses the 24 Programming Error names from PECI
Table 1 directly. The paper's A-X codes are retained internally as source
identifiers, while user-facing pages show only the exact literature category
names. The FYP adds a researcher-written operational definition to each label
so that the LLM has a repeatable decision boundary. The LLM may select one
internal code, but it may not invent, merge, or rename a category.

Three system outcomes are kept outside the literature taxonomy: `No Error`,
`Outside PECI Scope`, and `Unknown`. Runtime evidence such as `TypeError`,
`IndexError`, timeout, stderr, and output mismatch is stored separately. A
runtime exception is not relabelled as a PECI error unless the submitted code
actually satisfies one of the A-X definitions.

The canonical definitions, PECI mappings, topic aliases, and prompt text live
in `feedback_app/taxonomy.py`. `feedback_schema_v3_peci` injects those definitions
and the classification priority into every feedback prompt. Django Admin uses
a fixed multi-select field for question topics, so new questions cannot create
free-form topic wording through the normal instructor workflow.

To propose fixed tags for newly added, untagged questions, first run a preview:

```bash
python manage.py tag_question_topics --provider deepseek --dry-run
```

`--dry-run` calls the selected provider but does not write to the database. It
prints validated proposals for human review. After checking them, rerun without
`--dry-run` to save. The command rejects empty, malformed, or unknown topic IDs
instead of silently converting them. Use it only after explicitly approving the
API call, data sharing, and expected cost.

The completed Day 12/14 evaluation retains its original v1/v2 category labels
for reproducibility. Migration `0010` copies those values to
`legacy_error_category`; it does not manufacture A-X labels for historical
records. PECI A-X accuracy is reported only from the separate, completed v3
evaluation described below. `python manage.py canonicalize_categories` also
removes internal source-code prefixes from the display field of current PECI
records; it does not replace the stored original prompt or raw AI response.

## Local Setup

Use the local Desktop copy unless you intentionally create a separate backup. The GitHub repository does not need to be changed for local development.

```bash
cd /Users/a77777/Desktop/fyp-code-feedback
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo --with-history
python manage.py runserver 127.0.0.1:8000
```

To rebuild a clean, deterministic analytics demo after using `student1` or
`student2` for manual submissions, run:

```bash
python manage.py seed_demo --with-history --reset-demo-history
```

`--reset-demo-history` is deliberately opt-in. It deletes existing submissions
for the two demo student accounts before recreating their four five-attempt
trajectories; it does not delete evaluation runs or submissions owned by other
users.

If the project is stored in iCloud Desktop and startup becomes very slow, move the project to a non-iCloud folder or recreate the virtual environment outside iCloud sync.

## Demo Accounts

These accounts are created by `python manage.py seed_demo --with-history` for local demonstration only.

| Role | Username | Password | Main URL |
| --- | --- | --- | --- |
| Instructor | `instructor` | `instructor123` | `http://127.0.0.1:8000/instructor/` |
| Student | `student1` | `student123` | `http://127.0.0.1:8000/student/` |
| Student | `student2` | `student123` | `http://127.0.0.1:8000/student/` |

Useful demo pages:

- Student submission: `http://127.0.0.1:8000/student/`
- Student profile: `http://127.0.0.1:8000/profile/`
- Instructor dashboard: `http://127.0.0.1:8000/instructor/`
- Learning analytics: `http://127.0.0.1:8000/analytics/`
- Evaluation dashboard: `http://127.0.0.1:8000/evaluation/`
- Staff experiment interface: `http://127.0.0.1:8000/experiment/`

## Environment Variables

Copy `.env.example` to `.env` and fill only the values needed for your run. Do not commit `.env`.

- `DJANGO_SECRET_KEY`: set a new secret for any non-local deployment.
- `DJANGO_DEBUG`: keep `True` for local demo; set `False` for staging/production.
- `DJANGO_ALLOWED_HOSTS`: comma-separated hosts, for example `127.0.0.1,localhost`.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: required only when serving through HTTPS domains.
- `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SESSION_COOKIE_SECURE`, `DJANGO_CSRF_COOKIE_SECURE`, `DJANGO_SECURE_HSTS_SECONDS`, `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_SECURE_HSTS_PRELOAD`: keep the local defaults for demo; enable them only for HTTPS deployment.
- `DEEPSEEK_API_KEY`, `KIMI_API_KEY` or `MOONSHOT_API_KEY`: required only for real LLM calls.
- `*_INPUT_COST_PER_1M`, `*_OUTPUT_COST_PER_1M`: optional token price settings for cost estimates.

## Evaluation Workflow

Exporting and dry-run checks are safe because they do not call external APIs:

```bash
python manage.py export_evaluation_dataset --refactory-data-dir /path/to/refactory/data
python manage.py run_evaluation_dataset --name "Dry run pipeline check"
python manage.py analyze_evaluation_run --run-id 1 --review-limit 20
```

Real LLM evaluation sends the local evaluation samples, question context, and runtime evidence to the selected API provider. Run it only after confirming API balance and privacy boundaries:

```bash
python manage.py run_evaluation_dataset --run-llm --providers deepseek --prompt-versions baseline,context_aware,strict_scaffolded
python manage.py run_evaluation_dataset --run-llm --providers kimi --prompt-versions baseline,context_aware,strict_scaffolded --kimi-min-interval 3
python manage.py aggregate_evaluation_runs --run-ids 1,2 --dedupe-latest --name "Final real LLM evaluation"
```

The final Day 12 real-run report is `evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_summary.md`. The canonical AI-assisted human review spot-check file is `evaluation_reports/day12_ai_assisted_human_review_final_20.csv`.

### Independent PECI A-X Evaluation

The current PECI taxonomy must not be evaluated against the legacy Day 12
ground-truth labels. The independent A-X workflow therefore has two guarded
phases.

Phase 1 asks one provider for annotation proposals. It withholds the old
category from the classifier prompt, supplies the fixed PECI definitions and
stored runtime evidence, validates every proposed code against the local A-X
taxonomy, and leaves both researcher-confirmation columns blank:

```bash
python manage.py propose_peci_ground_truth --provider deepseek
```

The resulting file is
`evaluation_reports/peci_ax_ground_truth_proposals.csv`. The `--dry-run` form
prints all 55 proposals without writing a CSV or database records, but it still
makes 55 paid API calls. A researcher must review every row, fill
`confirmed_outcome` and `confirmed_peci_code`, and save the reviewed copy as
`evaluation_reports/peci_ax_ground_truth_confirmed.csv`.

Phase 2 refuses to run unless the confirmed file contains one valid, unique,
fully confirmed row for every one of the 55 Refactory samples. It then runs the
locked scope of 55 samples x 2 providers x one `strict_scaffolded` prompt:

```bash
python manage.py run_peci_ax_evaluation --run-llm --kimi-min-interval 21 --retry-delay 21
```

This makes 110 paid API calls and writes the following independent evidence:

- `evaluation_reports/peci_ax_evaluation_summary.json`
- `evaluation_reports/peci_ax_evaluation_summary.md`
- `evaluation_reports/peci_ax_evaluation_confusion_matrix.csv`

Report this ground truth as `researcher-confirmed AI-assisted A-X annotation`.
The resulting A-X accuracy is not interchangeable with the Day 12 legacy
taxonomy accuracy of 77.88%.

The completed post-fix A-X run is database run `#43`. The prompt now explicitly
requires escaped double quotes and encoded newlines in JSON string values. If a
provider still returns malformed JSON, the system makes one targeted repair
retry and stores both responses for audit. Results were:

- 110 outputs from 55 Refactory samples, 2 providers, and 1 strict-scaffolded prompt.
- Overall A-X accuracy: 50.00% (55/110), up from the pre-fix run's 32.73%.
- DeepSeek: 41.82% (23/55), with 0 output/API errors.
- Kimi: 58.18% (32/55), with 6 output/API errors, down from 34 before the fix.
- JSON repair: 1 attempt, 1 success, 0 malformed-JSON failures after retry.
- Residual Kimi errors: 3 empty responses and 3 network read timeouts; these are
  provider/transport failures rather than unescaped-quote parsing failures.
- Solution leakage: 0%.

Runs `#41` and `#42` were interrupted during operational checks (rate limiting
and insufficient balance) and are explicitly marked `ABORTED`; they are not
included in the final evidence or report files.

Final real-run headline results:

- 330 model outputs from 55 samples, 2 providers, and 3 prompt versions.
- Overall category accuracy: 77.88%.
- Prompt accuracy: baseline 55.5%, context-aware 90.9%, strict-scaffolded 87.3%.
- Provider accuracy: Kimi 82.4%, DeepSeek 73.3%.
- JSON compliance: 99.7%.
- Solution leakage: 0%.
- AI-assisted human review spot-check: 20/330 outputs (6.06%), helpfulness 4.20/5, lecture alignment 4.20/5, actionability 4.45/5, human-marked leakage 0%.

Supplemental boundary evaluation:

- 12 hand-crafted boundary cases, 2 providers, and 3 prompt versions, producing 72 real LLM outputs.
- Overall category accuracy: 83.33%.
- JSON compliance: 100%.
- Solution leakage: 0%.
- API/model errors after Kimi slow rerun and single retry: 0.
- This run is reported separately as a boundary/system-coverage check and is not mixed into the Day 12 Refactory headline metrics.

## Data And Provenance

The evaluation dataset uses Refactory-derived student code submissions where provenance can be traced from exported dataset metadata. A small hand-crafted boundary set is used separately to cover categories that the selected Refactory subset does not naturally cover well, such as syntax, indentation, timeout, and stdin-related failures. The project does not use real MPU student data.

Keep these files available for reporting:

- `day14_report_evidence_pack.md`
- `report_assets/screenshots/`
- `evaluation_samples.json`
- `evaluation_dataset_sources.md`
- `evaluation_reports/day12_deepseek_kimi_refactory_55_final_real_llm_summary.md`
- `evaluation_reports/day12_ai_assisted_human_review_final_20.csv`
- `evaluation_reports/day14_boundary_cases_real_llm_final_summary.md`
- Final SVG charts in `evaluation_reports/`

## Deployment Notes

For the FYP demo, local deployment is the safest option. Public deployment is optional and should only be used if the supervisor explicitly needs an online link.

Before any non-local deployment:

```bash
python manage.py check --deploy
python manage.py collectstatic --noinput
```

Then set:

- `DJANGO_DEBUG=False`
- a fresh `DJANGO_SECRET_KEY`
- a restricted `DJANGO_ALLOWED_HOSTS`
- HTTPS and `DJANGO_CSRF_TRUSTED_ORIGINS`
- secure cookie, SSL redirect, and HSTS settings after HTTPS is confirmed
- a production-ready database if multiple users will access it

With the local defaults, `python manage.py check --deploy` is expected to warn about DEBUG, the demo secret key, HTTPS redirect, HSTS, and secure cookies. Those warnings are acceptable for a local-only FYP demo but must be cleared before any public deployment.

Do not deploy or commit `.env`, `db.sqlite3`, `.venv/`, `evaluation_runs/`, or large intermediate evaluation reports.

## Day 13 Acceptance Checklist

- A fresh clone can install dependencies from `requirements.txt`.
- A fresh database can be rebuilt with `migrate` and `seed_demo --with-history`.
- Demo users and questions are reproducible.
- Secrets and provider keys are configured through `.env`.
- Public/staging settings are documented separately from local demo settings.
- Evaluation commands and final Day 12 outputs are documented.
- Intermediate evaluation artifacts are ignored, while final report files remain identifiable.
