"""Streams a live evaluation run to JSON for the dashboard. Does not affect scoring.

This runs the **official** evaluation. It calls `evaluator.local_evaluator.evaluate`
itself -- the same function `python -m evaluator.local_evaluator` calls, with the
same arguments -- so the customer simulation, the hit rule, and the metrics are the
evaluator's own, not a re-implementation. Nothing here is copied out of it.

The only additions are observers on this script's own `Agent` instance:

  * `reset` marks the start of the next session (the evaluator walks `samples` in
    order, so the sample is known from the count);
  * `respond` reads the ranked list on the way out;
  * `_plan` captures the planner's inputs on the way in, exactly as
    `demo/trace_session.py` does, and re-derives what every option was worth.

After each turn the accumulated state is written atomically to `--out`, and the
dashboard polls that file. Progress metrics are computed with the evaluator's own
`metric_summary`; when the run finishes, the official numbers `evaluate()` returned
replace them.

Because the rollout replay is side-effect free (see `trace_session.py`), the score
this prints must equal the score `python -m evaluator.local_evaluator` prints. It is
printed at the end so you can check.

Usage:
    python demo/live_run.py --out dashboard/public/live-run.json
    python demo/live_run.py --out dashboard/public/live-run.json --limit 12
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.trace_session import Tracer                 # noqa: E402
from evaluator import local_evaluator as EV           # noqa: E402
from starter import agent as AG                       # noqa: E402
from starter.agent import Agent                       # noqa: E402

DETAILED_SESSIONS = 3          # completed sessions kept with their full turn traces
WRITE_INTERVAL = 0.25          # seconds; a session boundary always flushes


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat()


class LiveRun(Tracer):
    """Watches the evaluator run and keeps a JSON snapshot of it on disk."""

    def __init__(self, agent: Agent, products: dict, catalog_ids: set, samples: list[dict],
                 out: Path, rollouts: bool = True):
        super().__init__(agent, products, catalog_ids, rollouts=rollouts)
        self.samples = samples
        self.out = out
        self.started = now()
        self.status = "running"
        self.index = -1                  # which sample the evaluator is on
        self.current: dict | None = None
        self.completed: list[dict] = []  # evaluator-shaped records, for metric_summary
        self.detailed: list[dict] = []   # the last few, with turns
        self.compact: list[dict] = []    # every finished session, small
        self.final: dict | None = None
        self._last_write = 0.0

        self._real_reset = agent.reset
        self._real_respond = agent.respond
        agent.reset = self._reset
        agent.respond = self._respond

    def close(self):
        self.agent.reset = self._real_reset
        self.agent.respond = self._real_respond
        super().close()

    # -- observers ---------------------------------------------------------- #

    def _reset(self, session_id, user_profile):
        self._finish()
        self.index += 1
        sample = self.samples[self.index]
        target = str(sample["ground_truth"]["parent_asin"])
        _card, behavior = EV.materialize_hidden_fields(sample, self.products)
        override = (behavior.get("override") or {}) if sample["scenario_type"] == "intent_override" else {}
        self.current = {
            "sample_id": sample["sample_id"],
            "scenario_type": sample["scenario_type"],
            "difficulty": sample.get("difficulty_bucket"),
            "target": target,
            "target_title": self.full_title(target),
            "override_turn": int(override["turn"]) if override else None,
            "opening": None,
            "hit_turn": None,
            "hit_rank": None,
            "turns": [],
        }
        self.write(force=True)
        return self._real_reset(session_id, user_profile)

    def _respond(self, session_id, user_message, turn, top_k):
        self.captured = None
        response = self._real_respond(session_id, user_message, turn, top_k)
        session = self.current
        if session is None:                      # never happens via evaluate(); be safe
            return response
        ranked = EV.normalize_recommendations(response.get("recommendations"), self.catalog_ids)
        data = self.turn_data(turn, user_message, response, ranked, session["target"])
        if turn == 1:
            session["opening"] = data["shopper"]

        # The evaluator's own hit rule: an intent_override session does not count a
        # hit until the turn the override lands on.
        override_turn = session["override_turn"]
        applied = override_turn is None or turn >= override_turn
        if applied and session["target"] in ranked:
            session["hit_turn"] = turn
            session["hit_rank"] = ranked.index(session["target"]) + 1
            data["hit_rank"] = session["hit_rank"]

        session["turns"].append(data)
        self.write()
        return response

    # -- bookkeeping -------------------------------------------------------- #

    def _finish(self):
        session = self.current
        self.current = None
        if session is None:
            return
        rank = session["hit_rank"]
        self.completed.append({
            "sample_id": session["sample_id"],
            "scenario_type": session["scenario_type"],
            "hit": session["hit_turn"] is not None,
            "first_hit_turn": session["hit_turn"],
            "best_rank": rank,
            "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
        })
        turn1 = session["turns"][0] if session["turns"] else None
        self.compact.append({
            "sample_id": session["sample_id"],
            "scenario_type": session["scenario_type"],
            "hit_turn": session["hit_turn"],
            "hit_rank": rank,
            "turns": len(session["turns"]),
            "turn1_shown": turn1["decision"]["show"] if turn1 else None,
            "turn1_gap": turn1["gap"] if turn1 else None,
        })
        self.detailed = [*self.detailed, session][-DETAILED_SESSIONS:]

    def metrics(self) -> dict:
        summary = EV.metric_summary(self.completed)
        if not self.completed:
            return {**summary, "efficiency": 0.0, "technical_score": 0.0}
        # The evaluator's formula, applied to the sessions finished so far.
        efficiency = max(0.0, min(1.0, (11.0 - float(summary["mttc"])) / 10.0))
        score = 0.50 * summary["hit_rate_at_10"] + 0.30 * summary["mrr"] + 0.20 * efficiency
        return {**summary, "efficiency": round(efficiency, 6),
                "technical_score": round(score, 6)}

    # -- snapshot ----------------------------------------------------------- #

    def write(self, force: bool = False):
        if not force and time.monotonic() - self._last_write < WRITE_INTERVAL:
            return
        self._last_write = time.monotonic()
        payload = {
            "status": self.status,
            "startedAt": self.started,
            "updatedAt": now(),
            "total": len(self.samples),
            "completed": len(self.completed),
            "rolloutDepth": AG.ROLLOUT_DEPTH,
            "rolloutsTraced": self.rollouts,
            "metrics": self.metrics(),
            "current": self.current,
            "recent": list(reversed(self.detailed)),
            "sessions": self.compact,
            "final": self.final,
        }
        tmp = self.out.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, self.out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the official evaluation and stream it to the dashboard."
    )
    parser.add_argument("--out", default=str(ROOT / "dashboard" / "public" / "live-run.json"),
                        help="JSON snapshot the dashboard polls")
    parser.add_argument("--limit", type=int, help="run only the first N sessions (partial score)")
    parser.add_argument("--no-rollouts", action="store_true",
                        help="skip the rollout replay; faster, but the 'what each option was "
                             "worth' panel is empty")
    parser.add_argument("--results", help="also write the evaluator's full result JSON here")
    parser.add_argument("--catalog",
                        default=os.environ.get("TECHJAM_CATALOG")
                        or str(ROOT / "data" / "catalog.jsonl"))
    parser.add_argument("--dataset", default=str(ROOT / "data" / "public_set.jsonl"))
    args = parser.parse_args()

    if not Path(args.catalog).exists():
        parser.error(f"no catalogue at {args.catalog}. Download catalog.jsonl.gz from the "
                     f"GitHub Release into data/, or set TECHJAM_CATALOG / pass --catalog.")

    print("loading catalogue and building the agent (~80s)...", file=sys.stderr)
    samples = EV.load_jsonl(args.dataset)
    if args.limit:
        samples = samples[: args.limit]
    catalog_ids, categories, products = EV.catalog_index(args.catalog)
    agent = Agent(args.catalog)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    live = LiveRun(agent, products, catalog_ids, samples, out, rollouts=not args.no_rollouts)
    live.write(force=True)
    print(f"streaming to {out} -- open the dashboard's Live run page", file=sys.stderr)

    started = time.monotonic()
    try:
        result = EV.evaluate(agent, samples, catalog_ids, categories, products)
    except BaseException:
        live.status = "failed"
        live._finish()
        live.write(force=True)
        raise
    finally:
        live.close()

    live._finish()
    live.status = "done"
    live.final = {key: value for key, value in result.items() if key != "sessions"}
    live.final["elapsedSeconds"] = round(time.monotonic() - started, 1)
    live.final["partial"] = bool(args.limit)
    live.write(force=True)

    if args.results:
        Path(args.results).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(live.final, indent=2))
    print(f"\n{len(samples)} sessions in {live.final['elapsedSeconds']}s. "
          f"Technical score {result['recommended_technical_score']}"
          + ("  (partial run)" if args.limit else
             "  -- must equal `python -m evaluator.local_evaluator`."), file=sys.stderr)


if __name__ == "__main__":
    main()
