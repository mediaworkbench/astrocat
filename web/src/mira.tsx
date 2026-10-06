/**
 * Mira, the cat (concept §3). One character illustration, five moods:
 * each pose adds its own light, motion and small decorations. Real pose
 * illustrations can be dropped into src/assets/poses/<pose>.webp later;
 * they replace the base image for that pose automatically.
 */

import { useTranslation } from "react-i18next";

import baseUrl from "./assets/mira.webp";

export const POSES = ["sleepy", "cautious", "calm", "playful", "radiant"] as const;
export type Pose = (typeof POSES)[number];

const poseImages = import.meta.glob<string>("./assets/poses/*.webp", { eager: true, import: "default" });

function poseImage(pose: Pose | undefined): string | undefined {
  return pose && poseImages[`./assets/poses/${pose}.webp`];
}

function isPose(value: string | undefined): value is Pose {
  return value !== undefined && (POSES as readonly string[]).includes(value);
}

/** Small four-pointed sparkle, used by several poses. */
function Sparkle({ x, y, size, delay }: { x: number; y: number; size: number; delay: number }) {
  return (
    <path
      className="sparkle"
      style={{ animationDelay: `${delay}s` }}
      transform={`translate(${x} ${y}) scale(${size})`}
      d="M0 -10 C1 -3 3 -1 10 0 C3 1 1 3 0 10 C-1 3 -3 1 -10 0 C-3 -1 -1 -3 0 -10Z"
    />
  );
}

/** Three rising z's, starting at (x, y) and drifting up to the right. */
function Zzz({ x, y }: { x: number; y: number }) {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <text key={i} className="zzz" x={x + i * 7} y={y - i * 9} style={{ animationDelay: `${i * 1.2}s` }}>
          z
        </text>
      ))}
    </>
  );
}

/**
 * Decorations drawn around Mira in a 100 × 100 box over the image. Dedicated
 * pose illustrations bring their own (cloud, star, sparkles), so only the
 * light extras stay for them.
 */
function Decorations({ pose, dedicated }: { pose: Pose; dedicated: boolean }) {
  if (dedicated) {
    if (pose === "sleepy") return <Zzz x={54} y={40} />; // just above her head, which rests on the left
    // calm: the illustration has its own sparkles
    return null;
  }
  switch (pose) {
    case "sleepy":
      return (
        <>
          <Zzz x={82} y={30} />
        </>
      );
    case "cautious":
      return (
        <g className="cloud">
          <path d="M8 92 q0 -9 9 -9 q2 -7 10 -7 q8 0 10 7 q8 0 8 8 q0 6 -6 6 h-25 q-6 0 -6 -5z" />
          <path d="M66 95 q0 -7 7 -7 q2 -5 8 -5 q7 0 8 6 q6 0 6 6 q0 4 -5 4 h-19 q-5 0 -5 -4z" />
        </g>
      );
    case "calm":
      return (
        <>
          <Sparkle x={10} y={14} size={0.35} delay={0} />
          <Sparkle x={90} y={30} size={0.28} delay={1.6} />
        </>
      );
    case "playful":
      return (
        <>
          <g className="orbit">
            <Sparkle x={50} y={4} size={0.5} delay={0} />
          </g>
          <Sparkle x={8} y={60} size={0.3} delay={0.4} />
          <Sparkle x={94} y={50} size={0.3} delay={1.1} />
        </>
      );
    case "radiant":
      return (
        <>
          <Sparkle x={6} y={12} size={0.45} delay={0} />
          <Sparkle x={92} y={8} size={0.55} delay={0.5} />
          <Sparkle x={97} y={48} size={0.35} delay={1} />
          <Sparkle x={4} y={52} size={0.38} delay={1.5} />
          <Sparkle x={78} y={86} size={0.3} delay={0.8} />
          <Sparkle x={20} y={88} size={0.32} delay={1.9} />
        </>
      );
  }
}

export function Mira({ pose, small, reading }: { pose?: string; small?: boolean; reading?: boolean }) {
  const p: Pose | undefined = isPose(pose) ? pose : undefined;
  const dedicated = reading ? undefined : poseImage(p);
  const classes = ["mira", small ? "small" : "", reading ? "reading" : ""].filter(Boolean).join(" ");
  return (
    <div className={classes} data-pose={p ?? "calm"} data-art={dedicated ? "pose" : "base"}>
      <div className="mira-glow" aria-hidden="true" />
      <div className="mira-body">
        <img src={dedicated ?? baseUrl} alt="Mira" draggable={false} />
        {reading && <div className="card-glow" aria-hidden="true" />}
      </div>
      {(p || reading) && (
        <svg className="mira-deco" viewBox="0 0 100 100" aria-hidden="true">
          {reading ? (
            <g className="orbit slow">
              <Sparkle x={50} y={2} size={0.45} delay={0} />
              <Sparkle x={50} y={98} size={0.32} delay={0.7} />
            </g>
          ) : (
            p && <Decorations pose={p} dedicated={Boolean(dedicated)} />
          )}
        </svg>
      )}
    </div>
  );
}

export function MiraLoading({ slow }: { slow?: boolean }) {
  const { t } = useTranslation();
  return (
    <div className="center-screen fade-in" role="status" aria-live="polite">
      <Mira reading />
      <p className="advice">{t("today.generating")}</p>
      <div className="dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      {slow && <p className="muted small">{t("today.generatingSlow")}</p>}
    </div>
  );
}

/** Development only: all poses side by side, for review screenshots. */
export function PoseGallery() {
  return (
    <main className="page stack">
      <h1>Mira</h1>
      {POSES.map((pose) => (
        <section key={pose} className="card stack-sm" style={{ textAlign: "center" }}>
          <h3>{pose}</h3>
          <Mira pose={pose} />
        </section>
      ))}
      <section className="card stack-sm" style={{ textAlign: "center" }}>
        <h3>reading the stars</h3>
        <Mira reading />
      </section>
    </main>
  );
}
