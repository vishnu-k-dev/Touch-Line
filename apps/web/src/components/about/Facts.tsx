import { CountUp } from "@/components/ui/CountUp";
import { Reveal } from "@/components/ui/Reveal";
import { ANALYST_EVAL, FACTS } from "@/content/facts";

const CARDS = [
  { value: <CountUp to={FACTS.apiTests} />, label: "API tests", note: "Metrics recounted from the raw StatsBomb JSON, the official scores, and known facts." },
  { value: <CountUp to={FACTS.unitTests + FACTS.e2eTests} />, label: "Browser and unit tests", note: "Playwright drives the real API; only the language model is mocked." },
  { value: <CountUp to={FACTS.retrievalRecall} decimals={2} />, label: `Search recall@3 (${FACTS.retrievalQuestions} questions)`, note: `Started at ${FACTS.firstRunRecall.toFixed(2)}; fixed by rewording documents, not by editing the questions.` },
  { value: <CountUp to={FACTS.teamPlayersOnPitch} />, label: "Players per team, every match", note: "Minutes played are checked: each side always adds up to eleven on the pitch." },
  { value: <>{FACTS.blockedShotsZeroDefenders}<span className="text-muted">/{FACTS.blockedShotsChecked}</span></>, label: "Blocked shots with no visible defender", note: "So the 360 shooting-lane count is a lower bound. The app says so." },
  { value: <><CountUp to={FACTS.apiMemoryMiB} /><span className="text-2xl text-muted"> MiB</span></>, label: "API memory, model loaded", note: "Measured in Docker, so a 1 GB host has room to spare." },
];

export function Facts() {
  return (
    <div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((c, i) => (
          <Reveal key={c.label} delay={(i % 3) * 90}>
            <div className="lift h-full border-2 border-rule bg-surface p-4">
              <p className="font-display text-6xl font-extrabold leading-none tabular">{c.value}</p>
              <p className="mt-2 font-display text-lg font-bold uppercase leading-tight tracking-wide">{c.label}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted">{c.note}</p>
            </div>
          </Reveal>
        ))}
      </div>
      <div className="mt-4 border-2 border-dashed border-line p-4 text-sm leading-relaxed">
        <p className="font-display text-lg font-bold uppercase tracking-wide">The analyst itself</p>
        {ANALYST_EVAL ? (
          <p className="mt-1 text-muted">
            On nine golden questions ({ANALYST_EVAL.model}, live): {Math.round(ANALYST_EVAL.passRate * 100)}% passed and {Math.round(ANALYST_EVAL.grounded * 100)}% of findings were
            verified, at a median {ANALYST_EVAL.medianLatencyS} s and about ${ANALYST_EVAL.costPerQuestionUsd.toFixed(3)} per question. The first run scored{" "}
            {Math.round(ANALYST_EVAL.firstRunPassRate * 100)}%: the one miss was a miscounted tally, fixed by making the tool return the totals. Nine questions is a smoke test, not a
            benchmark.
          </p>
        ) : (
          <p className="mt-1 text-muted">
            Its headline accuracy isn&apos;t published yet. The evaluation harness ships with the code (nine questions with ground truth taken from the database, two of which the data
            can&apos;t answer, so declining is correct), and the numbers go here after its first full run.
          </p>
        )}
      </div>
    </div>
  );
}

const ROWS = [
  { set: "Concept questions", n: 20, first: "0.90 recall@3 · 0.85 top-1", now: "1.00 · 0.95" },
  { set: "Which match was it?", n: 4, first: "0.50 top-1", now: "0.75 top-1 · 1.00 in top 3" },
  { set: "Find a named moment", n: 5, first: "1.00 hit@3", now: "1.00" },
  { set: "Attribute only (“goal from a counter-attack”)", n: 4, first: "0 of 3 right", now: "same: that is why exact filters exist" },
];

export function RetrievalTable() {
  return (
    <div className="overflow-x-auto border-2 border-rule bg-surface">
      <table className="w-full min-w-[560px] text-sm">
        <thead className="bg-rule text-left text-[#f1eedf]">
          <tr>
            {["Question set", "Queries", "First run", "After fixing the documents"].map((h) => (
              <th key={h} className="px-3 py-2 font-display text-sm font-semibold uppercase tracking-[0.14em]">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {ROWS.map((r) => (
            <tr key={r.set} className="transition-colors hover:bg-surface2">
              <td className="px-3 py-2 font-medium">{r.set}</td>
              <td className="tabular px-3 py-2">{r.n}</td>
              <td className="px-3 py-2 text-muted">{r.first}</td>
              <td className="px-3 py-2 font-medium">{r.now}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
