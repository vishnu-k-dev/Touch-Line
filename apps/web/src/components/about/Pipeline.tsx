import { Reveal } from "@/components/ui/Reveal";

const STEPS = [
  { n: 1, name: "Ingest", text: "StatsBomb events, lineups and 360 frames load into Postgres, with the full raw JSON kept.", proof: "Idempotent. Shootout kicks and the extra-time clock reset handled." },
  { n: 2, name: "Measure", text: "xG, PPDA, minutes, heatmaps and shooting-lane context are computed from those events.", proof: "Recounted from the raw files in tests." },
  { n: 3, name: "Retrieve", text: "156 documents are embedded with a local model. pgvector finds them by meaning; exact filters catch attributes.", proof: "recall@3 of 1.00 on 20 questions." },
  { n: 4, name: "Reason", text: "A language model picks from eight validated tools, up to eight turns, and submits structured findings.", proof: "OpenAI by default; Anthropic also wired in." },
  { n: 5, name: "Check", text: "The validator checks every cited number and event id against the tool results. Failures go back once, then get flagged.", proof: "Each rule broken on purpose to prove tests catch it." },
];

export function Pipeline() {
  return (
    <ol className="grid gap-4 md:grid-cols-5">
      {STEPS.map((s, i) => (
        <li key={s.n}>
          <Reveal delay={i * 100} className="h-full">
            <div className="lift group relative h-full border-2 border-rule bg-surface p-4">
              <div className="flex items-center gap-2">
                <span className="grid h-9 w-9 place-items-center bg-rule font-display text-2xl font-extrabold text-bg transition-colors group-hover:bg-card group-hover:text-cardfg">{s.n}</span>
                <h3 className="font-display text-2xl font-bold uppercase leading-none">{s.name}</h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted">{s.text}</p>
              <p className="mt-3 border-t border-line pt-2 font-display text-sm font-semibold uppercase tracking-wide text-turf">{s.proof}</p>
              {i < STEPS.length - 1 && (
                <span aria-hidden className="absolute -right-3 top-8 z-10 hidden h-0.5 w-6 bg-rule md:block">
                  <span className="absolute -right-0.5 -top-[3px] h-2 w-2 rotate-45 border-r-2 border-t-2 border-rule" />
                </span>
              )}
            </div>
          </Reveal>
        </li>
      ))}
    </ol>
  );
}
