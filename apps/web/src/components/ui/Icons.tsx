const base = { fill: "none", stroke: "currentColor", strokeLinecap: "square", strokeLinejoin: "miter" } as const;

export const CheckIcon = ({ size = 14 }: { size?: number }) => (
  <svg viewBox="0 0 16 16" width={size} height={size} aria-hidden {...base} strokeWidth={2.6}>
    <polyline points="2.5,8.5 6.5,12.5 13.5,3.5" />
  </svg>
);

export const WarnIcon = ({ size = 14 }: { size?: number }) => (
  <svg viewBox="0 0 16 16" width={size} height={size} aria-hidden {...base} strokeWidth={2}>
    <path d="M8 2 L14.5 13.5 H1.5 Z" />
    <line x1="8" y1="6.5" x2="8" y2="10" />
    <line x1="8" y1="11.8" x2="8" y2="12.2" />
  </svg>
);

export const ArrowIcon = ({ size = 16 }: { size?: number }) => (
  <svg viewBox="0 0 16 16" width={size} height={size} aria-hidden {...base} strokeWidth={2}>
    <line x1="2" y1="8" x2="13" y2="8" />
    <polyline points="9,4 13,8 9,12" />
  </svg>
);
