import { describe, expect, it } from "vitest";
import { formatARS, formatDate, formatDateTime, parsePrice } from "./format";

describe("parsePrice", () => {
  it("parses Decimal strings returned by the backend", () => {
    expect(parsePrice("12.50")).toBe(12.5);
    expect(parsePrice("0")).toBe(0);
    expect(parsePrice("1234.56")).toBeCloseTo(1234.56);
  });

  it("passes numbers through unchanged", () => {
    expect(parsePrice(1500)).toBe(1500);
    expect(parsePrice(0.99)).toBe(0.99);
  });

  it("falls back to 0 for nullish or invalid input", () => {
    expect(parsePrice(null)).toBe(0);
    expect(parsePrice(undefined)).toBe(0);
    expect(parsePrice("")).toBe(0);
    expect(parsePrice("not-a-number")).toBe(0);
  });
});

describe("formatARS", () => {
  it("renders an ARS currency string with es-AR separators", () => {
    expect(formatARS("12.50")).toContain("12,50");
    expect(formatARS(1500)).toContain("1.500");
    expect(formatARS(null)).toContain("0,00");
  });
});

describe("formatDate", () => {
  it("formats ISO dates in es-AR order", () => {
    expect(formatDate("2026-08-16T10:00:00")).toContain("2026");
  });

  it("returns a placeholder for missing values", () => {
    expect(formatDate(null)).toBe("—");
  });
});

describe("formatDateTime", () => {
  it("formats datetimes without crashing", () => {
    expect(formatDateTime("2026-08-16T10:30:00")).not.toBe("—");
    expect(formatDateTime("2026-08-16T10:30:00")).toContain("10:30");
  });

  it("returns a placeholder for missing values", () => {
    expect(formatDateTime(undefined)).toBe("—");
  });
});