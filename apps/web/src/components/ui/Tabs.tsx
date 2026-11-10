"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";

export type TabDef<T extends string> = { id: T; label: string; hint?: string };

/** Accessible tab list with an underline that slides to the active tab and arrow-key navigation. */
export function Tabs<T extends string>({ tabs, value, onChange, label }: { tabs: TabDef<T>[]; value: T; onChange: (id: T) => void; label: string }) {
  const list = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const move = () => {
      const active = list.current?.querySelector<HTMLElement>('[aria-selected="true"]');
      if (active && bar.current) {
        bar.current.style.width = `${active.offsetWidth}px`;
        bar.current.style.transform = `translateX(${active.offsetLeft}px)`;
      }
    };
    move();
    window.addEventListener("resize", move);
    return () => window.removeEventListener("resize", move);
  }, [value, tabs]);

  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = tabs.findIndex((t) => t.id === value);
    const next = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : null;
    if (next === null) return;
    e.preventDefault();
    const t = tabs[(next + tabs.length) % tabs.length];
    onChange(t.id);
    list.current?.querySelector<HTMLElement>(`[data-tab="${t.id}"]`)?.focus();
  };

  return (
    <div ref={list} role="tablist" aria-label={label} onKeyDown={onKey} className="relative flex gap-1 overflow-x-auto border-b-2 border-rule">
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          data-tab={t.id}
          aria-selected={value === t.id}
          tabIndex={value === t.id ? 0 : -1}
          onClick={() => onChange(t.id)}
          className={`group relative shrink-0 px-4 py-2.5 text-left font-display text-lg font-semibold uppercase leading-none tracking-wide transition-colors ${value === t.id ? "text-fg" : "text-muted hover:text-fg"}`}
        >
          {t.label}
          {t.hint && <span className="mt-0.5 block font-sans text-[10px] font-normal normal-case tracking-normal text-muted">{t.hint}</span>}
        </button>
      ))}
      <span ref={bar} aria-hidden className="absolute -bottom-0.5 left-0 h-1 bg-card transition-[transform,width] duration-300 ease-out" />
    </div>
  );
}
