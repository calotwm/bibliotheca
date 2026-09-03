import { describe, expect, it } from "vitest";
import { defaultSharesFromObservaciones, sellerLabelFromShares, timeOfDay } from "./shares";

describe("defaultSharesFromObservaciones", () => {
  it("defaults to 85/15 for null, empty, or no-name observaciones", () => {
    expect(defaultSharesFromObservaciones(null)).toEqual({ juli: 85, cande: 15 });
    expect(defaultSharesFromObservaciones(undefined)).toEqual({ juli: 85, cande: 15 });
    expect(defaultSharesFromObservaciones("")).toEqual({ juli: 85, cande: 15 });
    expect(defaultSharesFromObservaciones("En consignación 30%")).toEqual({
      juli: 85,
      cande: 15,
    });
  });

  it("defaults to 85/15 for Juli only", () => {
    expect(defaultSharesFromObservaciones("Juli")).toEqual({ juli: 85, cande: 15 });
  });

  it("defaults to 0/100 for Cande only", () => {
    expect(defaultSharesFromObservaciones("Cande")).toEqual({ juli: 0, cande: 100 });
  });

  it("defaults to 50/50 when both names are present", () => {
    expect(defaultSharesFromObservaciones("Juli y Cande")).toEqual({
      juli: 50,
      cande: 50,
    });
    expect(defaultSharesFromObservaciones("Consignación Juli y Cande")).toEqual({
      juli: 50,
      cande: 50,
    });
  });

  it("matches names case-insensitively", () => {
    expect(defaultSharesFromObservaciones("CANDE")).toEqual({ juli: 0, cande: 100 });
    expect(defaultSharesFromObservaciones("juli y cande")).toEqual({
      juli: 50,
      cande: 50,
    });
  });
});

describe("sellerLabelFromShares", () => {
  it("labels a 50/50 split as Juli y Cande (string or number)", () => {
    expect(sellerLabelFromShares(50, 50)).toBe("Juli y Cande");
    expect(sellerLabelFromShares("50.00", "50.00")).toBe("Juli y Cande");
  });

  it("labels Cande-only as Cande", () => {
    expect(sellerLabelFromShares(0, 100)).toBe("Cande");
    expect(sellerLabelFromShares("0.00", "100.00")).toBe("Cande");
  });

  it("labels Juli-only and the default split as Juli", () => {
    expect(sellerLabelFromShares(100, 0)).toBe("Juli");
    expect(sellerLabelFromShares(85, 15)).toBe("Juli");
    expect(sellerLabelFromShares(null, null)).toBe("Juli");
    expect(sellerLabelFromShares(undefined, undefined)).toBe("Juli");
  });

  it("shows explicit percentages for unusual splits", () => {
    expect(sellerLabelFromShares(60, 40)).toBe("Juli 60% / Cande 40%");
    expect(sellerLabelFromShares(70, 30)).toBe("Juli 70% / Cande 30%");
  });
});

describe("timeOfDay", () => {
  it("extracts the HH:MM:SS portion of an ISO datetime", () => {
    expect(timeOfDay("2026-08-29T00:30:00")).toBe("00:30:00");
    expect(timeOfDay("2026-08-29T10:15:00Z")).toBe("10:15:00");
  });

  it("falls back to midnight for missing values", () => {
    expect(timeOfDay(null)).toBe("00:00:00");
    expect(timeOfDay(undefined)).toBe("00:00:00");
    expect(timeOfDay("not-a-datetime")).toBe("00:00:00");
  });
});
