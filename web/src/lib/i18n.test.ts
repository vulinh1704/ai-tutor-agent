// @vitest-environment node
import { describe, expect, it } from "vitest";

import { detectLanguage, messages, translate, type MessageKey } from "@/lib/i18n";

describe("detectLanguage", () => {
  it.each([
    [["vi-VN", "en-US"], "vi"],
    [["vi"], "vi"],
    [["VI-vn"], "vi"],
    [["en-GB", "vi"], "en"],
    [["fr-FR"], "en"],
    [[], "en"],
  ])("%j -> %s", (preferred, expected) => {
    expect(detectLanguage(preferred)).toBe(expected);
  });
});

describe("translate", () => {
  it("fills placeholders in the chosen language", () => {
    expect(translate("en", "ladder.level", { level: 2, max: 3 })).toBe("Level 2 of 3");
    expect(translate("vi", "ladder.level", { level: 2, max: 3 })).toBe("Mức 2/3");
    expect(translate("vi", "home.title", { name: "Linh" })).toBe("Hôm nay mình học gì đây, Linh?");
  });

  it("leaves unknown placeholders visible instead of hiding them", () => {
    expect(translate("en", "grade.label")).toBe("Grade {n}");
  });

  it("has a complete, non-empty Vietnamese translation", () => {
    const keys = Object.keys(messages.en) as MessageKey[];
    expect(Object.keys(messages.vi).sort()).toEqual([...keys].sort());
    for (const key of keys) {
      expect(messages.vi[key].trim(), key).not.toBe("");
      const placeholders = (text: string) => (text.match(/\{\w+\}/g) ?? []).sort();
      expect(placeholders(messages.vi[key]), key).toEqual(placeholders(messages.en[key]));
    }
  });
});
