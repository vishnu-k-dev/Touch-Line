"use client";

import { useEffect, useRef } from "react";

/** A number that counts up from zero the first time it is on screen. Shows the final value without JS or with reduced motion. */
export function CountUp({ to, decimals = 0, ms = 1100 }: { to: number; decimals?: number; ms?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const format = (n: number) => n.toLocaleString("en-GB", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  useEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
    let raf = 0;
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / ms);
        el.textContent = format(to * (1 - Math.pow(1 - t, 3))); // ease-out
        if (t < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    });
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [to, decimals, ms]);
  return (
    <span ref={ref} className="tabular">
      {format(to)}
    </span>
  );
}
