/** Small Moon phase icon for the Moon line on Today. */

const ILLUMINATION: Record<string, { lit: number; waxing: boolean }> = {
  new_moon: { lit: 0, waxing: true },
  waxing_crescent: { lit: 0.25, waxing: true },
  first_quarter: { lit: 0.5, waxing: true },
  waxing_gibbous: { lit: 0.75, waxing: true },
  full_moon: { lit: 1, waxing: true },
  waning_gibbous: { lit: 0.75, waxing: false },
  last_quarter: { lit: 0.5, waxing: false },
  waning_crescent: { lit: 0.25, waxing: false },
};

/** Lit part of a moon of radius 10 around (12, 12), lit from the right (waxing, northern hemisphere). */
export function litPath(lit: number): string {
  if (lit <= 0) return "";
  if (lit >= 1) return "M12 2 A10 10 0 1 1 12 22 A10 10 0 1 1 12 2Z";
  const rx = Math.abs(1 - 2 * lit) * 10;
  const sweep = lit > 0.5 ? 1 : 0; // gibbous: the terminator bulges to the left
  return `M12 2 A10 10 0 0 1 12 22 A${rx.toFixed(2)} 10 0 0 ${sweep} 12 2Z`;
}

export function MoonPhaseIcon({ phase }: { phase: string }) {
  const { lit, waxing } = ILLUMINATION[phase] ?? ILLUMINATION.full_moon;
  return (
    <svg className="moon-phase" viewBox="0 0 24 24" width="1.15em" height="1.15em" aria-hidden="true">
      <circle cx="12" cy="12" r="10" className="moon-dark" />
      <path d={litPath(lit)} className="moon-lit" transform={waxing ? undefined : "matrix(-1 0 0 1 24 0)"} />
    </svg>
  );
}
