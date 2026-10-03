/** "Why Mira says this": localized descriptions of today's factors (concept §4). */

import type { TFunction } from "i18next";

import type { Factor } from "./api";

export interface FactorText {
  title: string;
  details: string[];
}

export function houseName(t: TFunction, house: number): string {
  return t("why.house", { count: house, ordinal: true });
}

export function describeFactor(t: TFunction, f: Factor): FactorText {
  const transit = t(`planet.${f.transit}`);
  const house = houseName(t, f.house);
  const theme = t(`why.houseTheme.${f.house}`);
  let title: string;
  const details: string[] = [];
  if (f.kind === "aspect" && f.aspect && f.natal) {
    title = t(`why.aspect.${f.aspect}`, { transit, natal: t(`why.natal.${f.natal}`) });
    details.push(t(`why.nature.${f.nature}`), `${house}: ${theme}`);
  } else {
    title = t("why.placement", { transit, house });
    details.push(theme);
  }
  if (f.exact_at) details.push(t("why.exactAt", { time: f.exact_at }));
  if (f.background) details.push(t("why.background"));
  return { title, details };
}
