"""Observational tracer for the shopping agent. Does not affect scoring.

This drives one session through the same Agent class and the same simulated
customer the official evaluator uses, and prints what the agent was thinking
between turns.

It is strictly an observer. It imports `starter.agent` and
`evaluator.local_evaluator` and changes neither. The only patching it does is on
its *own* Agent instance, to intercept the planner's inputs before planning
runs; the scored entrypoint constructs its own instance and never sees this.

The interesting output is the `rollouts` line, which reports what each question
and each list length was worth in simulation. Those numbers are local variables
inside `Agent._plan_inner` and are discarded once a decision is made, so this
script recomputes them rather than reaching in for them:

  * `_plan_inner` seeds its randomness deterministically as
    `random.Random((state["index"] << 8) ^ turn)`, so an outside observer can
    reproduce the identical particle set and random-number table;
  * `_rollout`, `_q_hat` and `_choose_show` copy any state they mutate, so
    re-running them is side-effect free.

Because the replication is exact rather than approximate, the script re-derives
the decision and asserts it matches the one the agent actually made. A mismatch
is printed loudly rather than hidden -- if these ever diverge, the trace is
lying and should not be trusted.

Usage:
    python demo/trace_session.py --session public_0007
    python demo/trace_session.py --find
"""
from __future__ import annotations

import argparse
import random
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator import local_evaluator as EV          # noqa: E402
from starter import agent as AG                      # noqa: E402
from starter.agent import Agent                      # noqa: E402

WIDTH = 96
TITLE_CHARS = 55


# --------------------------------------------------------------------------- #
# formatting helpers
# --------------------------------------------------------------------------- #

def short(text: str, limit: int = TITLE_CHARS) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def field(label: str, body: str, width: int = WIDTH) -> str:
    """`label    : body`, wrapped and hanging-indented to stay inside `width`."""
    head = f"{label:<10}: "
    return textwrap.fill(
        body, width=width, initial_indent=head,
        subsequent_indent=" " * len(head), break_long_words=False,
    )


# Buckets measured over the development dialogues; see experiments/E058.
def confidence(gap: float) -> str:
    if gap >= 4.0:
        return "confident (gaps this wide were right 100% of the time)"
    if gap >= 3.0:
        return "likely (52%)"
    if gap >= 2.0:
        return "likely (60%)"
    if gap >= 1.0:
        return "leaning (26%)"
    return "unsure (gaps under 1 were right 12% of the time)"


# --------------------------------------------------------------------------- #
# read-only replication of Agent._plan_inner
# --------------------------------------------------------------------------- #

def replicate_plan(agent: Agent, state: dict, context, pool: int, turn: int, top_k: int):
    """Recompute every option's simulated value, mutating nothing.

    Mirrors `_plan_inner` step for step, keeping the per-option numbers it
    discards. Returns None where `_plan_inner` would take an early exit.
    """
    if context is None or context.size <= 1 or turn >= AG.MAX_TURNS:
        return None
    residual = pool & ~AG._lowest_mask(pool, AG.SHOW_REF)
    if not residual:
        return None

    rng = random.Random((state["index"] << 8) ^ turn)
    particles = agent._sample_particles(context, residual, rng)
    if not particles:
        return None
    draws = [
        [rng.random() for _ in range(AG.DRAW_STRIDE * (AG.ROLLOUT_DEPTH + 2))]
        for _ in particles
    ]

    legal = agent._legal_actions(state, context, residual)
    question_value: dict[int, float] = {}
    best_action, best_score = None, -1.0
    for action in legal:
        total = weight_sum = 0.0
        for slot, (position, weight) in enumerate(particles):
            total += weight * agent._rollout(
                context, residual, action, position, draws[slot], state, turn,
                AG.ROLLOUT_SHOW,
            )
            weight_sum += weight
        monte_carlo = total / weight_sum if weight_sum else 0.0
        prior = agent._q_hat(context, residual, action, state, turn)
        score = (1.0 - AG.PRIOR_BLEND) * monte_carlo + AG.PRIOR_BLEND * prior
        question_value[action] = score
        if score > best_score:
            best_score, best_action = score, action

    silent_value = None
    if best_action is not None:
        silent = weight_sum = 0.0
        for position, weight in particles:
            silent += weight * AG._no_info_value(
                context.rank_of(residual, position), turn + 1, AG.ROLLOUT_SHOW
            )
            weight_sum += weight
        silent_value = silent / weight_sum if weight_sum else 0.0
        if best_score + AG.SILENCE_MARGIN < silent_value:
            best_action = None

    show_value = replicate_show(agent, context, pool, best_action, particles, draws,
                                state, turn, top_k)
    best_show = max(show_value, key=show_value.get) if show_value else top_k
    return {
        "questions": question_value,
        "shows": show_value,
        "action": best_action,
        "show": best_show,
        "silent": silent_value,
        "particles": len(particles),
    }


def replicate_show(agent, context, pool, action, particles, draws, state, turn, top_k):
    """Mirror of `_choose_show`, keeping the value of every list length."""
    total_mass = context.mass(pool)
    if total_mass <= 0.0:
        return {}
    options = sorted({min(k, top_k) for k in AG.SHOW_OPTIONS if k > 0} | {top_k})
    head = AG._lowest_positions(pool, options[-1])

    values: dict[int, float] = {}
    immediate = 0.0
    filled = 0
    for show in options:
        while filled < show and filled < len(head):
            immediate += context.weights[head[filled]] * AG._session_return(filled + 1, turn)
            filled += 1
        survivors = pool & ~AG._lowest_mask(pool, show)
        tail_mass = context.mass(survivors)
        continuation = 0.0
        if survivors and tail_mass > 0.0:
            total = weight_sum = 0.0
            for slot, (position, weight) in enumerate(particles):
                if not survivors & context.bit[position]:
                    continue
                if action is None:
                    value = AG._no_info_value(
                        context.rank_of(survivors, position), turn + 1, AG.ROLLOUT_SHOW
                    )
                else:
                    value = agent._rollout(
                        context, survivors, action, position, draws[slot], state, turn,
                        AG.ROLLOUT_SHOW,
                    )
                total += weight * value
                weight_sum += weight
            if weight_sum:
                continuation = (total / weight_sum) * tail_mass
        values[show] = (immediate + continuation) / total_mass
    return values


# --------------------------------------------------------------------------- #
# display-only clue extraction (mirrors _observe's matching, for labels)
# --------------------------------------------------------------------------- #

def clues_in(agent: Agent, message: str) -> list[str]:
    normalized = (message or "").lower().replace("-", " ")
    found: list[str] = []
    for attr, regex in AG.PHRASE_REGEX.items():
        hits = sorted({m.lower() for m in regex.findall(normalized)})
        found += [f"{attr}={v}" for v in hits]
    sizes = sorted({m.lower() for m in AG.SIZE_CONTEXT_RE.findall(normalized)})
    sizes += [p for p in AG.SIZE_STANDALONE_PHRASES if p in normalized]
    found += [f"size={v}" for v in sorted(set(sizes))]
    tokens = AG._terms(message or "")
    node = agent._category_phrase(tokens)
    if node:
        found.append(f"category={node}")
    for brand in sorted(agent._store_phrases(tokens)):
        found.append(f"brand={brand}")
    if agent._extract_budget(message or ""):
        found.append("budget=stated")
    return found


def narrowing(agent: Agent, state: dict) -> str:
    """How far the evidence held so far cuts the catalogue down."""
    total = len(agent._all_ids)
    parts = [f"{total:,}"]
    pool = None
    if state["category_rows"]:
        pool = set(state["category_rows"])
        parts.append(f"{len(pool):,} (category)")
    for index, (_attr, asins) in enumerate(state["constraints"][:3], start=1):
        pool = set(asins) if pool is None else (pool & set(asins))
        noun = "requirement" if index == 1 else "requirements"
        parts.append(f"{len(pool):,} ({index} {noun})")
    return " -> ".join(parts)


# --------------------------------------------------------------------------- #
# session driver
# --------------------------------------------------------------------------- #

class Tracer:
    """Runs one session, capturing the planner's inputs before it decides."""

    def __init__(self, agent: Agent, products: dict, catalog_ids: set):
        self.agent = agent
        self.products = products
        self.catalog_ids = catalog_ids
        self.captured = None
        self._real_plan = agent._plan
        agent._plan = self._plan

    def _plan(self, state, context, pool, turn, top_k):
        # State here is exactly what the planner will see: `_observe` has run,
        # but `_recommend` has not yet marked anything shown and `asked` has not
        # yet been incremented.
        self.captured = {
            "replica": replicate_plan(self.agent, state, context, pool, turn, top_k),
            "ranked": self.agent._ranked_ids(state, AG.WORKING_SET),
            "constraints": list(state["constraints"]),
            "category_rows": state["category_rows"],
            "phrases": list(state["phrases"]),
        }
        return self._real_plan(state, context, pool, turn, top_k)

    def close(self):
        self.agent._plan = self._real_plan

    def title(self, asin: str) -> str:
        return short(self.products.get(asin, {}).get("title", asin))

    def run(self, sample: dict, categories: dict, verbose: bool = True) -> dict:
        agent = self.agent
        session_id = f"trace_{sample['sample_id']}"
        agent.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = EV.materialize_hidden_fields(sample, self.products)
        effective = {**sample, "intent_card": card, "behavior": behavior}

        disclosed: set[str] = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        message = EV.initial_message(
            effective, EV.coarse_category(categories.get(target, [])), disclosed
        )

        record = {"sample_id": sample["sample_id"], "opening": message,
                  "turn1_shown": None, "hit_turn": None, "hit_rank": None}

        if verbose:
            print("=" * WIDTH)
            print(f"  SESSION {sample['sample_id']}   scenario={sample['scenario_type']}"
                  f"   difficulty={sample.get('difficulty_bucket', '?')}")
            print(f"  target  {target}  {self.title(target)}")
            print("=" * WIDTH)

        for turn in range(1, EV.MAX_TURNS + 1):
            self.captured = None
            response = agent.respond(session_id, message, turn, EV.TOP_K)
            ranked = EV.normalize_recommendations(response.get("recommendations"),
                                                  self.catalog_ids)
            if turn == 1:
                record["turn1_shown"] = len(ranked)

            if verbose:
                self.report(turn, message, response, ranked, target)

            if override_applied and target in ranked:
                record["hit_turn"] = turn
                record["hit_rank"] = ranked.index(target) + 1
                if verbose:
                    print(f"            -> HIT at rank {record['hit_rank']}\n")
                break
            if verbose:
                print("            -> no hit, continue\n")
            if turn == EV.MAX_TURNS:
                break

            override = effective.get("behavior", {}).get("override") or {}
            if not override_applied and turn + 1 == int(override.get("turn", 3)):
                override_applied = True
                new_value = str(override.get("new_value", ""))
                if new_value:
                    disclosed.add(new_value)
                message = str(override.get("message",
                                           "Actually, please ignore my earlier preference."))
            else:
                message, boundary_used = EV.customer_reply(
                    effective, response.get("ask_attribute"), disclosed, boundary_used
                )

        if verbose and record["hit_turn"] is None:
            print("            -> MISS\n")
        return record

    def report(self, turn, message, response, ranked, target):
        cap = self.captured
        print(f"=== TURN {turn} ===")
        print(field("SHOPPER", " ".join(str(message).split())))

        clues = clues_in(self.agent, message)
        print(field("clues", ", ".join(clues) if clues else "(none extracted)"))

        phrases = (cap or {}).get("phrases") or []
        if phrases:
            shown = ", ".join(f'"{p}"' for p in phrases[-6:])
            print(field("phrases", shown))

        if cap:
            state_view = {"category_rows": cap["category_rows"],
                          "constraints": cap["constraints"]}
            print(field("narrowed", narrowing(self.agent, state_view)))

            ids, scores = cap["ranked"]
            for i, (asin, score) in enumerate(zip(ids[:3], scores[:3]), start=1):
                mark = "*" if asin == target else " "
                print(f"  #{i}{mark} {score:7.2f}  {self.title(asin)}")
            if len(scores) >= 2:
                gap = scores[0] - scores[1]
                print(field("gap #1-#2", f"{gap:.2f}  -> {confidence(gap)}"))

        replica = (cap or {}).get("replica")
        if replica:
            best = sorted(replica["questions"].items(), key=lambda kv: -kv[1])[:3]
            qs = " | ".join(f"ask {AG.ACTIONS[a]} {v:.3f}" for a, v in best)
            ss = " | ".join(f"show {k} {v:.3f}" for k, v in sorted(replica["shows"].items()))
            print(field("rollouts", f"{qs}"))
            print(field("", ss))
            print(field("", f"({replica['particles']} hypotheses simulated, "
                            f"{AG.ROLLOUT_DEPTH} turns deep)"))

        ask = response.get("ask_attribute")
        decision = (f"show {len(ranked)} product{'s' if len(ranked) != 1 else ''}, "
                    + (f'ask "{ask}"' if ask else "ask nothing"))
        print(field("DECISION", decision))

        if replica is not None:
            # Cross-check: the replay above reproduced the planner's own inputs,
            # so it must reach the planner's own decision. If it does not, the
            # numbers printed above are not the ones the agent acted on.
            expected_ask = None if replica["action"] is None else AG.ACTIONS[replica["action"]]
            if expected_ask != ask or replica["show"] != len(ranked):
                print(field("!! WARNING",
                            f"replay disagrees with the agent "
                            f"(replay: show {replica['show']}, ask {expected_ask}). "
                            f"The rollout numbers above may not be what it used."))

        if ranked:
            print(field("published", "; ".join(self.title(a) for a in ranked[:2])
                        + ("; ..." if len(ranked) > 2 else "")))


# --------------------------------------------------------------------------- #
# session finder
# --------------------------------------------------------------------------- #

def find_sessions(agent, samples, catalog_ids, categories, products):
    tracer = Tracer(agent, products, catalog_ids)
    records = []
    for i, sample in enumerate(samples, start=1):
        records.append(tracer.run(sample, categories, verbose=False))
        if i % 25 == 0:
            print(f"  ...{i}/{len(samples)} sessions", file=sys.stderr)
    tracer.close()

    one = [r for r in records if r["turn1_shown"] == 1 and r["hit_rank"] == 1]
    ten = [r for r in records if r["turn1_shown"] == 10]

    print("=" * WIDTH)
    print("  CATEGORY 1 - showed ONE product on turn 1 and hit at rank 1")
    print(f"  {len(one)} sessions qualify. Five with the shortest opening message:")
    print("=" * WIDTH)
    for r in sorted(one, key=lambda r: len(r["opening"]))[:5]:
        print(f"\n  {r['sample_id']}   hit turn {r['hit_turn']}, rank {r['hit_rank']}"
              f"   ({len(r['opening'])} chars)")
        print(textwrap.fill(r["opening"], width=WIDTH - 4,
                            initial_indent="    ", subsequent_indent="    "))

    print("\n" + "=" * WIDTH)
    print(f"  CATEGORY 2 - showed TEN products on turn 1 ({len(ten)} sessions, all listed)")
    print("=" * WIDTH)
    for r in sorted(ten, key=lambda r: (r["hit_turn"] or 99)):
        turn = r["hit_turn"]
        flag = "  <- converges fast" if turn is not None and turn <= 3 else ""
        outcome = (f"hit turn {turn}, rank {r['hit_rank']}" if turn else "MISS")
        print(f"\n  {r['sample_id']}   {outcome}{flag}")
        print(textwrap.fill(r["opening"], width=WIDTH - 4,
                            initial_indent="    ", subsequent_indent="    "))

    print("\n" + "=" * WIDTH)
    print("  Suggested pairing for the video: one session from each category.")
    print("  The contrast is the argument: same agent, same turn, different confidence,")
    print("  different list length. Nothing in the code schedules that.")
    print("=" * WIDTH)


# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Observational tracer for the shopping agent (does not affect scoring)."
    )
    parser.add_argument("--session", help="sample_id to trace, e.g. public_0007")
    parser.add_argument("--find", action="store_true",
                        help="scan all sessions and suggest which to record")
    parser.add_argument("--catalog", default=str(ROOT / "data" / "catalog.jsonl"))
    parser.add_argument("--dataset", default=str(ROOT / "data" / "public_set.jsonl"))
    args = parser.parse_args()

    if not args.session and not args.find:
        parser.error("give --session SAMPLE_ID or --find")

    print("loading catalogue and building the agent (~80s)...", file=sys.stderr)
    samples = EV.load_jsonl(args.dataset)
    catalog_ids, categories, products = EV.catalog_index(args.catalog)
    agent = Agent(args.catalog)

    if args.find:
        find_sessions(agent, samples, catalog_ids, categories, products)
        return

    chosen = [s for s in samples if s["sample_id"] == args.session]
    if not chosen:
        parser.error(f"no session {args.session!r} in {args.dataset}")
    tracer = Tracer(agent, products, catalog_ids)
    try:
        tracer.run(chosen[0], categories, verbose=True)
    finally:
        tracer.close()


if __name__ == "__main__":
    main()
