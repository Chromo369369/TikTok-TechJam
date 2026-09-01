# Demo tracer

`trace_session.py` shows what the agent is thinking between turns. It exists for
the demo video and for debugging.

## It does not affect scoring

This is an **observer**. It imports the same `Agent` class and the same simulated
customer the official evaluator uses, and changes neither.

- Nothing in `starter/agent.py` or `evaluator/local_evaluator.py` was modified to
  build it. There is no verbose flag, no debug hook, no branch in the decision
  loop.
- The only patching is on the tracer's **own** `Agent` instance, wrapping `_plan`
  to read its inputs before planning runs. `python -m evaluator.local_evaluator`
  constructs its own instance and never sees it.
- The per-option numbers are **recomputed**, not extracted. They are local
  variables inside `Agent._plan_inner` and are discarded once a decision is made.

Verified before and after: `python -m evaluator.local_evaluator` reports
`0.958362` either way, and `python -m unittest discover -s tests` passes.

## Running it

```bash
python demo/trace_session.py --session public_0089    # trace one session
python demo/trace_session.py --find                   # pick sessions to record
```

Add `--export PATH` to write the same trace as JSON instead of text. Several
sessions can be traced in one pass:

```bash
python demo/trace_session.py --session public_0068,public_0089 \
    --export dashboard/public/trace-data.json
```

That file is what the dashboard's **Session trace** page reads
(`dashboard/src/Trace.tsx`, or `npm.cmd run trace` from `dashboard/`). It carries
every field the text output prints — clues, phrases, narrowing, the top of the
ranking, the confidence gap, and each option's simulated value.

Python 3.10+ and the standard library only — nothing to install. The catalogue is
read from `data/catalog.jsonl`; if it lives elsewhere, set `TECHJAM_CATALOG` or
pass `--catalog <path>`. Construction takes about 80 seconds. Output is wrapped
to 96 columns.

### Why `--session` replays earlier sessions first

Tracing a single session in isolation shows a decision **the scored run never
made**. Two pieces of agent state carry across sessions and both change the
outcome:

- `state["index"]` is a session counter, and it seeds the planner's randomness as
  `random.Random((state["index"] << 8) ^ turn)`;
- the "will a shopper answer this?" tally is learned over the whole run and is
  never reset.

So `--session public_0068` silently replays sessions 1–67 first, then traces 68
with the agent in exactly the state the scored run leaves it in. This is not
theoretical: traced in isolation, `public_0068` publishes one product on turn 1;
traced in position, it publishes ten. Adds a few seconds for later sessions.

## Reading the output

```
=== TURN 1 ===
SHOPPER   : I'm looking for Athletic Walking. Lightweight and responsive Ultra Go...
clues     : use_case=athletic, feature=lightweight, category=athletic walking
phrases   : "athletic walking lightweight responsive", "responsive ultra go midsole"
narrowed  : 50,000 -> 342 (category) -> 170 (2 requirements)
  #1*   28.69  Skechers Women's Go Walk 6-Big Splash Sneaker
  #2    15.71  Skechers Men's Go Max-Athletic Air Mesh Slip on Walk...
gap #1-#2 : 12.98  -> confident (gaps this wide were right 100% of the time)
rollouts  : ask material 0.738 | ask feature 0.734 | ask color 0.717
            show 1 0.969 | show 10 0.974
            (27 hypotheses simulated, 4 turns deep)
DECISION  : show 10 products, ask "material"
```

- `*` marks the hidden target, so you can watch it climb.
- `narrowed` is how far the evidence cuts the catalogue. When it reaches **0** the
  line says so — no product satisfies every extracted requirement, which is
  exactly why requirements only ever add points and never filter.
- `rollouts` is the important line: what each option was worth in simulation.
  It is the evidence that the agent plans forward rather than just ranking.
- `gap #1-#2` is the confidence measure. The percentages are measured, not
  asserted — see `experiments/E058`.

### What the numbers on the `rollouts` line mean

Question values (`ask material 0.738`) are 75% simulated outcome and 25% the
prior learned during self-play. List-length values (`show 1 0.969`) are expected
session score. They are on the same scale — expected points for this session —
so they can be compared directly, but they answer different questions and the
agent picks a winner from each row independently.

### One counterintuitive thing worth knowing before you narrate it

The agent publishes **ten when it is confident**, not when it is unsure. All four
sessions that publish ten on turn 1 have a #1-to-#2 gap between 6.1 and 18.0;
the median gap when publishing one is 0.84.

The logic: if the leader is almost certainly right, you convert at rank 1 whether
you show one row or ten, so ten costs nothing and eliminates nine more
non-targets. If you are unsure, showing ten risks converting at rank 5 and
locking in that score, so you show one and buy another turn.

Both behaviours come from the same expected-value calculation. Nothing schedules
either one.

## Picking sessions to record

`--find` scans all 200 sessions and reports the turn-1 list length distribution,
five short-opening sessions that publish one product, and every session that
publishes ten — each with its turn-1 confidence gap.

The counts move whenever ranking improves, because a better-ranked leader is a
more confident one. At score `0.958362` the split is 196 / 4.
