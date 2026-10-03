import { describe, expect, it } from "vitest";

import { litPath } from "./moon";

describe("moon phase icon", () => {
  it("draws nothing at new moon and a full disc at full moon", () => {
    expect(litPath(0)).toBe("");
    expect(litPath(1)).toContain("A10 10 0 1 1 12 2");
  });

  it("bends the terminator right for crescents and left for gibbous phases", () => {
    expect(litPath(0.25)).toBe("M12 2 A10 10 0 0 1 12 22 A5.00 10 0 0 0 12 2Z");
    expect(litPath(0.75)).toBe("M12 2 A10 10 0 0 1 12 22 A5.00 10 0 0 1 12 2Z");
    expect(litPath(0.5)).toContain("A0.00 10");
  });
});
