"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { BallMark } from "@/components/site/BallMark";
import { Badge } from "@/components/ui/Badge";
import { CheckIcon, WarnIcon } from "@/components/ui/Icons";
import { ApiError, apiDelete, apiGet, apiPost, useApi } from "@/lib/api";
import { shortId } from "@/lib/format";
import type { AnalystResult, AnalystStatus, Finding, HistoryTurn, Match, MatchStats } from "@/lib/types";
import { visitorHeaders } from "@/lib/visitor";

type Turn = { key: string; question: string; state: "loading" | "done" | "error"; result?: AnalystResult; error?: { status: number; text: string }; at?: string };

function suggestions(match: Match, stats: MatchStats | undefined): string[] {
  const out: string[] = [];
  if (stats) {
    const lead = stats.home.xg >= stats.away.xg ? stats.home : stats.away;
    const other = lead === stats.home ? stats.away : stats.home;
    out.push(lead.goals > other.goals ? `How did ${lead.team} turn their chances into a win over ${other.team}?` : `Why did ${lead.team} create more chances but not win?`);
  }
  out.push("Which team pressed harder, and how do you know?", "Who was the most dangerous player and from what kind of chances?", "How many shots had no visible defender in the shooting lane?", "What formation did each team play?");
  return out;
}

function Elapsed() {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const t0 = Date.now();
    const id = setInterval(() => setSecs(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);
  return <>{secs}s</>;
}

function Evidence({ id, onShow }: { id: string; onShow: (id: string) => void }) {
  return (
    <button
      onClick={() => onShow(id)}
      title={`StatsBomb event ${id}. Click to show it on the shot map (or copy the id).`}
      className="border-2 border-line bg-surface2 px-1.5 py-0.5 font-mono text-[11px] transition-colors hover:border-rule hover:bg-card hover:text-cardfg"
    >
      {shortId(id)}
    </button>
  );
}

function FindingCard({ f, onShow, index }: { f: Finding; onShow: (id: string) => void; index: number }) {
  return (
    <li className={`anim-slide-up border-2 bg-surface p-3 ${f.verified ? "border-line" : "border-warn"}`} style={{ animationDelay: `${index * 90}ms` }}>
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
        <Badge tone={f.verified ? "ok" : "review"} className="anim-pop mt-0.5 shrink-0">
          {f.verified ? <CheckIcon /> : <WarnIcon />}
          {f.verified ? "VAR: goal stands" : "VAR: under review"}
        </Badge>
        <p className="min-w-0 flex-1 text-[15px] leading-snug">{f.claim}</p>
      </div>
      {Object.keys(f.values).length > 0 && (
        <dl className="tabular mt-2.5 flex flex-wrap gap-x-6 gap-y-1">
          {Object.entries(f.values).map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-1.5">
              <dt className="text-sm text-muted">{k}</dt>
              <dd className="font-display text-2xl font-bold leading-none">{typeof v === "number" ? String(Math.round(v * 100) / 100) : v}</dd>
            </div>
          ))}
        </dl>
      )}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5 text-xs text-muted">
        <span>source{f.sources.length > 1 ? "s" : ""}:</span>
        {f.sources.map((s) => (
          <code key={s} className="bg-surface2 px-1">{s}</code>
        ))}
        {f.evidence.length > 0 && <span className="ml-2">events:</span>}
        {f.evidence.slice(0, 6).map((e) => (
          <Evidence key={e} id={e} onShow={onShow} />
        ))}
        {f.evidence.length > 6 && <span>+{f.evidence.length - 6}</span>}
      </div>
      {!f.verified && <p className="mt-2 text-xs text-warn">{f.problems.join(" · ")}</p>}
    </li>
  );
}

const H3 = "mb-1.5 font-display text-sm font-semibold uppercase tracking-[0.2em] text-muted";

function TurnView({ turn, onShow }: { turn: Turn; onShow: (id: string) => void }) {
  const r = turn.result;
  return (
    <article className="space-y-3">
      <p className="anim-slide-up ml-auto w-fit max-w-[90%] border-2 border-rule bg-card px-3.5 py-2 text-sm font-medium text-cardfg shadow-[3px_3px_0_var(--rule)]">{turn.question}</p>
      {turn.state === "loading" && (
        <p className="flex items-center gap-3 text-sm text-muted" aria-live="polite">
          <span className="anim-spin inline-block">
            <BallMark size={22} />
          </span>
          Checking the monitor… <Elapsed />
        </p>
      )}
      {turn.state === "error" && (
        <div className="anim-slide-up border-2 border-rule bg-surface p-3 text-sm" role="alert">
          <p className="font-display text-xl font-bold uppercase text-red">{turn.error?.status === 503 ? "The VAR room is closed" : "Own goal: the analyst couldn't answer"}</p>
          <p className="mt-1 text-muted">{turn.error?.text}</p>
        </div>
      )}
      {r && (
        <div className="space-y-3">
          {r.status === "unverified" && <p className="border-2 border-warn px-3 py-2 text-sm text-warn">Some findings could not be checked against the tool results and are flagged below.</p>}
          {(r.status === "incomplete" || r.status === "refused") && <p className="border-2 border-line bg-surface px-3 py-2 text-sm">{r.message}</p>}
          {r.answer && r.answer.findings.length > 0 && (
            <section aria-label="Measured findings">
              <h3 className={H3}>Measured findings</h3>
              <ul className="space-y-2">{r.answer.findings.map((f, i) => <FindingCard key={i} f={f} onShow={onShow} index={i} />)}</ul>
            </section>
          )}
          {r.answer?.interpretation && (
            <section aria-label="Interpretation" className="border-2 border-dashed border-line bg-surface p-3">
              <h3 className={H3}>Inference (not measured, may be wrong)</h3>
              <p className="text-sm leading-relaxed">{r.answer.interpretation}</p>
            </section>
          )}
          {r.answer && r.answer.limitations.length > 0 && (
            <section aria-label="Limitations">
              <h3 className={H3}>Limitations</h3>
              <ul className="list-disc space-y-0.5 pl-5 text-sm text-muted">{r.answer.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
            </section>
          )}
          <details className="border-2 border-line bg-surface text-sm">
            <summary className="cursor-pointer px-3 py-2 text-muted hover:text-fg">
              How it answered: {r.usage.tool_calls} tool call{r.usage.tool_calls === 1 ? "" : "s"} · {r.usage.steps} model turn{r.usage.steps === 1 ? "" : "s"} · {(r.usage.latency_ms / 1000).toFixed(1)}s
              {r.usage.cost_usd != null && ` · $${r.usage.cost_usd.toFixed(3)}`}
            </summary>
            <ol className="divide-y divide-line border-t border-line">
              {r.trace.map((t) => (
                <li key={t.call_id} className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <code className="bg-surface2 px-1 text-xs">{t.call_id}</code>
                    <span className="font-mono text-xs font-medium">{t.tool}</span>
                    <span className={t.ok ? "text-ok" : "text-red"}>{t.ok ? "ok" : "error"}</span>
                    <span className="tabular ml-auto text-xs text-muted">{t.ms} ms</span>
                  </div>
                  <p className="mt-1 break-all font-mono text-[11px] text-muted">{JSON.stringify(t.args)}</p>
                  <p className="mt-0.5 text-xs text-muted">{t.summary}</p>
                </li>
              ))}
            </ol>
            <p className="tabular border-t border-line px-3 py-2 text-xs text-muted">
              {r.usage.model} · {r.usage.input_tokens.toLocaleString()} in / {r.usage.output_tokens.toLocaleString()} out tokens
              {r.usage.cache_read_tokens > 0 && ` (${r.usage.cache_read_tokens.toLocaleString()} cached)`}
              {r.validation.passed ? " · all citations verified" : r.validation.violations.length ? ` · ${r.validation.violations.length} unverified claim(s)` : ""}
            </p>
          </details>
        </div>
      )}
    </article>
  );
}

export function Analyst({ match, stats, onShowEvidence }: { match: Match; stats: MatchStats | undefined; onShowEvidence: (id: string) => void }) {
  const status = useApi<AnalystStatus>("/api/v1/analyst/status");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [restored, setRestored] = useState(0);
  const [question, setQuestion] = useState("");
  const nextKey = useRef(1);
  const end = useRef<HTMLDivElement>(null);
  const busy = turns.some((t) => t.state === "loading");

  // Pick up where the visitor left off: earlier questions for this match come back from the server.
  useEffect(() => {
    const ctl = new AbortController();
    apiGet<HistoryTurn[]>(`/api/v1/analyst/history?match_id=${match.id}`, ctl.signal, visitorHeaders()).then(
      (history) => {
        if (!history.length) return;
        setRestored(history.length);
        setTurns((now) => [...history.map((h): Turn => ({ key: `h${h.id}`, question: h.question, state: "done", result: h.result, at: h.created_at })), ...now]);
      },
      () => {}, // history is a convenience: the analyst still works without it
    );
    return () => ctl.abort();
  }, [match.id]);

  useEffect(() => {
    if (turns.length) end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns.length]);

  function ask(q: string) {
    const text = q.trim();
    if (text.length < 3 || busy) return;
    const key = `n${nextKey.current++}`;
    setQuestion("");
    setTurns((ts) => [...ts, { key, question: text, state: "loading" }]);
    apiPost<AnalystResult>("/api/v1/analyst/chat", { question: text, match_id: match.id }, undefined, visitorHeaders()).then(
      (result) => setTurns((ts) => ts.map((t) => (t.key === key ? { ...t, state: "done", result } : t))),
      (e: Error) => setTurns((ts) => ts.map((t) => (t.key === key ? { ...t, state: "error", error: { status: e instanceof ApiError ? e.status : 0, text: e.message } } : t))),
    );
  }

  function clearHistory() {
    apiDelete(`/api/v1/analyst/history?match_id=${match.id}`, visitorHeaders()).then(
      () => {
        setTurns([]);
        setRestored(0);
      },
      () => {},
    );
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    ask(question);
  };

  return (
    <div className="space-y-5">
      <div className="border-2 border-rule bg-surface px-4 py-3 text-sm">
        <p className="font-display text-xl font-bold uppercase leading-none">The VAR room</p>
        <p className="mt-1.5 text-muted">
          Every number the analyst states must come from a tool result, and each finding cites the call and the events behind it. Anything it can&apos;t support goes under limitations.
        </p>
        {status.data && !status.data.configured && (
          <p className="mt-2 font-medium text-warn">The VAR room is closed: no LLM key is configured on this server. The rest of the stadium is open.</p>
        )}
      </div>

      {restored > 0 && (
        <p className="anim-fade flex flex-wrap items-center gap-3 border-l-4 border-card bg-surface2 px-3 py-2 text-sm">
          Picked up where you left off: {restored} earlier question{restored === 1 ? "" : "s"} on this match.
          <button onClick={clearHistory} className="font-display text-sm font-semibold uppercase tracking-wider text-muted underline decoration-2 underline-offset-2 hover:text-red">
            Clear history
          </button>
        </p>
      )}

      <div className="space-y-7" aria-live="polite">
        {turns.map((t) => (
          <TurnView key={t.key} turn={t} onShow={onShowEvidence} />
        ))}
        <div ref={end} />
      </div>

      {turns.length === 0 && (
        <div>
          <p className="mb-2 font-display text-sm font-semibold uppercase tracking-[0.2em] text-muted">Team sheet · pick a question</p>
          <div className="flex flex-wrap gap-2">
            {suggestions(match, stats).map((s, i) => (
              <button key={s} onClick={() => ask(s)} disabled={busy} className="lift group flex items-center gap-2 border-2 border-rule bg-surface py-1.5 pl-1.5 pr-3 text-left text-sm disabled:opacity-50">
                <span className="grid h-6 w-6 shrink-0 place-items-center bg-rule font-display text-sm font-bold text-bg transition-colors group-hover:bg-card group-hover:text-cardfg">{i + 1}</span>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={onSubmit} className="flex gap-2">
        <label htmlFor="q" className="sr-only">Ask the analyst about this match</label>
        <input
          id="q"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={500}
          placeholder={`Ask about ${match.home_team.name} v ${match.away_team.name}…`}
          className="min-w-0 flex-1 border-2 border-rule bg-surface px-3 py-2 text-sm placeholder:text-muted focus:bg-bg"
        />
        <button
          disabled={busy || question.trim().length < 3}
          className="border-2 border-rule bg-card px-5 py-2 font-display text-lg font-bold uppercase tracking-wide text-cardfg shadow-[3px_3px_0_var(--rule)] transition-all enabled:hover:-translate-x-0.5 enabled:hover:-translate-y-0.5 enabled:hover:shadow-[5px_5px_0_var(--rule)] disabled:opacity-40 disabled:shadow-none"
        >
          {busy ? "On the VAR…" : "Ask"}
        </button>
      </form>
    </div>
  );
}
