# Lab 4 checkpoints (conceptual answers; compare with your actual experiment runs)

## Experiment 1

The model may be confident about details learned during training, but it cannot guarantee real-time flight prices, opening hours or concert schedules without tool access. Relative dates require an explicit calendar and timezone; an unverified memory-based answer is not enough for booking.

## Experiment 2

1. A short final-answer prompt does not force a reliable breakdown of shared versus per-person expenses, overnight stays and two-way tickets.
2. Voting does not help if all five answers share a systematic error, and can prefer an incorrect majority.
3. Prefer LLM extraction plus deterministic arithmetic in production: it is auditable and not sensitive to a model's math skill. The measured success rates need actual model runs.

Budget reference: flights 2*2*129 = 516; hotel 4*85 = 340; city tax 2*4*2.5 = 20; passes 2*45 = 90; total 966; remaining 34 EUR.

## Experiment 3

1. The base interviewer may miss Ana's preference to avoid early starts, because `avoid` is optional; this could make an otherwise valid itinerary unpleasant.
2. Dates like `May` or `12-16 May` lack an unambiguous year, so they are not sufficient for a booking. Code, not the model, must determine operational completeness; stricter validation should require day, month and year.
3. With optional fields made required, the number of questions can increase by up to two (or more if clarification is needed). Do not claim an exact count without running the simulation.

## Experiment 4

1. A prompt-only hint may not improve schedule validity because the model cannot reliably enforce every constraint, especially without an explicit planning field.
2. The verifier has exact opening slots, durations, minimum transfer time, item counts and the day boundary; it computes rule violations deterministically.
3. Without the verifier, we risk choosing a persuasive but invalid schedule. Keep only verified candidates, or report failure.

## Experiment 5

1. Parallel mode runs independent tool calls simultaneously, decreasing waiting time. End-to-end time is noisy because it includes LLM latency, backend retries and model generation variance.
2. Flights from Vaslui depend on `nearest_airport`; the origin must be known before calling `flight_price`.
3. No direct Iasi-Lisbon flight is available. A fixed plan cannot adapt unless it anticipates the Bucharest connection; the ReAct loop can make extra calls after seeing the surprise.
4. A model may invent a year or assume an old one for `12 May`. The system prompt should say: 'When a date lacks a year, resolve it as the next occurrence after the current calendar date in the traveller's timezone; ask if still ambiguous.'

## Homework C

- Independent planned tool calls can run concurrently; dependent calls must wait.
- Calling `sum_eur` in the loop is straightforward once earlier results are available. A plan written before those results are returned cannot know what numeric values to pass to the calculator without a richer expression/dependency language.
- Compare medians across 3 real runs per mode, not single timings.
