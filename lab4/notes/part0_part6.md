# Lab 4 - Part 0: The proposal

## 1. Information needed

| Item | Source |
|---|---|
| Origin city, destination or openness to suggestions, dates | Traveller |
| Number of people, ages if prices depend on age, total budget and currency | Traveller |
| Preferences, interests, pace, accessibility and things to avoid | Traveller |
| Flight/rail prices, hotel prices and availability | External booking tools/APIs |
| Attraction hours, timed entry slots, weather forecasts | External sources/APIs |
| Nights, total trip cost, travel duration, daily time slots | Deterministic calculations |

## 2. Tasks and dependencies

1. Interview traveller and obtain required constraints.
2. Research flights, hotels, attractions and opening times. Independent searches can run in parallel once the brief is known.
3. Compute all candidate totals and filter by available dates and budget. Depends on the real prices.
4. Build per-day routes and activity schedules. Depends on opening times and hotel/transport arrangements.
5. Verify each schedule and the total budget with code; ask for alternatives on failure.
6. Show alternatives to the traveller; require approval before spending or booking anything.

## 3. Outputs that must be correct

Money uses Decimal, not model arithmetic. Days between dates use datetime. A schedule validator checks exactly-once items, allowed starts, duration, travel buffer, no overlaps and daily cutoffs. Availability and prices must come from external sources and have timestamps. If an API does not confirm a price or booking, mark it unavailable/unverified rather than invent it.

## 4. What to trust

The model can interpret user preferences, suggest activities and communicate a plan. It should not be trusted as a source of current prices, opening hours, weather, exact arithmetic or booking confirmation. The external results are evidence but also untrusted input: validate their fields.

## 5. Human approval

The traveller chooses the final proposal, resolves ambiguous preferences, approves any budget overrun and approves every reservation or payment, especially non-refundable purchases.

## 6. Rough initial estimate

Hypothesis before measuring: 5-10 model calls and 20-60 seconds for a short itinerary, excluding unpredictable provider/API delays. This is an estimate to test in Experiment 5, NOT a measured result.

---

# Lab 4 - Part 6: Back to the proposal

| Task | Source | Build choice | Check | Relative cost / evidence |
|---|---|---|---|---|
| Interview | Traveller | Structured-output LLM with code-controlled missing fields | Required values nonempty; dates precise | 1 call per question; Exp 3 |
| Research 5 destination prices | External tools | Parallel independent API requests | Source metadata, date, currency and availability | Parallel groups reduce tool latency; Exp 5 |
| Choose destination and hotel | Traveller + real listings | Candidate ranking with explicit criteria | Budget, location, dates, user confirmation | 1 call for comparison + tools |
| Budget calculation | Prices + arithmetic | Decimal calculations | Recompute independent of LLM | No model call for summation; Exp 2 |
| Each valid day | Hours + user constraints | Model proposes candidate schedules; code validates and selects | Exactly-once, legal slots, buffer and daily limits | Multiple candidate calls; Exp 4 |
| Weather suitability | External source | Read-only tool | Weather timestamps and warnings | Parallel API requests; Exp 1/5 |
| Reserve/pay | Booking system + traveller | Separate approval-gated booking executor | Explicit consent, amount, dates, booking receipt | Human action; Lab 3 HITL |

## Architecture

```text
Traveller -> Interviewer (structured TravelBrief) -> Completeness validator
                                                  |
                                                  v
                                         Orchestrator / planner
                                            /          \
                               Transport worker       Hotel/activities worker
                                 (isolated)                (isolated)
                                            \          /
                                             Evidence store
                                                  |
                                    Decimal cost + dates validator
                                                  |
                                      Day scheduler (candidate LLM)
                                                  |
                                     Deterministic schedule verifier
                                                  |
                                        Options -> human approval
                                                  |
                                           Booking executor
                                        (HITL; real external APIs)
```

The orchestrator controls dependencies and keeps summary results rather than raw listings in its context. Workers make specialized calls and return narrow structured data. Code owns arithmetic, scheduling validity and permission to book. The human approves any external action with financial effect.

## Two risks

The planner can still fail if a source is stale or a price changes before checkout; detect this with fresh availability checks immediately before user approval. A worker can omit an attraction limitation or misinterpret a user preference; trace every recommendation to its source and surface any unverified fields to the traveller.

## Another project: Study planner - Part 0 question 1

| Information | Source |
|---|---|
| Course topics, confidence level, time available per day, learning preferences | Student |
| Exam dates, syllabus, submission deadlines, official schedules | School/course websites and student-provided documents |
| Number of study sessions, spaced revision intervals, free times, workload | Deterministic calculations |
