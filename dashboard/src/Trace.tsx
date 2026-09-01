import { useEffect, useState } from 'react';

type Candidate = { rank: number; asin: string; title: string; score: number; target: boolean };
type Rollouts = {
  questions: { attribute: string; value: number }[];
  shows: { k: number; value: number }[];
  particles: number;
  depth: number;
  chosen_question: string | null;
  chosen_show: number;
};
type Turn = {
  turn: number;
  shopper: string;
  clues: string[];
  phrases: string[];
  narrowing: { steps: { label: string; count: number }[]; text: string; empty: boolean } | null;
  candidates: Candidate[];
  gap: number | null;
  confidence: string | null;
  rollouts: Rollouts | null;
  decision: { show: number; ask: string | null };
  published: { asin: string; title: string }[];
  warning: string | null;
  hit_rank?: number;
};
type Session = {
  sample_id: string;
  scenario_type: string;
  difficulty: string | null;
  target: string;
  target_title: string;
  opening: string;
  hit_turn: number | null;
  hit_rank: number | null;
  turns: Turn[];
};
export type TraceData = {
  generatedAt: string;
  dataset: string;
  catalogSize: number;
  rolloutDepth: number;
  sessions: Session[];
};

/** `demo/live_run.py` rewrites this file after every turn of the official run. */
type LiveSession = Session & { override_turn?: number | null };
type LiveMetrics = { hit_rate_at_10?: number; mrr?: number; mttc?: number; technical_score?: number };
export type LiveData = {
  status: 'running' | 'done' | 'failed';
  startedAt: string;
  updatedAt: string;
  total: number;
  completed: number;
  rolloutDepth: number;
  rolloutsTraced: boolean;
  metrics: LiveMetrics;
  current: LiveSession | null;
  recent: LiveSession[];
  sessions: { sample_id: string }[];
  final: { elapsedSeconds?: number; partial?: boolean } | null;
};

const num = (n: number, d = 3) => n.toFixed(d);

function Bars({ items }: { items: { label: string; value: number; chosen: boolean }[] }) {
  return (
    <div className="vbars">
      {items.map((x) => (
        <div key={x.label} className={x.chosen ? 'vbar chosen' : 'vbar'} title={`${x.label}: ${num(x.value)} expected points`}>
          <span className="vbar-label">{x.label}</span>
          <span className="vbar-track">
            <i style={{ width: `${Math.max(0, Math.min(1, x.value)) * 100}%` }} />
          </span>
          <b>{num(x.value)}</b>
          <em>{x.chosen ? 'chosen' : ''}</em>
        </div>
      ))}
    </div>
  );
}

function Candidates({ items }: { items: Candidate[] }) {
  const max = Math.max(...items.map((c) => c.score), 0.0001);
  return (
    <div className="cands">
      {items.map((c) => (
        <div key={c.asin} className={c.target ? 'cand target' : 'cand'} title={`${c.title} — score ${c.score.toFixed(2)}`}>
          <span className="cand-rank">#{c.rank}</span>
          <span className="cand-title">
            {c.title}
            {c.target && <b className="tag target-tag">hidden target</b>}
          </span>
          <span className="cand-track">
            <i style={{ width: `${(c.score / max) * 100}%` }} />
          </span>
          <b className="cand-score">{c.score.toFixed(2)}</b>
        </div>
      ))}
    </div>
  );
}

function Funnel({ steps, empty }: { steps: { label: string; count: number }[]; empty: boolean }) {
  return (
    <div className="funnel">
      {steps.map((s, i) => (
        <span key={s.label} className="funnel-step">
          {i > 0 && <em>→</em>}
          <b>{s.count.toLocaleString()}</b>
          <span>{s.label}</span>
        </span>
      ))}
      {empty && <p className="muted">Nothing satisfies every requirement — which is why requirements add points and never filter.</p>}
    </div>
  );
}

function TurnCard({ t, depth }: { t: Turn; depth: number }) {
  const ask = t.decision.ask;
  return (
    <section className="panel turn">
      <div className="turn-head">
        <p className="eyebrow">Turn {t.turn}</p>
        <p className="decision">
          show <b>{t.decision.show}</b> {t.decision.show === 1 ? 'product' : 'products'} · {ask ? <>ask <b>“{ask}”</b></> : <b>ask nothing</b>}
          {t.hit_rank && <span className="tag hit">hit at rank {t.hit_rank}</span>}
        </p>
      </div>

      <blockquote className="shopper">{t.shopper}</blockquote>

      <div className="grid two tight">
        <div>
          <p className="eyebrow">Clues extracted</p>
          <div className="chips">
            {t.clues.length ? t.clues.map((c) => <span className="chip" key={c}>{c}</span>) : <span className="muted">none extracted</span>}
          </div>
          {t.phrases.length > 0 && (
            <>
              <p className="eyebrow">Phrases kept</p>
              <div className="chips">
                {t.phrases.map((p) => <span className="chip quiet" key={p}>“{p}”</span>)}
              </div>
            </>
          )}
        </div>
        <div>
          <p className="eyebrow">Catalogue narrowing</p>
          {t.narrowing ? <Funnel steps={t.narrowing.steps} empty={t.narrowing.empty} /> : <span className="muted">planner short-circuited this turn</span>}
        </div>
      </div>

      {t.candidates.length > 0 && (
        <>
          <p className="eyebrow">Top of the ranking</p>
          <Candidates items={t.candidates} />
          {t.gap !== null && (
            <p className="gap">
              <span>gap #1–#2</span> <b>{t.gap.toFixed(2)}</b> <em>{t.confidence}</em>
            </p>
          )}
        </>
      )}

      {t.rollouts && (
        <div className="rollouts">
          <p className="eyebrow">What each option was worth in simulation</p>
          <div className="grid two tight">
            <div>
              <h4>Question to ask</h4>
              <Bars
                items={t.rollouts.questions.slice(0, 5).map((q) => ({
                  label: `ask ${q.attribute}`,
                  value: q.value,
                  chosen: q.attribute === t.rollouts!.chosen_question,
                }))}
              />
            </div>
            <div>
              <h4>How many to publish</h4>
              <Bars
                items={t.rollouts.shows.map((s) => ({
                  label: `show ${s.k}`,
                  value: s.value,
                  chosen: s.k === t.rollouts!.chosen_show,
                }))}
              />
            </div>
          </div>
          <p className="muted">
            {t.rollouts.particles} hypotheses simulated, {depth} turns deep. Both rows are expected points for this session, so they are
            directly comparable; the agent picks a winner from each row independently.
          </p>
        </div>
      )}

      {t.warning && <p className="warn">⚠ {t.warning}</p>}

      {t.published.length > 0 && (
        <details className="published">
          <summary>Published this turn ({t.published.length})</summary>
          <ol>
            {t.published.map((p) => <li key={p.asin}>{p.title}</li>)}
          </ol>
        </details>
      )}
    </section>
  );
}

function LiveStrip({ live }: { live: LiveData }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const i = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(i);
  }, []);
  const ago = Math.max(0, Math.round((Date.now() - new Date(live.updatedAt).getTime()) / 1000));
  const m = live.metrics || {};
  const done = live.completed;
  const label =
    live.status === 'running' ? `session ${Math.min(done + 1, live.total)} of ${live.total}`
    : live.status === 'done' ? `${done} of ${live.total} sessions scored`
    : `stopped after ${done} of ${live.total}`;
  return (
    <div className={`livebar ${live.status}`}>
      <span className="pip" />
      <b>{live.status === 'running' ? 'live' : live.status}</b>
      <span>{label}</span>
      <span className="livebar-track">
        <i style={{ width: `${(done / Math.max(live.total, 1)) * 100}%` }} />
      </span>
      {typeof m.hit_rate_at_10 === 'number' && <span>HR@10 <b>{m.hit_rate_at_10.toFixed(3)}</b></span>}
      {typeof m.mrr === 'number' && <span>MRR <b>{m.mrr.toFixed(3)}</b></span>}
      {typeof m.mttc === 'number' && <span>MTTC <b>{m.mttc.toFixed(2)}</b></span>}
      {typeof m.technical_score === 'number' && (
        <span>{live.status === 'running' ? 'score so far' : 'technical score'} <b>{m.technical_score.toFixed(4)}</b></span>
      )}
      <em>
        {live.status === 'running'
          ? ago < 2 ? 'updated just now' : `updated ${ago}s ago`
          : `finished ${new Date(live.updatedAt).toLocaleTimeString()}`}
      </em>
    </div>
  );
}

export function Trace() {
  const [recorded, setRecorded] = useState<TraceData | null>();
  const [live, setLive] = useState<LiveData | null>(null);
  const [pick, setPick] = useState<string | null>(null);

  useEffect(() => {
    fetch('/trace-data.json')
      .then((r) => (r.ok ? r.json() : null))
      .then(setRecorded)
      .catch(() => setRecorded(null));
  }, []);

  // Poll the snapshot `demo/live_run.py` writes: fast while a run is in flight,
  // slow otherwise so a run started after this page is open still shows up.
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let next: LiveData | null = null;
      try {
        const r = await fetch(`/live-run.json?t=${Date.now()}`, { cache: 'no-store' });
        if (r.ok) next = await r.json();
      } catch {
        next = null;
      }
      if (stopped) return;
      setLive(next);
      timer = setTimeout(poll, next && next.status === 'running' ? 1000 : 5000);
    };
    poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  const liveSessions = live ? [live.current, ...live.recent].filter((x): x is LiveSession => !!x) : [];
  const streaming = liveSessions.length > 0;
  const sessions = streaming ? liveSessions : recorded?.sessions ?? [];
  const depth = (streaming ? live?.rolloutDepth : recorded?.rolloutDepth) ?? 0;

  if (recorded === undefined && !live) return <p>Loading session trace…</p>;
  if (!sessions.length)
    return (
      <>
        <h1>Session trace</h1>
        <section className="panel">
          <h2>Nothing to trace yet</h2>
          <p>Start the official evaluation and this page fills in as it runs, turn by turn:</p>
          <pre>python demo/live_run.py --out dashboard/public/live-run.json</pre>
          <p>Or record one fixed session to keep:</p>
          <pre>python demo/trace_session.py --session public_0068,public_0089 --export dashboard/public/trace-data.json</pre>
        </section>
      </>
    );

  const found = sessions.findIndex((x) => x.sample_id === pick);
  const s = sessions[found < 0 ? 0 : found];
  const inFlight = streaming && live?.status === 'running' && live?.current?.sample_id === s.sample_id;

  return (
    <>
      <h1>Inside one decision</h1>
      {streaming ? (
        <p className="lead">
          This is the evaluation as it happens. <code>demo/live_run.py</code> calls the evaluator's own <code>evaluate()</code> and
          watches the agent from inside that run, so every clue, ranking and rollout below is the planner's own state at the moment
          that turn was answered. The snapshot is rewritten after each turn and this page re-reads it — the session in flight grows a
          card at a time as the agent works through it.
        </p>
      ) : (
        <p className="lead">
          Every number below is the agent's own planner state, captured turn by turn as the session ran rather than reconstructed
          afterwards — this one by <code>demo/trace_session.py</code>, against the same <code>Agent</code> class and simulated
          customer the evaluator drives. Start <code>python demo/live_run.py</code> and this page switches to the evaluation in
          progress, filling in as each turn is answered.
        </p>
      )}

      {live && <LiveStrip live={live} />}

      <div className="seg sessions">
        {sessions.map((x) => (
          <button
            key={x.sample_id}
            className={x.sample_id === s.sample_id ? 'active' : ''}
            onClick={() => setPick(x.sample_id)}
          >
            {x.sample_id}
            {streaming
              ? live?.current?.sample_id === x.sample_id && live?.status === 'running'
                ? ' · in progress'
                : x.hit_turn ? ` · hit turn ${x.hit_turn}` : ' · miss'
              : ` · ${x.turns[0]?.decision.show === 1 ? 'publishes 1' : `publishes ${x.turns[0]?.decision.show}`}`}
          </button>
        ))}
      </div>

      <div className="metrics">
        <div><strong>{s.scenario_type}</strong><span>scenario</span></div>
        <div><strong>{s.difficulty || '—'}</strong><span>difficulty</span></div>
        <div><strong>{s.hit_turn ? `turn ${s.hit_turn}` : inFlight ? 'still searching' : 'miss'}</strong><span>target found</span></div>
        <div><strong>{s.hit_rank ? `rank ${s.hit_rank}` : '—'}</strong><span>at rank</span></div>
        <div><strong>{s.turns.length}</strong><span>{inFlight ? 'turns so far' : 'turns traced'}</span></div>
      </div>

      <section className="panel target">
        <p className="eyebrow">Hidden target · {s.target}</p>
        <h2>{s.target_title}</h2>
        <p className="muted">The agent never sees this. It is marked in the ranking below so you can watch it climb.</p>
      </section>

      {s.turns.map((t) => <TurnCard key={t.turn} t={t} depth={depth} />)}

      {inFlight && (
        <p className="waiting">
          <span className="pip" /> waiting on turn {s.turns.length + 1} — the simulated customer is replying.
        </p>
      )}

      {streaming ? (
        <p className="muted">
          Streaming from <code>demo/live_run.py</code> · run started {new Date(live!.startedAt).toLocaleString()}
          {live!.final?.elapsedSeconds ? ` · finished in ${live!.final.elapsedSeconds}s` : ''}
          {live!.rolloutsTraced ? '' : ' · rollout replay disabled (--no-rollouts)'}.
        </p>
      ) : (
        <p className="muted">
          Traced against {recorded!.catalogSize.toLocaleString()} catalogue rows from {recorded!.dataset} · recorded{' '}
          {new Date(recorded!.generatedAt).toLocaleString()}.
        </p>
      )}
    </>
  );
}
