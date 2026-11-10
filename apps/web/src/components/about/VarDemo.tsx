"use client";

import { useState } from "react";
import { CheckIcon, WarnIcon } from "@/components/ui/Icons";
import { varCheck } from "@/lib/var";

// A slice of a real tool result (get_match_summary for Argentina 1-2 Saudi Arabia).
const RESULT = { call_id: "c1", home: { team: "Argentina", goals: 1, shots: 15, xg: 2.49 }, away: { team: "Saudi Arabia", goals: 2, shots: 3, xg: 0.15 } };
const NUMBERS = [RESULT.home.goals, RESULT.home.shots, RESULT.home.xg, RESULT.away.goals, RESULT.away.shots, RESULT.away.xg];
const PRESETS = [
  { v: "2.49", note: "what the tool said" },
  { v: "3.5", note: "made up" },
  { v: "2.34", note: "a gap: 2.49 − 0.15" },
];

export function VarDemo() {
  const [raw, setRaw] = useState("2.49");
  const value = Number(raw);
  const valid = raw.trim() !== "" && Number.isFinite(value);
  const verdict = valid ? varCheck(value, NUMBERS) : null;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <p className="mb-2 font-display text-sm font-semibold uppercase tracking-[0.2em] text-muted">1 · What the database returned (tool call c1)</p>
        <pre className="overflow-x-auto border-2 border-rule bg-[#0a100d] p-4 font-mono text-[13px] leading-relaxed text-[#f1eedf]">
          {`{
  "call_id": "c1",
  "home": { "team": "Argentina",
            "goals": `}
          <b className="text-card">1</b>
          {`, "shots": `}
          <b className="text-card">15</b>
          {`,
            "xg": `}
          <b className="text-card">2.49</b>
          {` },
  "away": { "team": "Saudi Arabia",
            "goals": `}
          <b className="text-card">2</b>
          {`, "shots": `}
          <b className="text-card">3</b>
          {`,
            "xg": `}
          <b className="text-card">0.15</b>
          {` }
}`}
        </pre>
      </div>

      <div>
        <p className="mb-2 font-display text-sm font-semibold uppercase tracking-[0.2em] text-muted">2 · What the analyst claims. Try to fool it.</p>
        <div className="border-2 border-rule bg-surface p-4">
          <p className="text-[15px]">
            “Argentina&apos;s expected goals were{" "}
            <input
              aria-label="Claimed xG for Argentina"
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              inputMode="decimal"
              className="tabular w-20 border-b-2 border-rule bg-bg px-1 text-center font-display text-2xl font-bold focus:bg-card focus:text-cardfg"
            />
            ,” citing <code className="bg-surface2 px-1">c1</code>.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.v}
                onClick={() => setRaw(p.v)}
                className={`border-2 px-2.5 py-1 text-left text-xs transition-colors hover:border-rule hover:bg-card hover:text-cardfg ${raw === p.v ? "border-rule bg-surface2" : "border-line"}`}
              >
                <span className="font-display text-base font-bold">{p.v}</span> <span className="text-muted">{p.note}</span>
              </button>
            ))}
          </div>

          <div aria-live="polite" className="mt-4 min-h-[8.5rem]">
            {verdict ? (
              <div key={`${verdict.ok}-${raw}`} className="anim-pop origin-left">
                <div className={`inline-flex items-center gap-2 border-[3px] px-3 py-1.5 font-display text-2xl font-extrabold uppercase tracking-wide ${verdict.ok ? "border-ok text-ok" : "border-red text-red"}`}>
                  {verdict.ok ? <CheckIcon size={22} /> : <WarnIcon size={22} />}
                  VAR: {verdict.ok ? "goal stands" : "no goal"}
                </div>
                <p className="mt-2 text-sm">{verdict.detail}</p>
                <p className="mt-2 text-xs leading-relaxed text-muted">
                  {verdict.ok
                    ? "The finding is shown with a green VAR badge."
                    : "The real system sends this back to the model once with the exact complaint. If the model can't fix it, the finding is returned flagged “under review”, never silently accepted."}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted">Type a number.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
