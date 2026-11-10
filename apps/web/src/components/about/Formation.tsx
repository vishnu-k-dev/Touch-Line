"use client";

import { useState } from "react";
import { PitchSvg } from "@/components/match/Pitch";

type Player = { n: number; role: string; label: string; title: string; text: string; where: string; x: number; y: number };

// 4-3-3, attacking right. The goalkeeper is the last line of defence: the database everything else leans on.
const XI: Player[] = [
  { n: 1, role: "GK", label: "Postgres", title: "PostgreSQL + pgvector", x: 8, y: 40, where: "infra/docker-compose.yml",
    text: "One database for matches, events, shots and embeddings. The last line of defence: every number traces back to a stored StatsBomb event." },
  { n: 2, role: "DEF", label: "Alembic", title: "Alembic migrations", x: 30, y: 12, where: "apps/api/migrations",
    text: "Schema changes are reviewed files, not accidents. CI runs `alembic check` and fails if the models and migrations disagree." },
  { n: 3, role: "DEF", label: "Models", title: "SQLAlchemy models", x: 30, y: 30, where: "apps/api/app/models/tables.py",
    text: "Typed tables, with the original event JSON kept in JSONB so no field is ever lost. Chat history lives here too." },
  { n: 4, role: "DEF", label: "Ingest", title: "Ingestion pipeline", x: 30, y: 50, where: "apps/api/app/services/ingest.py",
    text: "StatsBomb files become events, shots, minutes and 360 context. Idempotent. Handles penalty-shootout kicks and the extra-time clock reset." },
  { n: 5, role: "DEF", label: "Docker", title: "Docker + CI", x: 30, y: 68, where: "apps/api/Dockerfile, .github/workflows",
    text: "Compose runs database, API and web. The API container bootstraps itself on first start: migrate, load data, build the index." },
  { n: 6, role: "MID", label: "Analytics", title: "Analytics engine", x: 58, y: 20, where: "apps/api/app/services/analytics.py",
    text: "xG, PPDA, minutes played, heatmaps and shooting-lane context, each recounted from the raw JSON in tests." },
  { n: 7, role: "MID", label: "RAG", title: "Search (RAG)", x: 58, y: 40, where: "apps/api/app/services/rag.py",
    text: "A local bge-small model embeds 156 documents. pgvector finds them by meaning; exact filters catch attributes like corners and headers." },
  { n: 8, role: "MID", label: "Tools", title: "The tool layer", x: 58, y: 60, where: "apps/api/app/tools/football.py",
    text: "Eight tools with validated arguments, bounded results, and error messages the model can recover from." },
  { n: 9, role: "FWD", label: "FastAPI", title: "FastAPI", x: 92, y: 16, where: "apps/api/app/api/routes.py",
    text: "A typed REST API with per-visitor rate limits, a daily spend cap on the model, request tracing, and a readiness check." },
  { n: 10, role: "FWD", label: "Agent + VAR", title: "Agent loop + VAR check", x: 92, y: 40, where: "apps/api/app/agents/analyst.py",
    text: "A custom tool loop. Every finding must cite its tool calls and event ids; the validator checks each number against what the tools returned." },
  { n: 11, role: "FWD", label: "Next.js", title: "Next.js front end", x: 92, y: 64, where: "apps/web",
    text: "This site: the Match Centre, heatmaps, and an analyst whose evidence links open the exact shot on the map." },
];

export function Formation() {
  const [active, setActive] = useState<number>(10);
  const p = XI.find((x) => x.n === active)!;
  return (
    <div>
      <PitchSvg label="The technology stack drawn as a football formation: eleven players from goalkeeper to forwards. Select a player to read what it does.">
        {XI.map((x) => {
          const on = x.n === active;
          return (
            <g
              key={x.n}
              role="button"
              tabIndex={0}
              aria-label={`${x.n}, ${x.title}`}
              aria-pressed={on}
              onMouseEnter={() => setActive(x.n)}
              onFocus={() => setActive(x.n)}
              onClick={() => setActive(x.n)}
              className="cursor-pointer outline-none"
            >
              <g className="transition-transform duration-200 ease-out hover:scale-[1.18] focus-visible:scale-[1.18]" style={{ transformBox: "fill-box", transformOrigin: "center", transform: on ? "scale(1.18)" : undefined }}>
                {on && <circle cx={x.x} cy={x.y} r={5.4} fill="none" stroke="var(--card)" strokeWidth={0.8} style={{ transformBox: "fill-box", transformOrigin: "center", animation: "ring 1.4s ease-out infinite" }} />}
                <circle cx={x.x} cy={x.y} r={4.6} fill={x.role === "GK" ? "var(--card)" : "var(--home)"} stroke={on ? "var(--card)" : "var(--rule)"} strokeWidth={on ? 1 : 0.7} />
                <text x={x.x} y={x.y + 1.9} textAnchor="middle" fontSize={5.6} fontWeight={800} fill={x.role === "GK" ? "var(--card-fg)" : "#0a100d"} style={{ fontFamily: "var(--font-barlow)" }}>
                  {x.n}
                </text>
              </g>
              <text x={x.x} y={x.y + 9.6} textAnchor="middle" fontSize={3.3} fontWeight={700} fill="#f1eedf" stroke="rgba(0,0,0,0.45)" strokeWidth={0.5} paintOrder="stroke" style={{ fontFamily: "var(--font-barlow)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                {x.label}
              </text>
            </g>
          );
        })}
      </PitchSvg>
      <div key={p.n} className="anim-slide-up mt-4 grid gap-3 border-2 border-rule bg-surface p-4 sm:grid-cols-[auto_1fr]" aria-live="polite">
        <div className="flex items-center gap-3 sm:flex-col sm:items-start sm:gap-1">
          <span className="grid h-14 w-14 place-items-center bg-rule font-display text-4xl font-extrabold text-bg">{p.n}</span>
          <span className="font-display text-sm font-semibold uppercase tracking-[0.2em] text-muted">{p.role}</span>
        </div>
        <div>
          <h3 className="font-display text-3xl font-bold uppercase leading-none">{p.title}</h3>
          <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-muted">{p.text}</p>
          <p className="mt-2 font-mono text-xs text-turf">{p.where}</p>
        </div>
      </div>
    </div>
  );
}
