# Lab 4 experiment results (to complete after live API runs)

The following cells are intentionally unfilled. They require actual GEMINI_API_KEY/model measurements; do not submit invented counts.

## Experiment 1 - knowledge audit

Record the model responses and which claims could be independently verified (real prices and hours cannot be checked from memory).

## Experiment 2 (`python exp2_budget.py`, then `python exp2_budget.py --code`)

| Prompt | Correct / 5 | Average output tokens | Vote |
|---|---|---|---|
| Short | pending | pending | pending |
| Better | pending | pending | pending |
| Expression + code | pending | pending | n/a |

## Experiment 3 (`python exp3_interview.py --simulate`)

| Mode | Number of questions | Missing required | Missing optional |
|---|---|---|---|
| Normal | pending | pending | pending |
| Strict | pending | pending | pending |

## Experiment 4 (`python exp4_day.py`)

| Variant | Valid / 5 | Average output tokens |
|---|---|---|
| Plain | pending | pending |
| Hint, JSON only | pending | pending |
| Hint + plan field | pending | pending |

## Experiment 5 and Homework C (`python exp5_tools.py --runs 3`)

| Question | Mode | Correct / 3 | Median calls | Median input tokens | Median tool seconds | Median total seconds |
|---|---|---|---|---|---|---|
| 1-4 | loop/plan/parallel | pending | pending | pending | pending | pending |

Also run `python exp5_tools.py loop 3 --runs 3` and `python exp5_tools.py loop 3 --sum --runs 3` to compare arithmetic reliability.

## Homework A (`python homework_a_vouchers.py 4 9 10 13`; then `1 5 5 5`)

| Vouchers | Direct correct / 5 | Direct calls/tokens | Beam successful | Beam calls/tokens |
|---|---|---|---|---|
| 4 9 10 13 | pending | pending | pending | pending |
| 1 5 5 5 | pending | pending | pending | pending |

## Homework B (`python homework_b_failed_test.py 5`)

| Method | Successful runs / 5 | Average attempts | Average tokens |
|---|---|---|---|
| Plain retries | pending | pending | pending |
| Retries with lessons | pending | pending | pending |

Review the model's lessons manually and note inaccuracies.
