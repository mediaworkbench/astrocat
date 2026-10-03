import { createInstance, type TFunction } from "i18next";
import { describe, expect, it } from "vitest";

import type { Factor } from "./api";
import de from "./locales/de.json";
import en from "./locales/en.json";
import es from "./locales/es.json";
import { describeFactor } from "./why";

const LOCALES = { en, es, de } as const;

/** Flattened keys; plural/ordinal suffixes collapse, since languages need different forms. */
function keys(obj: object, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const key = prefix + k.replace(/_ordinal_(zero|one|two|few|many|other)$/, "");
    return typeof v === "object" && v !== null ? keys(v, `${key}.`) : [key];
  });
}

async function tFor(lng: keyof typeof LOCALES): Promise<TFunction> {
  const i18n = createInstance();
  await i18n.init({ lng, resources: { [lng]: { translation: LOCALES[lng] } }, interpolation: { escapeValue: false } });
  return i18n.t;
}

const aspect: Factor = {
  id: "f1", kind: "aspect", transit: "venus", aspect: "trine", natal: "moon", house: 5,
  nature: "harmonious", exact_at: null, background: false,
};
const moonAspect: Factor = { ...aspect, transit: "moon", aspect: "square", natal: "sun", house: 2, nature: "tense", exact_at: "14:20" };
const placement: Factor = {
  id: "f3", kind: "placement", transit: "moon", aspect: null, natal: null, house: 4,
  nature: "neutral", exact_at: null, background: false,
};
const background: Factor = { ...aspect, transit: "saturn", aspect: "opposition", natal: "ascendant", house: 10, nature: "tense", background: true };

describe("locales", () => {
  it("have the same keys in every language", () => {
    const reference = new Set(keys(en));
    for (const [lng, data] of Object.entries(LOCALES)) {
      const own = new Set(keys(data));
      expect([...reference].filter((k) => !own.has(k)), `${lng} is missing`).toEqual([]);
      expect([...own].filter((k) => !reference.has(k)), `${lng} has extra`).toEqual([]);
    }
  });

  it("have no empty strings", () => {
    for (const data of Object.values(LOCALES)) {
      const walk = (o: object): void =>
        Object.values(o).forEach((v) => (typeof v === "string" ? expect(v.trim()).not.toBe("") : walk(v)));
      walk(data);
    }
  });
});

describe("why texts", () => {
  it("describe aspects, placements, exact times and background themes in English", async () => {
    const t = await tFor("en");
    expect(describeFactor(t, aspect)).toEqual({
      title: "Venus trine your Moon",
      details: ["supportive", "5th house: romance, play and creativity"],
    });
    expect(describeFactor(t, moonAspect).details).toContain("exact at 14:20");
    expect(describeFactor(t, placement).title).toBe("Moon in your 4th house");
    expect(describeFactor(t, { ...placement, house: 1 }).title).toBe("Moon in your 1st house");
    expect(describeFactor(t, { ...placement, house: 2 }).title).toBe("Moon in your 2nd house");
    expect(describeFactor(t, { ...placement, house: 3 }).title).toBe("Moon in your 3rd house");
    expect(describeFactor(t, { ...placement, house: 11 }).title).toBe("Moon in your 11th house");
    expect(describeFactor(t, background).details).toContain("background theme for several weeks");
  });

  it("use German grammar", async () => {
    const t = await tFor("de");
    expect(describeFactor(t, aspect).title).toBe("Venus im Trigon zu deinem Mond");
    expect(describeFactor(t, moonAspect).title).toBe("Mond im Quadrat zu deiner Sonne");
    expect(describeFactor(t, placement).title).toBe("Mond in deinem 4. Haus");
    expect(describeFactor(t, background).title).toBe("Saturn in Opposition zu deinem Aszendenten");
  });

  it("use Spanish grammar", async () => {
    const t = await tFor("es");
    expect(describeFactor(t, aspect).title).toBe("Venus en trígono con tu Luna");
    expect(describeFactor(t, placement).title).toBe("Luna en tu casa 4");
    expect(describeFactor(t, moonAspect).details).toContain("exacto a las 14:20");
  });
});
